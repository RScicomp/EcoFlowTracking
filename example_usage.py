#!/usr/bin/env python3
"""
Example usage of the EcoFlow Delta 2 Monitoring System
Demonstrates various configuration and usage scenarios
"""

import time
import json
from ecoflow_monitor import EcoFlowMonitor

def example_basic_monitoring():
    """Basic monitoring example"""
    print("=== Basic Monitoring Example ===")
    
    # Initialize monitor with default config
    monitor = EcoFlowMonitor()
    
    # Start monitoring
    monitor.start_monitoring()
    
    print("Monitoring started. Press Ctrl+C to stop.")
    print("Check ecoflow_monitor.log for detailed logs.")
    
    try:
        # Keep running for 60 seconds as example
        time.sleep(60)
    except KeyboardInterrupt:
        pass
    finally:
        monitor.stop_monitoring()
        print("Monitoring stopped.")

def example_custom_polling():
    """Example with custom polling schedules"""
    print("=== Custom Polling Example ===")
    
    monitor = EcoFlowMonitor()
    
    # Modify polling schedules
    print("Updating polling schedules...")
    
    # Critical metrics every 60 seconds instead of 30
    monitor.update_polling_schedule("critical_metrics", interval_seconds=60)
    
    # Standard metrics every 10 minutes instead of 5
    monitor.update_polling_schedule("standard_metrics", interval_seconds=600)
    
    # Add custom metrics to critical monitoring
    custom_metrics = [
        "pd.soc", 
        "pd.wattsOutSum", 
        "pd.typec1Temp", 
        "bms_bmsStatus.temp",
        "pd.carWatts"  # Add car port monitoring
    ]
    monitor.update_polling_schedule("critical_metrics", metrics=custom_metrics)
    
    print("Updated polling schedules:")
    print(json.dumps(monitor.config["polling_schedules"], indent=2))
    
    # Start monitoring with custom settings
    monitor.start_monitoring()
    
    try:
        time.sleep(30)  # Run for 30 seconds
    except KeyboardInterrupt:
        pass
    finally:
        monitor.stop_monitoring()

def example_dashboard_generation():
    """Example of generating different dashboard types"""
    print("=== Dashboard Generation Example ===")
    
    monitor = EcoFlowMonitor()
    
    # Generate different types of dashboards
    print("Generating dashboards...")
    
    # Quick dashboard for last 7 days
    fig = monitor.create_dashboard(days=7, save_path="dashboard_7days.html")
    if fig:
        print("✓ 7-day dashboard generated")
    
    # Full dashboard for last 30 days
    fig = monitor.create_dashboard(days=30, save_path="dashboard_30days.html")
    if fig:
        print("✓ 30-day dashboard generated")
    
    # Check if we have data
    df = monitor.get_historical_data(days=7)
    if not df.empty:
        print(f"✓ Found {len(df)} data points")
        print(f"  Date range: {df['timestamp'].min()} to {df['timestamp'].max()}")
    else:
        print("⚠ No data available - start monitoring first")

def example_alert_configuration():
    """Example of configuring alerts"""
    print("=== Alert Configuration Example ===")
    
    monitor = EcoFlowMonitor()
    
    # Update alert thresholds
    print("Configuring custom alerts...")
    
    monitor.config["alerts"]["low_battery_threshold"] = 15  # Alert at 15% instead of 20%
    monitor.config["alerts"]["high_temperature_threshold"] = 70  # Alert at 70°C instead of 60°C
    monitor.config["alerts"]["high_power_threshold"] = 1500  # Alert at 1500W instead of 2000W
    
    # Save the updated config
    monitor.save_config(monitor.config, "config.json")
    
    print("Updated alert thresholds:")
    print(json.dumps(monitor.config["alerts"], indent=2))
    
    # Test alerts
    print("\nTesting alerts...")
    alerts = monitor.check_alerts()
    if alerts:
        for alert in alerts:
            print(f"  {alert}")
    else:
        print("  No alerts triggered")

def example_data_analysis():
    """Example of analyzing collected data"""
    print("=== Data Analysis Example ===")
    
    monitor = EcoFlowMonitor()
    
    # Get historical data
    df = monitor.get_historical_data(days=7)
    
    if df.empty:
        print("No data available. Start monitoring first.")
        return
    
    print(f"Analyzing {len(df)} data points from the last 7 days...")
    
    # Basic statistics
    print("\n📊 Basic Statistics:")
    print(f"  Total Energy Output: {df['watts_out'].sum() / 1000:.2f} kWh")
    print(f"  Total Energy Input:  {df['watts_in'].sum() / 1000:.2f} kWh")
    print(f"  Average Battery:     {df['soc'].mean():.1f}%")
    print(f"  Peak Power Usage:    {df['watts_out'].max()}W")
    
    # Port usage analysis
    print("\n🔌 Port Usage (Average Watts):")
    ports = {
        'Type-C1': df['typec1_watts'].mean(),
        'Car': df['car_watts'].mean(),
        'USB1': df['usb1_watts'].mean(),
        'USB2': df['usb2_watts'].mean(),
        'QC-USB1': df['qc_usb1_watts'].mean(),
        'QC-USB2': df['qc_usb2_watts'].mean(),
        'Type-C2': df['typec2_watts'].mean()
    }
    
    for port, watts in ports.items():
        print(f"  {port:12}: {watts:6.1f}W")
    
    # Most used port
    most_used = max(ports.items(), key=lambda x: x[1])
    print(f"\n  Most used port: {most_used[0]} ({most_used[1]:.1f}W)")
    
    # Temperature analysis
    print("\n🌡️ Temperature Analysis:")
    print(f"  Type-C1 Avg: {df['typec1_temp'].mean():.1f}°C (Max: {df['typec1_temp'].max():.1f}°C)")
    print(f"  Car Port Avg: {df['car_temp'].mean():.1f}°C (Max: {df['car_temp'].max():.1f}°C)")
    
    # Efficiency calculation
    efficiency = (df['watts_out'].sum() / max(df['watts_in'].sum(), 1)) * 100
    print(f"\n⚡ Efficiency: {efficiency:.1f}%")

def example_energy_cost_analysis():
    """Example of energy cost analysis"""
    print("=== Energy Cost Analysis Example ===")
    
    monitor = EcoFlowMonitor()
    
    # Get data for different time periods
    periods = [1, 7, 30]  # days
    
    for days in periods:
        df = monitor.get_historical_data(days)
        
        if df.empty:
            print(f"No data for {days} day(s)")
            continue
        
        total_energy = df['watts_out'].sum() / 1000  # kWh
        
        # Different electricity rates
        rates = {
            "Residential": 0.12,
            "Peak Hours": 0.18,
            "Off-Peak": 0.08,
            "Solar Credit": -0.05  # Negative for solar generation
        }
        
        print(f"\n💰 Cost Analysis - Last {days} day(s):")
        print(f"  Total Energy: {total_energy:.2f} kWh")
        
        for rate_name, rate in rates.items():
            cost = total_energy * rate
            print(f"  {rate_name:12}: ${cost:6.2f} (${rate:.2f}/kWh)")
        
        # Solar vs grid charging
        solar_energy = df['chg_sun_power'].sum() / 1000
        grid_energy = df['chg_power_ac'].sum() / 1000
        
        if solar_energy > 0:
            solar_savings = solar_energy * 0.12  # Assuming grid rate
            print(f"  Solar Savings: ${solar_savings:.2f} (from {solar_energy:.2f} kWh solar)")

def example_cleanup_and_maintenance():
    """Example of database cleanup and maintenance"""
    print("=== Database Maintenance Example ===")
    
    monitor = EcoFlowMonitor()
    
    # Clean up old data
    print("Cleaning up old data...")
    monitor.cleanup_old_data()
    
    # Check database size
    import os
    db_path = monitor.config["database"]["path"]
    if os.path.exists(db_path):
        size_mb = os.path.getsize(db_path) / (1024 * 1024)
        print(f"Database size: {size_mb:.2f} MB")
    
    # Generate daily summary
    print("Generating daily summary...")
    monitor.generate_daily_summary()

def main():
    """Run all examples"""
    print("EcoFlow Delta 2 Monitoring System - Examples")
    print("=" * 50)
    
    examples = [
        ("Basic Monitoring", example_basic_monitoring),
        ("Custom Polling", example_custom_polling),
        ("Dashboard Generation", example_dashboard_generation),
        ("Alert Configuration", example_alert_configuration),
        ("Data Analysis", example_data_analysis),
        ("Energy Cost Analysis", example_energy_cost_analysis),
        ("Database Maintenance", example_cleanup_and_maintenance)
    ]
    
    for i, (name, func) in enumerate(examples, 1):
        print(f"\n{i}. {name}")
        try:
            func()
        except Exception as e:
            print(f"Error in {name}: {e}")
        
        print("\n" + "-" * 30)
    
    print("\nAll examples completed!")

if __name__ == "__main__":
    main() 