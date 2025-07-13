# EcoFlow Delta 2 Monitoring System

A comprehensive monitoring and analytics system for EcoFlow Delta 2 portable batteries. Track power usage, battery health, energy efficiency, and usage patterns over time.


<img width="462" height="653" alt="Screenshot 2025-07-13 at 2 47 48 PM" src="https://github.com/user-attachments/assets/bff5d4cf-62e2-4da6-9625-9a7fa713a7d7" />

<img width="482" height="619" alt="Screenshot 2025-07-13 at 2 47 43 PM" src="https://github.com/user-attachments/assets/76b40a7c-9b3a-4239-aea4-6f8a84416005" />


## Features

- **Real-time Monitoring**: Track critical metrics every 30 seconds
- **Comprehensive Data Collection**: Monitor all power outputs, charging sources, and temperatures
- **Interactive Dashboards**: Beautiful visualizations with Plotly
- **Configurable Polling**: Adjustable data collection intervals
- **Alert System**: Get notified of low battery, high temperature, or unusual usage
- **Data Retention**: Automatic cleanup of old data
- **Energy Analysis**: Track efficiency, costs, and usage patterns

## Quick Start

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

### 2. Set Up Environment Variables

Create a `.env` file in your project directory:

```bash
ECOFLOW_ACCESS_KEY=your_access_key_here
ECOFLOW_SECRET_KEY=your_secret_key_here
ECOFLOW_DEVICE_SN=your_device_serial_number
```

### 3. Start Monitoring

```bash
python ecoflow_monitor.py
```

### 4. Generate Dashboard

```bash
python dashboard_generator.py --type quick --days 7
```

## Configuration

The system uses `config.json` for all settings. You can modify polling schedules, alerts, and other parameters:

### Polling Schedules

```json
{
  "polling_schedules": {
    "critical_metrics": {
      "interval_seconds": 30,
      "enabled": true,
      "metrics": ["pd.soc", "pd.wattsOutSum", "pd.typec1Temp"]
    },
    "standard_metrics": {
      "interval_seconds": 300,
      "enabled": true,
      "metrics": "all"
    }
  }
}
```

### Alerts

```json
{
  "alerts": {
    "low_battery_threshold": 20,
    "high_temperature_threshold": 60,
    "high_power_threshold": 2000,
    "enabled": true
  }
}
```

## Usage Examples

### Modify Polling Schedule

```python
from ecoflow_monitor import EcoFlowMonitor

monitor = EcoFlowMonitor()

# Change critical metrics to every minute
monitor.update_polling_schedule("critical_metrics", interval_seconds=60)

# Disable standard metrics collection
monitor.update_polling_schedule("standard_metrics", enabled=False)
```

### Generate Different Dashboard Types

```bash
# Quick overview (2x2 layout)
python dashboard_generator.py --type quick --days 7

# Full comprehensive dashboard (4x2 layout)
python dashboard_generator.py --type full --days 30

# Energy analysis with cost estimates
python dashboard_generator.py --type energy --days 30

# Text-based usage report
python dashboard_generator.py --type report --days 7
```

### Custom Dashboard Output

```bash
# Save dashboard to specific file
python dashboard_generator.py --type quick --days 7 --output my_dashboard.html
```

## Data Collection

### Critical Metrics (Every 30 seconds)
- Battery State of Charge (SOC)
- Total power output
- Type-C1 temperature
- Battery temperature

### Standard Metrics (Every 5 minutes)
- All power outputs (Type-C, USB, Car, etc.)
- Energy accumulation (AC, DC, Solar charging)
- Charging status and types
- All temperature sensors
- Battery voltage and health

### Key Metrics Tracked

| Metric | Description | Unit |
|--------|-------------|------|
| `pd.wattsOutSum` | Total output power | Watts |
| `pd.wattsInSum` | Total input power | Watts |
| `pd.soc` | Battery level | % |
| `pd.typec1Watts` | Type-C1 output power | Watts |
| `pd.carWatts` | Car port output power | Watts |
| `pd.chgPowerAC` | Cumulative AC charging | Wh |
| `pd.chgSunPower` | Cumulative solar charging | Wh |
| `pd.typec1Temp` | Type-C1 temperature | °C |

## Dashboard Features

### Power Usage Tracking
- Real-time power consumption graphs
- Input vs output power comparison
- Peak usage identification

### Battery Health Monitoring
- SOC trends over time
- Battery temperature monitoring
- Charge/discharge cycles

### Energy Flow Analysis
- Solar vs AC vs DC charging breakdown
- Energy efficiency calculations
- Cost analysis (configurable rates)

### Usage Patterns
- Port utilization analysis
- Hourly usage heatmaps
- Daily/weekly patterns

## Alert System

The system monitors for:
- **Low Battery**: Below 20% (configurable)
- **High Temperature**: Above 60°C (configurable)
- **High Power Usage**: Above 2000W (configurable)
- **API Errors**: Connection or authentication issues

## Data Storage

- **Database**: SQLite (`ecoflow_data.db`)
- **Retention**: 90 days by default (configurable)
- **Automatic Cleanup**: Old data is automatically removed
- **Backup**: Daily summaries saved as JSON files

## Troubleshooting

### Common Issues

1. **API Authentication Error**
   - Verify your access key and secret key in `.env`
   - Check device serial number format

2. **No Data in Dashboard**
   - Ensure monitoring is running
   - Check database file exists
   - Verify device is online

3. **High CPU Usage**
   - Increase polling intervals in config
   - Disable unused metrics

### Logs

Check `ecoflow_monitor.log` for detailed system logs:
```bash
tail -f ecoflow_monitor.log
```

## Advanced Configuration

### Custom Metrics

Add specific metrics to critical monitoring:
```python
monitor.update_polling_schedule("critical_metrics", 
    metrics=["pd.soc", "pd.wattsOutSum", "pd.typec1Temp", "bms_bmsStatus.vol"])
```

### Database Management

```python
# Clean up old data
monitor.cleanup_old_data()

# Get historical data
df = monitor.get_historical_data(days=30)
```

### Custom Alerts

```python
# Check current alerts
alerts = monitor.check_alerts()
for alert in alerts:
    print(alert)
```

## API Reference

### EcoFlowMonitor Class

- `start_monitoring()`: Start data collection
- `stop_monitoring()`: Stop data collection
- `create_dashboard(days, save_path)`: Generate dashboard
- `get_historical_data(days)`: Retrieve historical data
- `check_alerts()`: Check for alert conditions
- `update_polling_schedule(name, **kwargs)`: Modify polling

### Dashboard Generator

- `--type`: Dashboard type (quick, full, energy, report)
- `--days`: Number of days to analyze
- `--output`: Output file path
- `--config`: Configuration file path

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests if applicable
5. Submit a pull request

## License

MIT License - see LICENSE file for details

## Support

For issues and questions:
1. Check the troubleshooting section
2. Review the logs
3. Open an issue on GitHub

## Changelog

### v1.0.0
- Initial release
- Basic monitoring and dashboard functionality
- Configurable polling schedules
- Alert system
- Energy analysis features 
