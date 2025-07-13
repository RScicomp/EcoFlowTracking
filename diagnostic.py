#!/usr/bin/env python3
"""
EcoFlow Monitoring System Diagnostic Script
Checks system status, database contents, API connectivity, and recent logs
"""

import os
import sqlite3
import json
import requests
import hashlib
import hmac
import random
import binascii
from datetime import datetime, timedelta
from dotenv import load_dotenv
import pandas as pd

def check_environment():
    """Check environment variables"""
    print("🔍 CHECKING ENVIRONMENT VARIABLES")
    print("=" * 50)
    
    load_dotenv()
    
    access_key = os.getenv('ECOFLOW_ACCESS_KEY')
    secret_key = os.getenv('ECOFLOW_SECRET_KEY')
    device_sn = os.getenv('ECOFLOW_DEVICE_SN')
    
    print(f"ECOFLOW_ACCESS_KEY: {'✅ Set' if access_key else '❌ Missing'}")
    if access_key:
        print(f"  Length: {len(access_key)} characters")
        print(f"  Preview: {access_key[:8]}...")
    
    print(f"ECOFLOW_SECRET_KEY: {'✅ Set' if secret_key else '❌ Missing'}")
    if secret_key:
        print(f"  Length: {len(secret_key)} characters")
        print(f"  Preview: {secret_key[:8]}...")
    
    print(f"ECOFLOW_DEVICE_SN: {'✅ Set' if device_sn else '❌ Missing'}")
    if device_sn:
        print(f"  Value: {device_sn}")
    
    return bool(access_key and secret_key and device_sn)

def check_database():
    """Check database status and contents"""
    print("\n🗄️  CHECKING DATABASE")
    print("=" * 50)
    
    db_path = "ecoflow_data.db"
    
    if not os.path.exists(db_path):
        print(f"❌ Database file not found: {db_path}")
        return False
    
    # Check file size
    size_mb = os.path.getsize(db_path) / (1024 * 1024)
    print(f"✅ Database file exists: {db_path}")
    print(f"   Size: {size_mb:.2f} MB")
    
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Check if table exists
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='power_usage'")
        table_exists = cursor.fetchone() is not None
        
        if table_exists:
            print("✅ power_usage table exists")
            
            # Get row count
            cursor.execute("SELECT COUNT(*) FROM power_usage")
            row_count = cursor.fetchone()[0]
            print(f"   Total records: {row_count}")
            
            if row_count > 0:
                # Get latest record
                cursor.execute("SELECT timestamp, watts_out, soc FROM power_usage ORDER BY timestamp DESC LIMIT 1")
                latest = cursor.fetchone()
                print(f"   Latest record: {latest[0]}")
                print(f"   Latest watts_out: {latest[1]}W")
                print(f"   Latest SOC: {latest[2]}%")
                
                # Get records from last 24 hours
                yesterday = (datetime.now() - timedelta(days=1)).isoformat()
                cursor.execute("SELECT COUNT(*) FROM power_usage WHERE timestamp >= ?", (yesterday,))
                recent_count = cursor.fetchone()[0]
                print(f"   Records in last 24h: {recent_count}")
                
                # Get collection types
                cursor.execute("SELECT collection_type, COUNT(*) FROM power_usage GROUP BY collection_type")
                collection_types = cursor.fetchall()
                print("   Collection types:")
                for ctype, count in collection_types:
                    print(f"     {ctype}: {count} records")
            else:
                print("   ⚠️  No data records found")
        else:
            print("❌ power_usage table does not exist")
        
        conn.close()
        return table_exists
        
    except Exception as e:
        print(f"❌ Database error: {e}")
        return False

def get_qstr(params):
    """Generate query string from parameters"""
    if not params:
        return ""
    return '&'.join([f"{key}={params[key]}" for key in sorted(params.keys())])

def hmac_sha256(data: str, key: str) -> str:
    """Generate HMAC-SHA256 signature"""
    hashed = hmac.new(key.encode('utf-8'), data.encode('utf-8'), hashlib.sha256).digest()
    return binascii.hexlify(hashed).decode('utf-8')

def get_map(json_obj, prefix=""):
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

def test_api_connection():
    """Test API connection and authentication"""
    print("\n🌐 TESTING API CONNECTION")
    print("=" * 50)
    
    load_dotenv()
    
    access_key = os.getenv('ECOFLOW_ACCESS_KEY')
    secret_key = os.getenv('ECOFLOW_SECRET_KEY')
    device_sn = os.getenv('ECOFLOW_DEVICE_SN')
    
    if not all([access_key, secret_key, device_sn]):
        print("❌ Missing environment variables for API test")
        return False
    
    base_url = "https://api.ecoflow.com"
    
    # Test device quota endpoint (correct endpoint)
    try:
        print("Testing device quota endpoint...")
        params = {
            "sn": device_sn,
            "params": {
                "quotas": ["pd.soc", "pd.wattsOutSum", "pd.typec1Temp"]
            }
        }
        
        # Generate signature using the same method as the monitor
        nonce = str(random.randint(100000, 999999))
        timestamp = str(int(time.time() * 1000))
        headers = {
            'accessKey': access_key,
            'nonce': nonce,
            'timestamp': timestamp
        }
        
        sign_str = (get_qstr(get_map(params)) + '&' if params else '') + get_qstr(headers)
        headers['sign'] = hmac_sha256(sign_str, secret_key)
        
        response = requests.post(f"{base_url}/iot-open/sign/device/quota", headers=headers, json=params)
        print(f"   Status: {response.status_code}")
        print(f"   Response: {response.text[:200]}...")
        
        if response.status_code == 200:
            data = response.json()
            if data.get('code') == '0':
                print("✅ Device quota API working")
                quota_data = data.get('data', {}).get('quota', {})
                print("   Device data:")
                for key, value in quota_data.items():
                    print(f"     {key}: {value}")
                return True
            else:
                print(f"❌ API error: {data.get('message', 'Unknown error')}")
                return False
        else:
            print(f"❌ HTTP error: {response.status_code}")
            return False
            
    except Exception as e:
        print(f"❌ API connection error: {e}")
        return False

def test_device_data():
    """Test getting device data"""
    print("\n📊 TESTING DEVICE DATA RETRIEVAL")
    print("=" * 50)
    
    load_dotenv()
    
    access_key = os.getenv('ECOFLOW_ACCESS_KEY')
    secret_key = os.getenv('ECOFLOW_SECRET_KEY')
    device_sn = os.getenv('ECOFLOW_DEVICE_SN')
    
    if not all([access_key, secret_key, device_sn]):
        print("❌ Missing environment variables for device data test")
        return False
    
    base_url = "https://api.ecoflow.com"
    
    # Test device quota all endpoint (correct endpoint)
    try:
        print("Testing device quota all endpoint...")
        
        # Include device SN for quota/all endpoint
        params = {
            "sn": device_sn
        }
        nonce = str(random.randint(100000, 999999))
        timestamp = str(int(time.time() * 1000))
        headers = {
            'accessKey': access_key,
            'nonce': nonce,
            'timestamp': timestamp
        }
        
        sign_str = (get_qstr(get_map(params)) + '&' if params else '') + get_qstr(headers)
        headers['sign'] = hmac_sha256(sign_str, secret_key)
        
        response = requests.get(f"{base_url}/iot-open/sign/device/quota/all", headers=headers, params=params)
        
        print(f"   Status: {response.status_code}")
        print(f"   Response: {response.text[:300]}...")
        
        if response.status_code == 200:
            data = response.json()
            if data.get('code') == '0':
                print("✅ Device quota all API working")
                quota_data = data.get('data', {}).get('quota', {})
                print("   Sample device data:")
                count = 0
                for key, value in quota_data.items():
                    if count < 5:  # Show first 5 items
                        print(f"     {key}: {value}")
                        count += 1
                    else:
                        print(f"     ... and {len(quota_data) - 5} more metrics")
                        break
                return True
            else:
                print(f"❌ API error: {data.get('message', 'Unknown error')}")
                return False
        else:
            print(f"❌ HTTP error: {response.status_code}")
            return False
            
    except Exception as e:
        print(f"❌ Device data error: {e}")
        return False

def check_logs():
    """Check recent log entries"""
    print("\n📝 CHECKING RECENT LOGS")
    print("=" * 50)
    
    log_file = "ecoflow_monitor.log"
    
    if not os.path.exists(log_file):
        print(f"❌ Log file not found: {log_file}")
        return False
    
    # Get file size
    size_mb = os.path.getsize(log_file) / (1024 * 1024)
    print(f"✅ Log file exists: {log_file}")
    print(f"   Size: {size_mb:.2f} MB")
    
    # Read last 20 lines
    try:
        with open(log_file, 'r') as f:
            lines = f.readlines()
            print(f"   Total lines: {len(lines)}")
            
            if lines:
                print("\n   Last 10 log entries:")
                for line in lines[-10:]:
                    print(f"     {line.strip()}")
            else:
                print("   ⚠️  Log file is empty")
        
        return True
        
    except Exception as e:
        print(f"❌ Error reading log file: {e}")
        return False

def check_config():
    """Check configuration file"""
    print("\n⚙️  CHECKING CONFIGURATION")
    print("=" * 50)
    
    config_file = "config.json"
    
    if not os.path.exists(config_file):
        print(f"❌ Config file not found: {config_file}")
        return False
    
    try:
        with open(config_file, 'r') as f:
            config = json.load(f)
        
        print(f"✅ Config file exists: {config_file}")
        
        # Check polling schedules
        schedules = config.get('polling_schedules', {})
        print("   Polling schedules:")
        for name, schedule in schedules.items():
            enabled = schedule.get('enabled', False)
            interval = schedule.get('interval_seconds', 0)
            print(f"     {name}: {'✅ Enabled' if enabled else '❌ Disabled'} ({interval}s)")
        
        # Check alerts
        alerts = config.get('alerts', {})
        print("   Alerts:")
        print(f"     Low battery threshold: {alerts.get('low_battery_threshold', 'Not set')}%")
        print(f"     High temp threshold: {alerts.get('high_temperature_threshold', 'Not set')}°C")
        print(f"     Alerts enabled: {'✅ Yes' if alerts.get('enabled', False) else '❌ No'}")
        
        return True
        
    except Exception as e:
        print(f"❌ Error reading config file: {e}")
        return False

def main():
    """Run all diagnostic checks"""
    print("🔧 ECOFLOW MONITORING SYSTEM DIAGNOSTIC")
    print("=" * 60)
    print(f"Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    
    # Run all checks
    env_ok = check_environment()
    db_ok = check_database()
    api_ok = test_api_connection()
    data_ok = test_device_data()
    logs_ok = check_logs()
    config_ok = check_config()
    
    # Summary
    print("\n📋 DIAGNOSTIC SUMMARY")
    print("=" * 50)
    
    checks = [
        ("Environment Variables", env_ok),
        ("Database", db_ok),
        ("API Connection", api_ok),
        ("Device Data", data_ok),
        ("Logs", logs_ok),
        ("Configuration", config_ok)
    ]
    
    all_passed = True
    for name, status in checks:
        status_icon = "✅" if status else "❌"
        print(f"{status_icon} {name}")
        if not status:
            all_passed = False
    
    print()
    if all_passed:
        print("🎉 All checks passed! System appears to be working correctly.")
    else:
        print("⚠️  Some checks failed. Review the issues above.")
        
        # Recommendations
        print("\n💡 RECOMMENDATIONS:")
        if not env_ok:
            print("   - Check your .env file and ensure all required variables are set")
        if not db_ok:
            print("   - Database may be corrupted or missing. Try restarting the monitor.")
        if not api_ok or not data_ok:
            print("   - API credentials may be incorrect or device may be offline")
        if not logs_ok:
            print("   - Check file permissions for log file")
        if not config_ok:
            print("   - Configuration file may be corrupted. Check JSON syntax.")

if __name__ == "__main__":
    import time
    main() 