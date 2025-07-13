import os
import time
import json
import requests
import hashlib
import hmac
import random
import binascii
from datetime import datetime, timedelta
from dotenv import load_dotenv
import sqlite3
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import threading
import logging
from typing import Dict, List, Optional
import sys

# Load environment variables
load_dotenv()

class EcoFlowMonitor:
    def __init__(self, config_file: str = "config.json", debug: bool = False):
        """
        Initialize EcoFlow Monitor with configurable polling schedules
        
        Args:
            config_file: Path to configuration file
            debug: Enable debug logging
        """
        self.access_key = os.getenv('ECOFLOW_ACCESS_KEY')
        self.secret_key = os.getenv('ECOFLOW_SECRET_KEY')
        self.device_sn = os.getenv('ECOFLOW_DEVICE_SN')
        self.base_url = "https://api.ecoflow.com"
        
        # Setup logging FIRST
        log_level = logging.DEBUG if debug else logging.INFO
        logging.basicConfig(
            level=log_level,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler('ecoflow_monitor.log'),
                logging.StreamHandler()
            ]
        )
        self.logger = logging.getLogger(__name__)
        
        if debug:
            self.logger.debug("Debug mode enabled")
            self.logger.debug(f"Access Key: {self.access_key[:8]}..." if self.access_key else "Not set")
            self.logger.debug(f"Secret Key: {self.secret_key[:8]}..." if self.secret_key else "Not set")
            self.logger.debug(f"Device SN: {self.device_sn}")
        
        # Load configuration AFTER logger is set up
        self.config = self.load_config(config_file)
        
        # Initialize database
        self.setup_database()
        
        # Threading control
        self.running = False
        self.collection_thread = None
        
    def load_config(self, config_file: str) -> Dict:
        """Load configuration from JSON file"""
        default_config = {
            "polling_schedules": {
                "critical_metrics": {
                    "interval_seconds": 30,
                    "enabled": True,
                    "metrics": ["pd.soc", "pd.wattsOutSum", "pd.typec1Temp", "bms_bmsStatus.temp"]
                },
                "standard_metrics": {
                    "interval_seconds": 300,  # 5 minutes
                    "enabled": True,
                    "metrics": "all"
                },
                "daily_summary": {
                    "interval_seconds": 86400,  # 24 hours
                    "enabled": True,
                    "time": "00:00"  # Midnight
                }
            },
            "alerts": {
                "low_battery_threshold": 20,
                "high_temperature_threshold": 60,
                "high_power_threshold": 2000,
                "enabled": True
            },
            "database": {
                "path": "ecoflow_data.db",
                "retention_days": 90
            },
            "visualization": {
                "default_days": 7,
                "auto_generate": True,
                "output_path": "dashboard.html"
            }
        }
        
        try:
            with open(config_file, 'r') as f:
                config = json.load(f)
                # Merge with defaults
                for key, value in default_config.items():
                    if key not in config:
                        config[key] = value
                    elif isinstance(value, dict):
                        config[key].update(value)
            self.logger.info(f"Configuration loaded from {config_file}")
        except FileNotFoundError:
            config = default_config
            self.save_config(config, config_file)
            self.logger.info(f"Created default configuration file: {config_file}")
        
        return config
    
    def save_config(self, config: Dict, config_file: str):
        """Save configuration to JSON file"""
        with open(config_file, 'w') as f:
            json.dump(config, f, indent=2)
    
    def update_polling_schedule(self, schedule_name: str, **kwargs):
        """Update polling schedule configuration"""
        if schedule_name in self.config["polling_schedules"]:
            self.config["polling_schedules"][schedule_name].update(kwargs)
            self.save_config(self.config, "config.json")
            self.logger.info(f"Updated {schedule_name} polling schedule")
        else:
            self.logger.error(f"Unknown schedule: {schedule_name}")
    
    def get_qstr(self, params):
        """Generate query string from parameters"""
        if not params:
            return ""
        return '&'.join([f"{key}={params[key]}" for key in sorted(params.keys())])
    
    def hmac_sha256(self, data: str, key: str) -> str:
        """Generate HMAC-SHA256 signature"""
        hashed = hmac.new(key.encode('utf-8'), data.encode('utf-8'), hashlib.sha256).digest()
        return binascii.hexlify(hashed).decode('utf-8')
    
    def get_map(self, json_obj, prefix=""):
        """Flatten JSON object for signature generation"""
        def flatten(obj, pre=""):
            result = {}
            if isinstance(obj, dict):
                for k, v in obj.items():
                    result.update(flatten(v, f"{pre}.{k}" if pre else k))
            elif isinstance(obj, list):
                for i, item in enumerate(obj):
                    result.update(flatten(item, f"{pre}[{i}]"))
            else:
                result[pre] = obj
            return result
        return flatten(json_obj, prefix)
    
    def make_authenticated_request(self, endpoint: str, params: Dict = None) -> Dict:
        """Make authenticated API request"""
        nonce = str(random.randint(100000, 999999))
        timestamp = str(int(time.time() * 1000))
        headers = {
            'accessKey': self.access_key,
            'nonce': nonce,
            'timestamp': timestamp
        }
        
        sign_str = (self.get_qstr(self.get_map(params)) + '&' if params else '') + self.get_qstr(headers)
        headers['sign'] = self.hmac_sha256(sign_str, self.secret_key)
        
        url = f"{self.base_url}{endpoint}"
        
        # Debug logging
        self.logger.debug(f"Making API request to: {url}")
        self.logger.debug(f"Headers: {headers}")
        if params:
            self.logger.debug(f"Params: {params}")
        
        # Use POST for quota endpoint, GET for quota/all endpoint
        if endpoint == "/iot-open/sign/device/quota":
            response = requests.post(url, headers=headers, json=params)
        else:
            response = requests.get(url, headers=headers, params=params)
        
        self.logger.debug(f"Response status: {response.status_code}")
        self.logger.debug(f"Response headers: {dict(response.headers)}")
        
        if response.status_code == 200:
            response_data = response.json()
            self.logger.debug(f"Response data: {response_data}")
            return response_data
        else:
            self.logger.error(f"API request failed: {response.status_code} - {response.text}")
            return {"code": "error", "message": f"HTTP {response.status_code}"}
    
    def get_all_quotas(self, specific_metrics: List[str] = None) -> Dict:
        """Get comprehensive device data"""
        if specific_metrics:
            # Get specific metrics
            params = {
                "sn": self.device_sn,
                "params": {
                    "quotas": specific_metrics
                }
            }
            return self.make_authenticated_request("/iot-open/sign/device/quota", params)
        else:
            # Get all metrics - need to include device SN
            params = {
                "sn": self.device_sn
            }
            return self.make_authenticated_request("/iot-open/sign/device/quota/all", params)
    
    def setup_database(self):
        """Create SQLite database for time-series data"""
        db_path = self.config["database"]["path"]
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS power_usage (
                timestamp DATETIME PRIMARY KEY,
                watts_out INTEGER,
                watts_in INTEGER,
                soc INTEGER,
                remain_time INTEGER,
                typec1_watts INTEGER,
                car_watts INTEGER,
                usb1_watts INTEGER,
                usb2_watts INTEGER,
                qc_usb1_watts INTEGER,
                qc_usb2_watts INTEGER,
                typec2_watts INTEGER,
                chg_power_ac INTEGER,
                chg_power_dc INTEGER,
                chg_sun_power INTEGER,
                dsg_power_ac INTEGER,
                dsg_power_dc INTEGER,
                chg_type INTEGER,
                chg_state INTEGER,
                chg_dsg_state INTEGER,
                typec1_temp INTEGER,
                typec2_temp INTEGER,
                car_temp INTEGER,
                mppt_temp INTEGER,
                inv_temp INTEGER,
                battery_voltage INTEGER,
                battery_temp INTEGER,
                collection_type TEXT
            )
        ''')
        
        # Create indexes for better query performance
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_timestamp ON power_usage(timestamp)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_collection_type ON power_usage(collection_type)')
        
        conn.commit()
        conn.close()
        self.logger.info("Database setup complete")
    
    def store_data(self, data: Dict, collection_type: str = "standard"):
        """Store data in database"""
        try:
            conn = sqlite3.connect(self.config["database"]["path"])
            cursor = conn.cursor()
            
            timestamp = datetime.now().isoformat()
            
            cursor.execute('''
                INSERT OR REPLACE INTO power_usage (
                    timestamp, watts_out, watts_in, soc, remain_time,
                    typec1_watts, car_watts, usb1_watts, usb2_watts,
                    qc_usb1_watts, qc_usb2_watts, typec2_watts,
                    chg_power_ac, chg_power_dc, chg_sun_power,
                    dsg_power_ac, dsg_power_dc, chg_type, chg_state,
                    chg_dsg_state, typec1_temp, typec2_temp, car_temp,
                    mppt_temp, inv_temp, battery_voltage, battery_temp,
                    collection_type
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                timestamp,
                data.get('pd.wattsOutSum', 0),
                data.get('pd.wattsInSum', 0),
                data.get('pd.soc', 0),
                data.get('pd.remainTime', 0),
                data.get('pd.typec1Watts', 0),
                data.get('pd.carWatts', 0),
                data.get('pd.usb1Watts', 0),
                data.get('pd.usb2Watts', 0),
                data.get('pd.qcUsb1Watts', 0),
                data.get('pd.qcUsb2Watts', 0),
                data.get('pd.typec2Watts', 0),
                data.get('pd.chgPowerAC', 0),
                data.get('pd.chgPowerDC', 0),
                data.get('pd.chgSunPower', 0),
                data.get('pd.dsgPowerAC', 0),
                data.get('pd.dsgPowerDC', 0),
                data.get('mppt.chgType', 0),
                data.get('bms_emsStatus.chgState', 0),
                data.get('pd.chgDsgState', 0),
                data.get('pd.typec1Temp', 0),
                data.get('pd.typec2Temp', 0),
                data.get('pd.carTemp', 0),
                data.get('mppt.mpptTemp', 0),
                data.get('inv.outTemp', 0),
                data.get('bms_bmsStatus.vol', 0),
                data.get('bms_bmsStatus.temp', 0),
                collection_type
            ))
            
            conn.commit()
            conn.close()
            
        except Exception as e:
            self.logger.error(f"Error storing data: {e}")
    
    def get_historical_data(self, days: int = 7) -> pd.DataFrame:
        """Get historical data from database"""
        try:
            conn = sqlite3.connect(self.config["database"]["path"])
            
            # Calculate retention date
            retention_date = datetime.now() - timedelta(days=days)
            
            query = '''
                SELECT * FROM power_usage 
                WHERE timestamp >= ? 
                ORDER BY timestamp
            '''
            
            df = pd.read_sql_query(query, conn, params=(retention_date.isoformat(),))
            conn.close()
            
            # Convert timestamp to datetime
            df['timestamp'] = pd.to_datetime(df['timestamp'])
            
            return df
            
        except Exception as e:
            self.logger.error(f"Error retrieving historical data: {e}")
            return pd.DataFrame()
    
    def check_alerts(self) -> List[str]:
        """Monitor for critical conditions"""
        if not self.config["alerts"]["enabled"]:
            return []
        
        try:
            data = self.get_all_quotas(self.config["polling_schedules"]["critical_metrics"]["metrics"])
            
            if data.get('code') != '0':
                return [f"❌ API Error: {data.get('message', 'Unknown error')}"]
            
            data = data.get('data', {})
            alerts = []
            
            # Low battery alert
            soc = data.get('pd.soc', 100)
            if soc < self.config["alerts"]["low_battery_threshold"]:
                alerts.append(f"⚠️ Low battery: {soc}%")
            
            # High temperature alert
            typec1_temp = data.get('pd.typec1Temp', 0)
            if typec1_temp > self.config["alerts"]["high_temperature_threshold"]:
                alerts.append(f"🔥 High Type-C1 temperature: {typec1_temp}°C")
            
            # High power usage alert
            watts_out = data.get('pd.wattsOutSum', 0)
            if watts_out > self.config["alerts"]["high_power_threshold"]:
                alerts.append(f"⚡ High power usage: {watts_out}W")
            
            return alerts
            
        except Exception as e:
            self.logger.error(f"Error checking alerts: {e}")
            return [f"❌ Alert check failed: {e}"]
    
    def collect_critical_data(self):
        """Collect critical metrics at high frequency"""
        while self.running:
            try:
                data = self.get_all_quotas(self.config["polling_schedules"]["critical_metrics"]["metrics"])
                if data.get('code') == '0':
                    self.store_data(data['data'], "critical")
                    
                    # Check alerts
                    alerts = self.check_alerts()
                    for alert in alerts:
                        self.logger.warning(alert)
                        
                else:
                    self.logger.error(f"Critical data collection failed: {data.get('message')}")
                    
            except Exception as e:
                self.logger.error(f"Critical data collection error: {e}")
            
            time.sleep(self.config["polling_schedules"]["critical_metrics"]["interval_seconds"])
    
    def collect_standard_data(self):
        """Collect all metrics at standard frequency"""
        while self.running:
            try:
                data = self.get_all_quotas()
                if data.get('code') == '0':
                    self.store_data(data['data'], "standard")
                    self.logger.info("Standard data collected successfully")
                else:
                    self.logger.error(f"Standard data collection failed: {data.get('message')}")
                    
            except Exception as e:
                self.logger.error(f"Standard data collection error: {e}")
            
            time.sleep(self.config["polling_schedules"]["standard_metrics"]["interval_seconds"])
    
    def generate_daily_summary(self):
        """Generate daily summary report"""
        try:
            df = self.get_historical_data(1)  # Last 24 hours
            
            if df.empty:
                self.logger.warning("No data available for daily summary")
                return
            
            summary = {
                "date": datetime.now().strftime("%Y-%m-%d"),
                "total_energy_in": df['watts_in'].sum() / 1000,  # Convert to kWh
                "total_energy_out": df['watts_out'].sum() / 1000,  # Convert to kWh
                "avg_soc": df['soc'].mean(),
                "min_soc": df['soc'].min(),
                "max_soc": df['soc'].max(),
                "peak_power": df['watts_out'].max(),
                "avg_temperature": df['typec1_temp'].mean(),
                "charging_sessions": len(df[df['chg_state'] == 1]),
                "discharging_sessions": len(df[df['chg_dsg_state'] == 1])
            }
            
            # Store summary in database or file
            with open(f"daily_summary_{summary['date']}.json", 'w') as f:
                json.dump(summary, f, indent=2)
            
            self.logger.info(f"Daily summary generated: {summary}")
            
        except Exception as e:
            self.logger.error(f"Error generating daily summary: {e}")
    
    def start_monitoring(self):
        """Start the monitoring system"""
        if self.running:
            self.logger.warning("Monitoring already running")
            return
        
        self.running = True
        self.logger.info("Starting EcoFlow monitoring system")
        
        # Start critical metrics collection
        if self.config["polling_schedules"]["critical_metrics"]["enabled"]:
            self.collection_thread = threading.Thread(target=self.collect_critical_data)
            self.collection_thread.daemon = True
            self.collection_thread.start()
            self.logger.info("Critical metrics collection started")
        
        # Start standard metrics collection
        if self.config["polling_schedules"]["standard_metrics"]["enabled"]:
            self.standard_thread = threading.Thread(target=self.collect_standard_data)
            self.standard_thread.daemon = True
            self.standard_thread.start()
            self.logger.info("Standard metrics collection started")
    
    def stop_monitoring(self):
        """Stop the monitoring system"""
        self.running = False
        self.logger.info("Stopping EcoFlow monitoring system")
        
        if self.collection_thread:
            self.collection_thread.join(timeout=5)
        if hasattr(self, 'standard_thread'):
            self.standard_thread.join(timeout=5)
    
    def create_dashboard(self, days: int = None, save_path: str = None) -> go.Figure:
        """Create comprehensive dashboard"""
        if days is None:
            days = self.config["visualization"]["default_days"]
        
        df = self.get_historical_data(days)
        
        if df.empty:
            self.logger.warning("No data available for dashboard")
            return None
        
        # Create subplots
        fig = make_subplots(
            rows=4, cols=2,
            subplot_titles=(
                'Power Usage Over Time', 'Battery Level',
                'Energy Accumulation', 'Temperature Monitoring',
                'Output Port Usage', 'Charging Type Distribution',
                'Daily Usage Pattern', 'Efficiency Metrics'
            ),
            specs=[[{"secondary_y": False}, {"secondary_y": False}],
                   [{"secondary_y": False}, {"secondary_y": False}],
                   [{"secondary_y": False}, {"secondary_y": False}],
                   [{"secondary_y": False}, {"secondary_y": False}]]
        )
        
        # Power usage over time
        fig.add_trace(
            go.Scatter(x=df['timestamp'], y=df['watts_out'], 
                      name='Power Out', line=dict(color='red')),
            row=1, col=1
        )
        fig.add_trace(
            go.Scatter(x=df['timestamp'], y=df['watts_in'], 
                      name='Power In', line=dict(color='green')),
            row=1, col=1
        )
        
        # Battery level
        fig.add_trace(
            go.Scatter(x=df['timestamp'], y=df['soc'], 
                      name='Battery %', line=dict(color='blue')),
            row=1, col=2
        )
        
        # Energy accumulation
        fig.add_trace(
            go.Scatter(x=df['timestamp'], y=df['chg_power_ac'], 
                      name='AC Charged (Wh)', line=dict(color='orange')),
            row=2, col=1
        )
        fig.add_trace(
            go.Scatter(x=df['timestamp'], y=df['chg_sun_power'], 
                      name='Solar Charged (Wh)', line=dict(color='yellow')),
            row=2, col=1
        )
        
        # Temperature monitoring
        fig.add_trace(
            go.Scatter(x=df['timestamp'], y=df['typec1_temp'], 
                      name='Type-C1 Temp', line=dict(color='purple')),
            row=2, col=2
        )
        fig.add_trace(
            go.Scatter(x=df['timestamp'], y=df['car_temp'], 
                      name='Car Temp', line=dict(color='brown')),
            row=2, col=2
        )
        
        # Output port usage (bar chart)
        port_usage = {
            'Type-C1': df['typec1_watts'].mean(),
            'Car': df['car_watts'].mean(),
            'USB1': df['usb1_watts'].mean(),
            'USB2': df['usb2_watts'].mean(),
            'QC-USB1': df['qc_usb1_watts'].mean(),
            'QC-USB2': df['qc_usb2_watts'].mean(),
            'Type-C2': df['typec2_watts'].mean()
        }
        
        fig.add_trace(
            go.Bar(x=list(port_usage.keys()), y=list(port_usage.values()),
                   name='Port Usage (W)'),
            row=3, col=1
        )
        
        # Charging type distribution
        charging_types = df['chg_type'].value_counts()
        charging_labels = {
            0: 'None', 1: 'Adapter', 2: 'MPPT (Solar)', 
            3: 'AC (Grid)', 4: 'Gas', 5: 'Wind'
        }
        
        fig.add_trace(
            go.Pie(labels=[charging_labels.get(i, f'Type {i}') for i in charging_types.index],
                   values=charging_types.values,
                   name='Charging Types'),
            row=3, col=2
        )
        
        # Daily usage pattern (heatmap)
        df['hour'] = pd.to_datetime(df['timestamp']).dt.hour
        df['day'] = pd.to_datetime(df['timestamp']).dt.day_name()
        
        hourly_usage = df.groupby(['day', 'hour'])['watts_out'].mean().unstack()
        
        fig.add_trace(
            go.Heatmap(z=hourly_usage.values, x=hourly_usage.columns, 
                      y=hourly_usage.index, colorscale='Viridis',
                      name='Hourly Usage'),
            row=4, col=1
        )
        
        # Efficiency metrics
        efficiency = {
            'Avg Efficiency': (df['watts_out'].sum() / max(df['watts_in'].sum(), 1)) * 100,
            'Peak Power': df['watts_out'].max(),
            'Avg SOC': df['soc'].mean(),
            'Total Energy (kWh)': df['watts_out'].sum() / 1000
        }
        
        fig.add_trace(
            go.Bar(x=list(efficiency.keys()), y=list(efficiency.values()),
                   name='Efficiency Metrics'),
            row=4, col=2
        )
        
        fig.update_layout(
            height=1200, 
            title_text=f"EcoFlow Delta 2 Usage Dashboard - Last {days} Days",
            showlegend=True
        )
        
        # Save dashboard if path provided
        if save_path:
            fig.write_html(save_path)
            self.logger.info(f"Dashboard saved to {save_path}")
        
        return fig
    
    def cleanup_old_data(self):
        """Clean up old data based on retention policy"""
        try:
            retention_days = self.config["database"]["retention_days"]
            cutoff_date = datetime.now() - timedelta(days=retention_days)
            
            conn = sqlite3.connect(self.config["database"]["path"])
            cursor = conn.cursor()
            
            cursor.execute('DELETE FROM power_usage WHERE timestamp < ?', (cutoff_date.isoformat(),))
            deleted_rows = cursor.rowcount
            
            conn.commit()
            conn.close()
            
            self.logger.info(f"Cleaned up {deleted_rows} old data records")
            
        except Exception as e:
            self.logger.error(f"Error cleaning up old data: {e}")

if __name__ == "__main__":
    # Check for debug flag
    debug_mode = "--debug" in sys.argv
    
    # Example usage
    monitor = EcoFlowMonitor(debug=debug_mode)
    
    if debug_mode:
        print("🔍 Debug mode enabled!")
        print("Check ecoflow_monitor.log for detailed debug information")
    
    # Update polling schedules if needed
    # monitor.update_polling_schedule("critical_metrics", interval_seconds=60)
    # monitor.update_polling_schedule("standard_metrics", interval_seconds=600)
    
    # Start monitoring
    monitor.start_monitoring()
    
    try:
        # Keep the main thread alive
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        monitor.stop_monitoring()
        print("Monitoring stopped") 