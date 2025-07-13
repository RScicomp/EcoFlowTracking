#!/usr/bin/env python3
"""
EcoFlow Dashboard Generator
Creates comprehensive visualizations from collected data
"""

import argparse
import sys
from datetime import datetime, timedelta
from ecoflow_monitor import EcoFlowMonitor
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import pandas as pd

def create_quick_dashboard(monitor, days=7, save_path=None):
    """Create a quick overview dashboard"""
    df = monitor.get_historical_data(days)
    
    if df.empty:
        print("No data available for dashboard")
        return None
    
    fig = make_subplots(
        rows=2, cols=2,
        subplot_titles=('Power Usage', 'Battery Level', 'Port Usage', 'Temperature'),
        specs=[[{"secondary_y": False}, {"secondary_y": False}],
               [{"secondary_y": False}, {"secondary_y": False}]]
    )
    
    # Power usage
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
    
    # Port usage
    port_usage = {
        'Type-C1': df['typec1_watts'].mean(),
        'Car': df['car_watts'].mean(),
        'USB1': df['usb1_watts'].mean(),
        'USB2': df['usb2_watts'].mean()
    }
    
    fig.add_trace(
        go.Bar(x=list(port_usage.keys()), y=list(port_usage.values()),
               name='Port Usage (W)'),
        row=2, col=1
    )
    
    # Temperature
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
    
    fig.update_layout(
        height=800,
        title_text=f"EcoFlow Quick Dashboard - Last {days} Days",
        showlegend=True
    )
    
    if save_path:
        fig.write_html(save_path)
        print(f"Dashboard saved to {save_path}")
    
    return fig

def create_energy_analysis(monitor, days=30, save_path=None):
    """Create detailed energy analysis"""
    df = monitor.get_historical_data(days)
    
    if df.empty:
        print("No data available for energy analysis")
        return None
    
    fig = make_subplots(
        rows=3, cols=2,
        subplot_titles=(
            'Daily Energy Consumption', 'Charging Sources',
            'Energy Efficiency', 'Peak Usage Times',
            'Battery Cycles', 'Cost Analysis'
        ),
        specs=[[{"secondary_y": False}, {"secondary_y": False}],
               [{"secondary_y": False}, {"secondary_y": False}],
               [{"secondary_y": False}, {"secondary_y": False}]]
    )
    
    # Daily energy consumption
    df['date'] = pd.to_datetime(df['timestamp']).dt.date
    daily_energy = df.groupby('date')['watts_out'].sum() / 1000  # Convert to kWh
    
    fig.add_trace(
        go.Bar(x=daily_energy.index, y=daily_energy.values,
               name='Daily Energy (kWh)'),
        row=1, col=1
    )
    
    # Charging sources
    charging_sources = {
        'AC Charging': df['chg_power_ac'].sum() / 1000,
        'DC Charging': df['chg_power_dc'].sum() / 1000,
        'Solar Charging': df['chg_sun_power'].sum() / 1000
    }
    
    fig.add_trace(
        go.Pie(labels=list(charging_sources.keys()),
               values=list(charging_sources.values()),
               name='Charging Sources'),
        row=1, col=2
    )
    
    # Energy efficiency over time
    df['efficiency'] = (df['watts_out'] / df['watts_in'].replace(0, 1)) * 100
    fig.add_trace(
        go.Scatter(x=df['timestamp'], y=df['efficiency'],
                  name='Efficiency %', line=dict(color='green')),
        row=2, col=1
    )
    
    # Peak usage times (heatmap)
    df['hour'] = pd.to_datetime(df['timestamp']).dt.hour
    df['day'] = pd.to_datetime(df['timestamp']).dt.day_name()
    hourly_usage = df.groupby(['day', 'hour'])['watts_out'].mean().unstack()
    
    fig.add_trace(
        go.Heatmap(z=hourly_usage.values, x=hourly_usage.columns,
                  y=hourly_usage.index, colorscale='Viridis'),
        row=2, col=2
    )
    
    # Battery cycles
    df['soc_change'] = df['soc'].diff()
    charge_cycles = len(df[df['soc_change'] > 10])  # Significant charge events
    discharge_cycles = len(df[df['soc_change'] < -10])  # Significant discharge events
    
    fig.add_trace(
        go.Bar(x=['Charge Cycles', 'Discharge Cycles'],
               y=[charge_cycles, discharge_cycles],
               name='Battery Cycles'),
        row=3, col=1
    )
    
    # Cost analysis (example with $0.12/kWh)
    total_energy = df['watts_out'].sum() / 1000
    estimated_cost = total_energy * 0.12
    
    fig.add_trace(
        go.Indicator(
            mode="gauge+number+delta",
            value=estimated_cost,
            title={'text': f"Estimated Cost (${0.12}/kWh)"},
            gauge={'axis': {'range': [None, estimated_cost * 1.2]},
                   'bar': {'color': "darkblue"},
                   'steps': [{'range': [0, estimated_cost * 0.5], 'color': "lightgray"},
                            {'range': [estimated_cost * 0.5, estimated_cost], 'color': "gray"}]}
        ),
        row=3, col=2
    )
    
    fig.update_layout(
        height=1200,
        title_text=f"Energy Analysis - Last {days} Days",
        showlegend=True
    )
    
    if save_path:
        fig.write_html(save_path)
        print(f"Energy analysis saved to {save_path}")
    
    return fig

def create_usage_report(monitor, days=7):
    """Generate a text-based usage report"""
    df = monitor.get_historical_data(days)
    
    if df.empty:
        print("No data available for report")
        return
    
    print(f"\n{'='*50}")
    print(f"ECOFLOW USAGE REPORT - Last {days} Days")
    print(f"{'='*50}")
    
    # Basic stats
    total_energy_out = df['watts_out'].sum() / 1000  # kWh
    total_energy_in = df['watts_in'].sum() / 1000    # kWh
    avg_soc = df['soc'].mean()
    peak_power = df['watts_out'].max()
    
    print(f"\n📊 BASIC STATISTICS:")
    print(f"   Total Energy Output: {total_energy_out:.2f} kWh")
    print(f"   Total Energy Input:  {total_energy_in:.2f} kWh")
    print(f"   Average Battery:     {avg_soc:.1f}%")
    print(f"   Peak Power Usage:    {peak_power}W")
    
    # Charging analysis
    ac_charging = df['chg_power_ac'].sum() / 1000
    dc_charging = df['chg_power_dc'].sum() / 1000
    solar_charging = df['chg_sun_power'].sum() / 1000
    
    print(f"\n🔋 CHARGING ANALYSIS:")
    print(f"   AC Charging:         {ac_charging:.2f} kWh")
    print(f"   DC Charging:         {dc_charging:.2f} kWh")
    print(f"   Solar Charging:      {solar_charging:.2f} kWh")
    
    # Port usage
    print(f"\n🔌 PORT USAGE (Average Watts):")
    print(f"   Type-C1:             {df['typec1_watts'].mean():.1f}W")
    print(f"   Car Port:            {df['car_watts'].mean():.1f}W")
    print(f"   USB1:                {df['usb1_watts'].mean():.1f}W")
    print(f"   USB2:                {df['usb2_watts'].mean():.1f}W")
    print(f"   QC-USB1:             {df['qc_usb1_watts'].mean():.1f}W")
    print(f"   QC-USB2:             {df['qc_usb2_watts'].mean():.1f}W")
    print(f"   Type-C2:             {df['typec2_watts'].mean():.1f}W")
    
    # Temperature stats
    print(f"\n🌡️  TEMPERATURE STATISTICS:")
    print(f"   Type-C1 Avg Temp:    {df['typec1_temp'].mean():.1f}°C")
    print(f"   Car Port Avg Temp:   {df['car_temp'].mean():.1f}°C")
    print(f"   Max Type-C1 Temp:    {df['typec1_temp'].max():.1f}°C")
    print(f"   Max Car Temp:        {df['car_temp'].max():.1f}°C")
    
    # Efficiency
    efficiency = (total_energy_out / max(total_energy_in, 0.001)) * 100
    print(f"\n⚡ EFFICIENCY:")
    print(f"   Overall Efficiency:  {efficiency:.1f}%")
    
    # Usage patterns
    df['hour'] = pd.to_datetime(df['timestamp']).dt.hour
    peak_hour = df.groupby('hour')['watts_out'].mean().idxmax()
    print(f"\n📈 USAGE PATTERNS:")
    print(f"   Peak Usage Hour:     {peak_hour}:00")
    
    # Cost estimate
    estimated_cost = total_energy_out * 0.12  # $0.12/kWh
    print(f"\n💰 COST ESTIMATE:")
    print(f"   Estimated Cost:      ${estimated_cost:.2f} (at $0.12/kWh)")
    
    print(f"\n{'='*50}")

def main():
    parser = argparse.ArgumentParser(description='EcoFlow Dashboard Generator')
    parser.add_argument('--days', type=int, default=7, help='Number of days to analyze')
    parser.add_argument('--type', choices=['quick', 'full', 'energy', 'report'], 
                       default='quick', help='Type of dashboard to generate')
    parser.add_argument('--output', type=str, help='Output file path')
    parser.add_argument('--config', type=str, default='config.json', help='Configuration file')
    
    args = parser.parse_args()
    
    try:
        monitor = EcoFlowMonitor(args.config)
        
        if args.type == 'quick':
            fig = create_quick_dashboard(monitor, args.days, args.output)
        elif args.type == 'full':
            fig = monitor.create_dashboard(args.days, args.output)
        elif args.type == 'energy':
            fig = create_energy_analysis(monitor, args.days, args.output)
        elif args.type == 'report':
            create_usage_report(monitor, args.days)
            return
        
        if fig:
            fig.show()
            
    except Exception as e:
        print(f"Error generating dashboard: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main() 