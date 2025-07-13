#!/usr/bin/env python3
"""
EcoFlow Web Server
Provides web interface and API endpoints for EcoFlow monitoring with AI assistant
"""

from flask import Flask, render_template, jsonify, request, send_from_directory
from flask_cors import CORS
import json
import os
from datetime import datetime, timedelta
import pandas as pd
from ecoflow_monitor import EcoFlowMonitor
from ai_assistant import EcoFlowAIAssistant
import logging

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize Flask app
app = Flask(__name__)
CORS(app)  # Enable CORS for all routes

# Initialize EcoFlow monitor and AI assistant
monitor = EcoFlowMonitor()
ai_assistant = EcoFlowAIAssistant(monitor)

@app.route('/')
def dashboard():
    """Serve the main dashboard"""
    return send_from_directory('.', 'ai_dashboard.html')

@app.route('/api/current-status')
def current_status():
    """Get current device status"""
    try:
        status = ai_assistant.analyze_current_status()
        if 'error' in status:
            return jsonify({'error': status['error']}), 500
        
        # Add online status
        status['online'] = True
        return jsonify(status)
    except Exception as e:
        logger.error(f"Error getting current status: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/ai-insights')
def ai_insights():
    """Get AI-generated insights"""
    try:
        current = ai_assistant.analyze_current_status()
        historical = ai_assistant.analyze_historical_patterns(7)
        
        if 'error' in current:
            return jsonify({'error': current['error']}), 500
        
        insights = {
            'current_status': current,
            'historical_analysis': historical,
            'timestamp': datetime.now().isoformat()
        }
        
        return jsonify(insights)
    except Exception as e:
        logger.error(f"Error getting AI insights: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/chart-data')
def chart_data():
    """Get chart data for visualization"""
    try:
        days = int(request.args.get('days', 7))
        df = monitor.get_historical_data(days)
        
        if df.empty:
            return jsonify({
                'timestamps': [],
                'power_out': [],
                'power_in': [],
                'battery_level': [],
                'temperature': []
            })
        
        # Prepare data for charts
        data = {
            'timestamps': df['timestamp'].dt.strftime('%Y-%m-%d %H:%M:%S').tolist(),
            'power_out': df['watts_out'].tolist(),
            'power_in': df['watts_in'].tolist(),
            'battery_level': df['soc'].tolist(),
            'temperature': df['typec1_temp'].tolist()
        }
        
        return jsonify(data)
    except Exception as e:
        logger.error(f"Error getting chart data: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/recommendations')
def recommendations():
    """Get AI recommendations"""
    try:
        recommendations = ai_assistant.generate_smart_recommendations()
        if 'error' in recommendations:
            return jsonify({'error': recommendations['error']}), 500
        
        return jsonify(recommendations)
    except Exception as e:
        logger.error(f"Error getting recommendations: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/ai-query', methods=['POST'])
def ai_query():
    """Handle natural language queries"""
    try:
        data = request.get_json()
        query = data.get('query', '')
        
        if not query:
            return jsonify({'error': 'No query provided'}), 400
        
        answer = ai_assistant.answer_natural_language_query(query)
        if 'error' in answer:
            return jsonify({'error': answer['error']}), 500
        
        return jsonify(answer)
    except Exception as e:
        logger.error(f"Error processing AI query: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/predictions')
def predictions():
    """Get energy predictions"""
    try:
        hours = int(request.args.get('hours', 24))
        prediction = ai_assistant.predict_energy_needs(hours)
        
        if 'error' in prediction:
            return jsonify({'error': prediction['error']}), 500
        
        return jsonify(prediction)
    except Exception as e:
        logger.error(f"Error getting predictions: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/export-data')
def export_data():
    """Export data in various formats"""
    try:
        format_type = request.args.get('format', 'json')
        days = int(request.args.get('days', 7))
        
        df = monitor.get_historical_data(days)
        
        if df.empty:
            return jsonify({'error': 'No data available for export'}), 404
        
        if format_type == 'csv':
            csv_data = df.to_csv(index=False)
            return csv_data, 200, {'Content-Type': 'text/csv', 'Content-Disposition': f'attachment; filename=ecoflow_data_{days}days.csv'}
        elif format_type == 'json':
            return jsonify(df.to_dict('records'))
        else:
            return jsonify({'error': 'Unsupported format'}), 400
            
    except Exception as e:
        logger.error(f"Error exporting data: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/device-info')
def device_info():
    """Get device information"""
    try:
        data = monitor.get_all_quotas()
        if data.get('code') != '0':
            return jsonify({'error': 'Unable to fetch device data'}), 500
        
        device_data = data['data']
        
        info = {
            'model': device_data.get('pd.model', 'Unknown'),
            'serial_number': monitor.device_sn,
            'firmware_version': device_data.get('pd.sysVer', 'Unknown'),
            'battery_capacity': device_data.get('bms_bmsStatus.designCap', 0),
            'cycles': device_data.get('bms_bmsStatus.cycles', 0),
            'online': True,
            'last_update': datetime.now().isoformat()
        }
        
        return jsonify(info)
    except Exception as e:
        logger.error(f"Error getting device info: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/health')
def health_check():
    """Health check endpoint"""
    try:
        # Test API connection
        data = monitor.get_all_quotas()
        online = data.get('code') == '0'
        
        return jsonify({
            'status': 'healthy',
            'online': online,
            'timestamp': datetime.now().isoformat(),
            'version': '1.0.0'
        })
    except Exception as e:
        return jsonify({
            'status': 'unhealthy',
            'error': str(e),
            'timestamp': datetime.now().isoformat()
        }), 500

@app.route('/api/analytics')
def analytics():
    """Get comprehensive analytics"""
    try:
        days = int(request.args.get('days', 7))
        
        # Get various analyses
        current = ai_assistant.analyze_current_status()
        historical = ai_assistant.analyze_historical_patterns(days)
        predictions = ai_assistant.predict_energy_needs(24)
        recommendations = ai_assistant.generate_smart_recommendations()
        
        analytics_data = {
            'current_status': current,
            'historical_analysis': historical,
            'predictions': predictions,
            'recommendations': recommendations,
            'summary': {
                'total_records': len(monitor.get_historical_data(days)),
                'analysis_period_days': days,
                'generated_at': datetime.now().isoformat()
            }
        }
        
        return jsonify(analytics_data)
    except Exception as e:
        logger.error(f"Error getting analytics: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/compare')
def compare_data():
    """Compare data between different time periods"""
    try:
        period1 = request.args.get('period1', '7')  # days
        period2 = request.args.get('period2', '14')  # days
        
        df1 = monitor.get_historical_data(int(period1))
        df2 = monitor.get_historical_data(int(period2))
        
        if df1.empty or df2.empty:
            return jsonify({'error': 'Insufficient data for comparison'}), 404
        
        comparison = {
            'period1': {
                'days': period1,
                'avg_daily_usage': df1['watts_out'].sum() / 1000 / len(df1['timestamp'].dt.date.unique()),
                'avg_battery': df1['soc'].mean(),
                'peak_power': df1['watts_out'].max()
            },
            'period2': {
                'days': period2,
                'avg_daily_usage': df2['watts_out'].sum() / 1000 / len(df2['timestamp'].dt.date.unique()),
                'avg_battery': df2['soc'].mean(),
                'peak_power': df2['watts_out'].max()
            },
            'changes': {
                'usage_change_percent': 0,  # Calculate percentage change
                'battery_change_percent': 0,
                'peak_power_change_percent': 0
            }
        }
        
        # Calculate changes
        if comparison['period1']['avg_daily_usage'] > 0:
            comparison['changes']['usage_change_percent'] = (
                (comparison['period2']['avg_daily_usage'] - comparison['period1']['avg_daily_usage']) / 
                comparison['period1']['avg_daily_usage'] * 100
            )
        
        return jsonify(comparison)
    except Exception as e:
        logger.error(f"Error comparing data: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/alerts')
def get_alerts():
    """Get current alerts"""
    try:
        alerts = monitor.check_alerts()
        current = ai_assistant.analyze_current_status()
        
        alert_data = {
            'system_alerts': alerts,
            'ai_alerts': [],
            'timestamp': datetime.now().isoformat()
        }
        
        # Add AI-generated alerts based on current status
        if 'battery_status' in current:
            soc = current['battery_status'].get('soc', 100)
            if soc < 20:
                alert_data['ai_alerts'].append({
                    'type': 'critical',
                    'message': f'Battery critically low at {soc}%',
                    'category': 'battery'
                })
            elif soc < 30:
                alert_data['ai_alerts'].append({
                    'type': 'warning',
                    'message': f'Battery low at {soc}%',
                    'category': 'battery'
                })
        
        if 'temperature' in current:
            temp = current['temperature'].get('temperature', 0)
            if temp > 50:
                alert_data['ai_alerts'].append({
                    'type': 'warning',
                    'message': f'High temperature detected: {temp}°C',
                    'category': 'temperature'
                })
        
        return jsonify(alert_data)
    except Exception as e:
        logger.error(f"Error getting alerts: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/config')
def get_config():
    """Get current configuration"""
    try:
        return jsonify(monitor.config)
    except Exception as e:
        logger.error(f"Error getting config: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/config', methods=['POST'])
def update_config():
    """Update configuration"""
    try:
        data = request.get_json()
        
        # Update specific configuration sections
        if 'polling_schedules' in data:
            for schedule_name, schedule_data in data['polling_schedules'].items():
                monitor.update_polling_schedule(schedule_name, **schedule_data)
        
        return jsonify({'message': 'Configuration updated successfully'})
    except Exception as e:
        logger.error(f"Error updating config: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/generate-report', methods=['POST'])
def generate_report():
    """Generate comprehensive report with AI insights"""
    try:
        data = request.get_json() or {}
        report_type = data.get('type', 'html')  # html, pdf, json
        days = data.get('days', 7)
        include_charts = data.get('include_charts', True)
        include_ai_insights = data.get('include_ai_insights', True)
        
        # Get all the data we need
        current_status = ai_assistant.analyze_current_status()
        historical_analysis = ai_assistant.analyze_historical_patterns(days)
        predictions = ai_assistant.predict_energy_needs(24)
        recommendations = ai_assistant.generate_smart_recommendations()
        device_info = get_device_info_data()
        
        # Get historical data for charts
        df = monitor.get_historical_data(days)
        
        # Create report data structure
        report_data = {
            'metadata': {
                'generated_at': datetime.now().isoformat(),
                'report_type': report_type,
                'analysis_period_days': days,
                'device_info': device_info
            },
            'current_status': current_status,
            'historical_analysis': historical_analysis,
            'predictions': predictions,
            'recommendations': recommendations,
            'summary': generate_report_summary(current_status, historical_analysis, predictions, recommendations)
        }
        
        if report_type == 'json':
            return jsonify(report_data)
        elif report_type == 'html':
            html_report = generate_html_report(report_data, df, include_charts, include_ai_insights)
            return html_report, 200, {'Content-Type': 'text/html'}
        elif report_type == 'pdf':
            # For PDF, we'd need additional libraries like reportlab or weasyprint
            # For now, return HTML that can be printed to PDF
            html_report = generate_html_report(report_data, df, include_charts, include_ai_insights)
            return html_report, 200, {'Content-Type': 'text/html', 'Content-Disposition': 'attachment; filename=ecoflow_report.html'}
        else:
            return jsonify({'error': 'Unsupported report type'}), 400
            
    except Exception as e:
        logger.error(f"Error generating report: {e}")
        return jsonify({'error': str(e)}), 500

def get_device_info_data():
    """Get device information for the report"""
    try:
        data = monitor.get_all_quotas()
        if data.get('code') != '0':
            return {'error': 'Unable to fetch device data'}
        
        device_data = data['data']
        
        return {
            'model': device_data.get('pd.model', 'Unknown'),
            'serial_number': monitor.device_sn,
            'firmware_version': device_data.get('pd.sysVer', 'Unknown'),
            'battery_capacity': device_data.get('bms_bmsStatus.designCap', 0),
            'cycles': device_data.get('bms_bmsStatus.cycles', 0),
            'online': True
        }
    except Exception as e:
        logger.error(f"Error getting device info: {e}")
        return {'error': str(e)}

def generate_report_summary(current_status, historical_analysis, predictions, recommendations):
    """Generate a summary for the report"""
    summary = {
        'key_metrics': {},
        'insights': [],
        'actions_required': [],
        'trends': {}
    }
    
    # Key metrics
    if 'battery_status' in current_status:
        summary['key_metrics']['battery_level'] = current_status['battery_status'].get('soc', 0)
        summary['key_metrics']['battery_health'] = current_status['battery_health'].get('health_score', 0)
    
    if 'power_usage' in current_status:
        summary['key_metrics']['current_power'] = current_status['power_usage'].get('current_output', 0)
        summary['key_metrics']['power_status'] = current_status['power_usage'].get('status', 'unknown')
    
    # Historical insights
    if 'usage_patterns' in historical_analysis:
        patterns = historical_analysis['usage_patterns']
        summary['key_metrics']['avg_daily_usage'] = patterns.get('average_daily_usage_kwh', 0)
        summary['key_metrics']['peak_usage_hour'] = patterns.get('peak_usage_hour', 0)
    
    if 'efficiency_analysis' in historical_analysis:
        efficiency = historical_analysis['efficiency_analysis']
        summary['key_metrics']['avg_efficiency'] = efficiency.get('average_efficiency', 0)
        summary['insights'].append(f"Average efficiency: {efficiency.get('average_efficiency', 0):.1f}%")
    
    # Predictions
    if 'total_predicted_kwh' in predictions:
        summary['key_metrics']['predicted_usage'] = predictions.get('total_predicted_kwh', 0)
        summary['insights'].append(f"Predicted energy needs: {predictions.get('total_predicted_kwh', 0):.2f} kWh")
    
    # Recommendations
    if 'immediate_actions' in recommendations and recommendations['immediate_actions']:
        summary['actions_required'].extend([rec['action'] for rec in recommendations['immediate_actions']])
    
    if 'optimization_tips' in recommendations and recommendations['optimization_tips']:
        summary['insights'].extend([rec['action'] for rec in recommendations['optimization_tips']])
    
    return summary

def generate_html_report(report_data, df, include_charts, include_ai_insights):
    """Generate HTML report"""
    
    # Create chart data if requested
    chart_data = ""
    if include_charts and not df.empty:
        chart_data = generate_chart_html(df)
    
    html_template = f"""
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>EcoFlow Delta 2 - Energy Report</title>
        <script src="https://cdn.plot.ly/plotly-latest.min.js"></script>
        <style>
            body {{
                font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
                line-height: 1.6;
                color: #333;
                max-width: 1200px;
                margin: 0 auto;
                padding: 20px;
                background: #f5f5f5;
            }}
            .header {{
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                color: white;
                padding: 30px;
                border-radius: 10px;
                text-align: center;
                margin-bottom: 30px;
            }}
            .header h1 {{
                margin: 0;
                font-size: 2.5em;
            }}
            .header p {{
                margin: 10px 0 0 0;
                opacity: 0.9;
            }}
            .section {{
                background: white;
                padding: 25px;
                margin-bottom: 20px;
                border-radius: 10px;
                box-shadow: 0 2px 10px rgba(0,0,0,0.1);
            }}
            .section h2 {{
                color: #2c3e50;
                border-bottom: 3px solid #667eea;
                padding-bottom: 10px;
                margin-bottom: 20px;
            }}
            .metrics-grid {{
                display: grid;
                grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
                gap: 20px;
                margin-bottom: 20px;
            }}
            .metric-card {{
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                color: white;
                padding: 20px;
                border-radius: 10px;
                text-align: center;
            }}
            .metric-value {{
                font-size: 2em;
                font-weight: bold;
                margin-bottom: 5px;
            }}
            .metric-label {{
                font-size: 0.9em;
                opacity: 0.9;
            }}
            .insights-list {{
                background: #f8f9fa;
                padding: 20px;
                border-radius: 10px;
                border-left: 5px solid #667eea;
            }}
            .insights-list h3 {{
                color: #2c3e50;
                margin-top: 0;
            }}
            .insights-list ul {{
                margin: 0;
                padding-left: 20px;
            }}
            .insights-list li {{
                margin-bottom: 10px;
            }}
            .recommendations {{
                display: grid;
                grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
                gap: 15px;
            }}
            .recommendation {{
                background: #fff3cd;
                border: 1px solid #ffeaa7;
                padding: 15px;
                border-radius: 8px;
            }}
            .recommendation.high {{
                background: #f8d7da;
                border-color: #f5c6cb;
            }}
            .recommendation.medium {{
                background: #fff3cd;
                border-color: #ffeaa7;
            }}
            .recommendation.low {{
                background: #d1ecf1;
                border-color: #bee5eb;
            }}
            .chart-container {{
                height: 400px;
                margin: 20px 0;
            }}
            .summary-box {{
                background: #e8f5e8;
                border: 1px solid #c3e6c3;
                padding: 20px;
                border-radius: 10px;
                margin-bottom: 20px;
            }}
            .summary-box h3 {{
                color: #2c3e50;
                margin-top: 0;
            }}
            .device-info {{
                background: #f8f9fa;
                padding: 15px;
                border-radius: 8px;
                margin-bottom: 20px;
            }}
            .device-info table {{
                width: 100%;
                border-collapse: collapse;
            }}
            .device-info td {{
                padding: 8px;
                border-bottom: 1px solid #dee2e6;
            }}
            .device-info td:first-child {{
                font-weight: bold;
                width: 30%;
            }}
            @media print {{
                body {{ background: white; }}
                .section {{ box-shadow: none; border: 1px solid #ddd; }}
            }}
        </style>
    </head>
    <body>
        <div class="header">
            <h1>🏠 EcoFlow Delta 2 Energy Report</h1>
            <p>Generated on {report_data['metadata']['generated_at'][:19].replace('T', ' ')} | Analysis Period: {report_data['metadata']['analysis_period_days']} days</p>
        </div>

        <div class="section">
            <h2>📊 Executive Summary</h2>
            <div class="summary-box">
                <h3>Key Findings</h3>
                <ul>
                    <li><strong>Battery Level:</strong> {report_data['summary']['key_metrics'].get('battery_level', 'N/A')}%</li>
                    <li><strong>Current Power Output:</strong> {report_data['summary']['key_metrics'].get('current_power', 'N/A')}W</li>
                    <li><strong>Average Daily Usage:</strong> {report_data['summary']['key_metrics'].get('avg_daily_usage', 'N/A'):.2f} kWh</li>
                    <li><strong>System Efficiency:</strong> {report_data['summary']['key_metrics'].get('avg_efficiency', 'N/A'):.1f}%</li>
                </ul>
            </div>
        </div>

        <div class="section">
            <h2>🔧 Device Information</h2>
            <div class="device-info">
                <table>
                    <tr><td>Model:</td><td>{report_data['metadata']['device_info'].get('model', 'Unknown')}</td></tr>
                    <tr><td>Serial Number:</td><td>{report_data['metadata']['device_info'].get('serial_number', 'Unknown')}</td></tr>
                    <tr><td>Firmware Version:</td><td>{report_data['metadata']['device_info'].get('firmware_version', 'Unknown')}</td></tr>
                    <tr><td>Battery Capacity:</td><td>{report_data['metadata']['device_info'].get('battery_capacity', 'Unknown')} mAh</td></tr>
                    <tr><td>Charge Cycles:</td><td>{report_data['metadata']['device_info'].get('cycles', 'Unknown')}</td></tr>
                    <tr><td>Status:</td><td>{'Online' if report_data['metadata']['device_info'].get('online', False) else 'Offline'}</td></tr>
                </table>
            </div>
        </div>

        <div class="section">
            <h2>📈 Current Status</h2>
            <div class="metrics-grid">
                <div class="metric-card">
                    <div class="metric-value">{report_data['current_status'].get('battery_status', {}).get('soc', '--')}%</div>
                    <div class="metric-label">Battery Level</div>
                </div>
                <div class="metric-card">
                    <div class="metric-value">{report_data['current_status'].get('power_usage', {}).get('current_output', '--')}W</div>
                    <div class="metric-label">Power Output</div>
                </div>
                <div class="metric-card">
                    <div class="metric-value">{report_data['current_status'].get('temperature', {}).get('temperature', '--')}°C</div>
                    <div class="metric-label">Temperature</div>
                </div>
                <div class="metric-card">
                    <div class="metric-value">{report_data['current_status'].get('battery_health', {}).get('health_score', '--'):.1f}%</div>
                    <div class="metric-label">Battery Health</div>
                </div>
            </div>
        </div>

        {chart_data if include_charts else ''}

        {generate_ai_insights_html(report_data) if include_ai_insights else ''}

        <div class="section">
            <h2>🎯 AI Recommendations</h2>
            <div class="recommendations">
                {generate_recommendations_html(report_data['recommendations'])}
            </div>
        </div>

        <div class="section">
            <h2>🔮 Energy Predictions</h2>
            <div class="insights-list">
                <h3>Next 24 Hours Forecast</h3>
                <ul>
                    <li><strong>Predicted Energy Needs:</strong> {report_data['predictions'].get('total_predicted_kwh', 0):.2f} kWh</li>
                    <li><strong>Confidence Level:</strong> {report_data['predictions'].get('confidence_level', 'Unknown')}</li>
                    <li><strong>Factors Considered:</strong> {', '.join(report_data['predictions'].get('factors', ['None identified']))}</li>
                </ul>
            </div>
        </div>

        <div class="section">
            <h2>📋 Report Metadata</h2>
            <div class="device-info">
                <table>
                    <tr><td>Report Generated:</td><td>{report_data['metadata']['generated_at'][:19].replace('T', ' ')}</td></tr>
                    <tr><td>Analysis Period:</td><td>{report_data['metadata']['analysis_period_days']} days</td></tr>
                    <tr><td>Report Type:</td><td>{report_data['metadata']['report_type'].upper()}</td></tr>
                    <tr><td>Data Points Analyzed:</td><td>{len(df) if not df.empty else 0}</td></tr>
                </table>
            </div>
        </div>

        <script>
            // Auto-resize charts for better printing
            window.addEventListener('load', function() {{
                if (typeof Plotly !== 'undefined') {{
                    Plotly.Plots.resize();
                }}
            }});
        </script>
    </body>
    </html>
    """
    
    return html_template

def generate_chart_html(df):
    """Generate HTML for charts"""
    if df.empty:
        return ""
    
    # Prepare chart data
    timestamps = df['timestamp'].dt.strftime('%Y-%m-%d %H:%M:%S').tolist()
    power_out = df['watts_out'].tolist()
    power_in = df['watts_in'].tolist()
    battery_level = df['soc'].tolist()
    
    chart_html = f"""
    <div class="section">
        <h2>📊 Usage Charts</h2>
        <div class="chart-container" id="powerChart"></div>
        <div class="chart-container" id="batteryChart"></div>
    </div>

    <script>
        // Power Usage Chart
        const powerData = [
            {{
                x: {timestamps},
                y: {power_out},
                type: 'scatter',
                mode: 'lines+markers',
                name: 'Power Out',
                line: {{ color: '#e74c3c' }}
            }},
            {{
                x: {timestamps},
                y: {power_in},
                type: 'scatter',
                mode: 'lines+markers',
                name: 'Power In',
                line: {{ color: '#27ae60' }}
            }}
        ];

        const powerLayout = {{
            title: 'Power Usage Over Time',
            xaxis: {{ title: 'Time' }},
            yaxis: {{ title: 'Power (W)' }},
            hovermode: 'closest',
            showlegend: true,
            height: 400
        }};

        Plotly.newPlot('powerChart', powerData, powerLayout);

        // Battery Level Chart
        const batteryData = [
            {{
                x: {timestamps},
                y: {battery_level},
                type: 'scatter',
                mode: 'lines+markers',
                name: 'Battery Level',
                line: {{ color: '#3498db' }},
                fill: 'tonexty'
            }}
        ];

        const batteryLayout = {{
            title: 'Battery Level Over Time',
            xaxis: {{ title: 'Time' }},
            yaxis: {{ title: 'Battery Level (%)', range: [0, 100] }},
            hovermode: 'closest',
            showlegend: true,
            height: 400
        }};

        Plotly.newPlot('batteryChart', batteryData, batteryLayout);
    </script>
    """
    
    return chart_html

def generate_ai_insights_html(report_data):
    """Generate HTML for AI insights"""
    insights = []
    
    # Add insights from summary
    if 'insights' in report_data['summary']:
        insights.extend(report_data['summary']['insights'])
    
    # Add insights from historical analysis
    if 'usage_patterns' in report_data['historical_analysis']:
        patterns = report_data['historical_analysis']['usage_patterns']
        insights.append(f"Peak usage occurs at {patterns.get('peak_usage_hour', 0)}:00 hours")
        insights.append(f"Usage variability: {patterns.get('usage_variability', 0):.2f}")
    
    if 'efficiency_analysis' in report_data['historical_analysis']:
        efficiency = report_data['historical_analysis']['efficiency_analysis']
        insights.append(f"Efficiency trend: {efficiency.get('efficiency_trend', 'stable')}")
    
    if 'trends' in report_data['historical_analysis']:
        trends = report_data['historical_analysis']['trends']
        insights.append(f"Usage trend: {trends.get('usage_trend', 'stable')}")
    
    insights_html = f"""
    <div class="section">
        <h2>🤖 AI Insights</h2>
        <div class="insights-list">
            <h3>Key Insights</h3>
            <ul>
                {''.join([f'<li>{insight}</li>' for insight in insights])}
            </ul>
        </div>
    </div>
    """
    
    return insights_html

def generate_recommendations_html(recommendations):
    """Generate HTML for recommendations"""
    html_parts = []
    
    # Immediate actions
    if 'immediate_actions' in recommendations and recommendations['immediate_actions']:
        for rec in recommendations['immediate_actions']:
            html_parts.append(f"""
            <div class="recommendation {rec.get('priority', 'medium')}">
                <strong>🚨 Immediate Action Required</strong><br>
                {rec.get('action', '')}<br>
                <em>Reason: {rec.get('reason', '')}</em>
            </div>
            """)
    
    # Optimization tips
    if 'optimization_tips' in recommendations and recommendations['optimization_tips']:
        for rec in recommendations['optimization_tips']:
            html_parts.append(f"""
            <div class="recommendation {rec.get('priority', 'medium')}">
                <strong>💡 Optimization Tip</strong><br>
                {rec.get('action', '')}<br>
                <em>Reason: {rec.get('reason', '')}</em>
            </div>
            """)
    
    # Efficiency improvements
    if 'efficiency_improvements' in recommendations and recommendations['efficiency_improvements']:
        for rec in recommendations['efficiency_improvements']:
            html_parts.append(f"""
            <div class="recommendation {rec.get('priority', 'medium')}">
                <strong>⚡ Efficiency Improvement</strong><br>
                {rec.get('action', '')}<br>
                <em>Reason: {rec.get('reason', '')}</em>
            </div>
            """)
    
    # If no recommendations, show a positive message
    if not html_parts:
        html_parts.append("""
        <div class="recommendation low">
            <strong>✅ All Good!</strong><br>
            Your system is operating optimally. No immediate recommendations needed.
        </div>
        """)
    
    return ''.join(html_parts)

# Error handlers
@app.errorhandler(404)
def not_found(error):
    return jsonify({'error': 'Endpoint not found'}), 404

@app.errorhandler(500)
def internal_error(error):
    return jsonify({'error': 'Internal server error'}), 500

if __name__ == '__main__':
    print("🚀 Starting EcoFlow Web Server...")
    print("📊 Dashboard available at: http://localhost:8080")
    print("🔧 API endpoints available at: http://localhost:8080/api/")
    print("🤖 AI Assistant integrated and ready!")
    print("=" * 50)
    
    # Start the Flask development server
    app.run(host='0.0.0.0', port=8080, debug=True) 