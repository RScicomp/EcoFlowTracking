#!/usr/bin/env python3
"""
EcoFlow AI Assistant
Provides intelligent analysis, predictions, and recommendations for EcoFlow data
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
import json
import logging
from ecoflow_monitor import EcoFlowMonitor

class EcoFlowAIAssistant:
    def __init__(self, monitor: EcoFlowMonitor):
        """
        Initialize AI Assistant with EcoFlow monitor
        
        Args:
            monitor: EcoFlowMonitor instance for data access
        """
        self.monitor = monitor
        self.logger = logging.getLogger(__name__)
        
        # Analysis thresholds and parameters
        self.thresholds = {
            'low_battery': 20,
            'high_temperature': 60,
            'high_power': 2000,
            'efficiency_warning': 85,
            'deep_discharge': 10
        }
        
        # Cost analysis parameters
        self.electricity_rate = 0.12  # $/kWh
        self.solar_savings_rate = 0.08  # $/kWh saved with solar
        
    def analyze_current_status(self) -> Dict:
        """Analyze current device status and provide insights"""
        try:
            # Get latest data
            latest_data = self.monitor.get_all_quotas()
            
            if latest_data.get('code') != '0':
                return {'error': 'Unable to fetch current data'}
            
            data = latest_data['data']
            
            # Extract key metrics
            soc = data.get('pd.soc', 0)
            watts_out = data.get('bms_bmsStatus.outputWatts', 0)
            watts_in = data.get('pd.wattsInSum', 0)
            temp = data.get('bms_bmsStatus.temp', 0)
            cycles = data.get('bms_bmsStatus.cycles', 0)
            remain_time = data.get('pd.remainTime', 0)
            
            # Generate insights
            insights = {
                'battery_status': self._analyze_battery_status(soc, remain_time),
                'power_usage': self._analyze_power_usage(watts_out, watts_in),
                'temperature': self._analyze_temperature(temp),
                'battery_health': self._analyze_battery_health(cycles, soc),
                'recommendations': self._generate_recommendations(soc, watts_out, temp, cycles)
            }
            
            return insights
            
        except Exception as e:
            self.logger.error(f"Error analyzing current status: {e}")
            return {'error': str(e)}
    
    def analyze_historical_patterns(self, days: int = 7) -> Dict:
        """Analyze historical usage patterns"""
        try:
            df = self.monitor.get_historical_data(days)
            
            if df.empty:
                return {'error': 'No historical data available'}
            
            analysis = {
                'usage_patterns': self._analyze_usage_patterns(df),
                'efficiency_analysis': self._analyze_efficiency(df),
                'cost_analysis': self._analyze_costs(df),
                'battery_patterns': self._analyze_battery_patterns(df),
                'anomalies': self._detect_anomalies(df),
                'trends': self._analyze_trends(df)
            }
            
            return analysis
            
        except Exception as e:
            self.logger.error(f"Error analyzing historical patterns: {e}")
            return {'error': str(e)}
    
    def predict_energy_needs(self, hours_ahead: int = 24) -> Dict:
        """Predict energy needs for the next period"""
        try:
            df = self.monitor.get_historical_data(7)  # Last 7 days
            
            if df.empty:
                return {'error': 'Insufficient data for prediction'}
            
            # Calculate average hourly usage
            df['hour'] = pd.to_datetime(df['timestamp']).dt.hour
            hourly_usage = df.groupby('hour')['watts_out'].mean()
            
            # Get current time and predict next hours
            now = datetime.now()
            predictions = []
            
            for i in range(hours_ahead):
                future_hour = (now + timedelta(hours=i)).hour
                predicted_usage = hourly_usage.get(future_hour, hourly_usage.mean())
                predictions.append({
                    'hour': future_hour,
                    'predicted_watts': predicted_usage,
                    'timestamp': (now + timedelta(hours=i)).isoformat()
                })
            
            total_predicted = sum(p['predicted_watts'] for p in predictions)
            
            return {
                'predictions': predictions,
                'total_predicted_kwh': total_predicted / 1000,
                'confidence_level': self._calculate_prediction_confidence(df),
                'factors': self._identify_prediction_factors(df)
            }
            
        except Exception as e:
            self.logger.error(f"Error predicting energy needs: {e}")
            return {'error': str(e)}
    
    def generate_smart_recommendations(self) -> Dict:
        """Generate personalized recommendations"""
        try:
            # Get current and historical data
            current = self.analyze_current_status()
            historical = self.analyze_historical_patterns(7)
            
            recommendations = {
                'immediate_actions': [],
                'optimization_tips': [],
                'maintenance_suggestions': [],
                'cost_savings': [],
                'efficiency_improvements': []
            }
            
            # Battery recommendations
            if 'battery_status' in current:
                soc = current['battery_status'].get('soc', 100)
                if soc < 30:
                    recommendations['immediate_actions'].append({
                        'priority': 'high',
                        'action': 'Charge battery to avoid deep discharge',
                        'reason': f'Battery at {soc}% - below recommended 30% threshold'
                    })
                elif soc > 90:
                    recommendations['optimization_tips'].append({
                        'priority': 'medium',
                        'action': 'Consider using stored energy to make room for solar charging',
                        'reason': 'Battery nearly full - solar charging may be wasted'
                    })
            
            # Efficiency recommendations
            if 'efficiency_analysis' in historical:
                avg_efficiency = historical['efficiency_analysis'].get('average_efficiency', 100)
                if avg_efficiency < 90:
                    recommendations['efficiency_improvements'].append({
                        'priority': 'medium',
                        'action': 'Check for high-power devices during peak solar hours',
                        'reason': f'Average efficiency is {avg_efficiency:.1f}% - below optimal'
                    })
            
            # Cost savings recommendations
            if 'cost_analysis' in historical:
                daily_cost = historical['cost_analysis'].get('average_daily_cost', 0)
                if daily_cost > 2.0:  # More than $2/day
                    recommendations['cost_savings'].append({
                        'priority': 'medium',
                        'action': 'Shift high-power usage to off-peak hours',
                        'reason': f'Daily energy cost is ${daily_cost:.2f} - above average'
                    })
            
            return recommendations
            
        except Exception as e:
            self.logger.error(f"Error generating recommendations: {e}")
            return {'error': str(e)}
    
    def answer_natural_language_query(self, query: str) -> Dict:
        """Answer natural language queries about EcoFlow data"""
        query_lower = query.lower()
        
        try:
            if 'consumption' in query_lower or 'usage' in query_lower:
                return self._answer_consumption_query(query)
            elif 'battery' in query_lower or 'soc' in query_lower:
                return self._answer_battery_query(query)
            elif 'efficiency' in query_lower or 'efficient' in query_lower:
                return self._answer_efficiency_query(query)
            elif 'cost' in query_lower or 'money' in query_lower or 'savings' in query_lower:
                return self._answer_cost_query(query)
            elif 'predict' in query_lower or 'forecast' in query_lower:
                return self._answer_prediction_query(query)
            elif 'compare' in query_lower:
                return self._answer_comparison_query(query)
            elif 'recommend' in query_lower or 'suggest' in query_lower:
                return self._answer_recommendation_query(query)
            else:
                return {
                    'answer': "I can help you with questions about power consumption, battery status, efficiency, costs, predictions, comparisons, and recommendations. Please try rephrasing your question.",
                    'suggestions': [
                        "What's my average daily power consumption?",
                        "How efficient is my solar charging?",
                        "What's my battery health status?",
                        "How much money am I saving with solar?",
                        "Predict my energy needs for tomorrow"
                    ]
                }
                
        except Exception as e:
            self.logger.error(f"Error answering query: {e}")
            return {'error': str(e)}
    
    def _analyze_battery_status(self, soc: int, remain_time: int) -> Dict:
        """Analyze battery status"""
        status = 'normal'
        if soc <= self.thresholds['low_battery']:
            status = 'critical'
        elif soc <= 30:
            status = 'low'
        
        return {
            'soc': soc,
            'status': status,
            'remaining_time_hours': abs(remain_time) / 3600 if remain_time != 0 else None,
            'health_indicator': 'good' if soc > 80 else 'fair' if soc > 50 else 'poor'
        }
    
    def _analyze_power_usage(self, watts_out: int, watts_in: int) -> Dict:
        """Analyze power usage patterns"""
        return {
            'current_output': watts_out,
            'current_input': watts_in,
            'net_power': watts_out - watts_in,
            'status': 'discharging' if watts_out > watts_in else 'charging' if watts_in > watts_out else 'idle'
        }
    
    def _analyze_temperature(self, temp: int) -> Dict:
        """Analyze temperature status"""
        status = 'normal'
        if temp >= self.thresholds['high_temperature']:
            status = 'critical'
        elif temp >= 50:
            status = 'elevated'
        
        return {
            'temperature': temp,
            'status': status,
            'recommendation': 'Monitor closely' if status != 'normal' else 'Normal operating range'
        }
    
    def _analyze_battery_health(self, cycles: int, soc: int) -> Dict:
        """Analyze battery health"""
        health_score = max(0, 100 - (cycles * 0.5))  # Rough estimate
        
        return {
            'cycles': cycles,
            'health_score': health_score,
            'estimated_life_remaining': f"{max(0, 1000 - cycles)} cycles",
            'recommendation': 'Consider replacement' if cycles > 800 else 'Good condition'
        }
    
    def _analyze_usage_patterns(self, df: pd.DataFrame) -> Dict:
        """Analyze usage patterns from historical data"""
        df['hour'] = pd.to_datetime(df['timestamp']).dt.hour
        df['day'] = pd.to_datetime(df['timestamp']).dt.day_name()
        
        hourly_usage = df.groupby('hour')['watts_out'].mean()
        daily_usage = df.groupby('day')['watts_out'].mean()
        
        peak_hour = hourly_usage.idxmax()
        peak_day = daily_usage.idxmax()
        
        return {
            'peak_usage_hour': int(peak_hour),
            'peak_usage_day': peak_day,
            'average_daily_usage_kwh': df['watts_out'].sum() / 1000 / len(df['day'].unique()),
            'usage_variability': hourly_usage.std() / hourly_usage.mean() if hourly_usage.mean() > 0 else 0
        }
    
    def _analyze_efficiency(self, df: pd.DataFrame) -> Dict:
        """Analyze energy efficiency"""
        df['efficiency'] = (df['watts_out'] / df['watts_in'].replace(0, 1)) * 100
        df['efficiency'] = df['efficiency'].clip(0, 100)
        
        return {
            'average_efficiency': df['efficiency'].mean(),
            'efficiency_trend': 'improving' if df['efficiency'].iloc[-10:].mean() > df['efficiency'].iloc[:10].mean() else 'declining',
            'efficiency_issues': len(df[df['efficiency'] < self.thresholds['efficiency_warning']])
        }
    
    def _analyze_costs(self, df: pd.DataFrame) -> Dict:
        """Analyze energy costs"""
        total_energy_kwh = df['watts_out'].sum() / 1000
        total_cost = total_energy_kwh * self.electricity_rate
        
        return {
            'total_energy_kwh': total_energy_kwh,
            'total_cost': total_cost,
            'average_daily_cost': total_cost / len(df['timestamp'].dt.date.unique()),
            'cost_per_kwh': self.electricity_rate
        }
    
    def _analyze_battery_patterns(self, df: pd.DataFrame) -> Dict:
        """Analyze battery usage patterns"""
        df['soc_change'] = df['soc'].diff()
        
        deep_discharges = len(df[df['soc'] < self.thresholds['deep_discharge']])
        charge_cycles = len(df[df['soc_change'] > 10])
        discharge_cycles = len(df[df['soc_change'] < -10])
        
        return {
            'deep_discharges': deep_discharges,
            'charge_cycles': charge_cycles,
            'discharge_cycles': discharge_cycles,
            'average_soc': df['soc'].mean(),
            'soc_variability': df['soc'].std()
        }
    
    def _detect_anomalies(self, df: pd.DataFrame) -> List[Dict]:
        """Detect anomalies in the data"""
        anomalies = []
        
        # High power usage anomalies
        power_threshold = df['watts_out'].mean() + 2 * df['watts_out'].std()
        high_power_events = df[df['watts_out'] > power_threshold]
        
        for _, row in high_power_events.iterrows():
            anomalies.append({
                'type': 'high_power_usage',
                'timestamp': row['timestamp'],
                'value': row['watts_out'],
                'severity': 'high' if row['watts_out'] > self.thresholds['high_power'] else 'medium',
                'description': f'Unusually high power usage: {row["watts_out"]}W'
            })
        
        # Temperature anomalies
        temp_threshold = df['typec1_temp'].mean() + 2 * df['typec1_temp'].std()
        high_temp_events = df[df['typec1_temp'] > temp_threshold]
        
        for _, row in high_temp_events.iterrows():
            anomalies.append({
                'type': 'high_temperature',
                'timestamp': row['timestamp'],
                'value': row['typec1_temp'],
                'severity': 'high' if row['typec1_temp'] > self.thresholds['high_temperature'] else 'medium',
                'description': f'Unusually high temperature: {row["typec1_temp"]}°C'
            })
        
        return anomalies
    
    def _analyze_trends(self, df: pd.DataFrame) -> Dict:
        """Analyze trends in the data"""
        # Calculate moving averages
        df['watts_out_ma'] = df['watts_out'].rolling(window=24).mean()
        df['soc_ma'] = df['soc'].rolling(window=24).mean()
        
        # Determine trends
        recent_usage = df['watts_out'].iloc[-24:].mean()
        earlier_usage = df['watts_out'].iloc[:24].mean()
        
        usage_trend = 'increasing' if recent_usage > earlier_usage * 1.1 else 'decreasing' if recent_usage < earlier_usage * 0.9 else 'stable'
        
        return {
            'usage_trend': usage_trend,
            'trend_strength': abs(recent_usage - earlier_usage) / earlier_usage if earlier_usage > 0 else 0,
            'seasonal_patterns': self._detect_seasonal_patterns(df)
        }
    
    def _detect_seasonal_patterns(self, df: pd.DataFrame) -> Dict:
        """Detect seasonal or cyclical patterns"""
        df['hour'] = pd.to_datetime(df['timestamp']).dt.hour
        
        # Daily pattern
        hourly_usage = df.groupby('hour')['watts_out'].mean()
        peak_hours = hourly_usage.nlargest(3).index.tolist()
        
        return {
            'peak_hours': peak_hours,
            'daily_pattern': 'consistent' if hourly_usage.std() / hourly_usage.mean() < 0.5 else 'variable'
        }
    
    def _calculate_prediction_confidence(self, df: pd.DataFrame) -> str:
        """Calculate confidence level for predictions"""
        if len(df) < 24:  # Less than 1 day of data
            return 'low'
        elif len(df) < 168:  # Less than 1 week of data
            return 'medium'
        else:
            return 'high'
    
    def _identify_prediction_factors(self, df: pd.DataFrame) -> List[str]:
        """Identify factors affecting predictions"""
        factors = []
        
        if df['watts_out'].std() / df['watts_out'].mean() > 0.5:
            factors.append('High usage variability')
        
        if len(df[df['soc'] < 20]) > 0:
            factors.append('Low battery events')
        
        if len(df[df['typec1_temp'] > 50]) > 0:
            factors.append('Temperature fluctuations')
        
        return factors
    
    def _generate_recommendations(self, soc: int, watts_out: int, temp: int, cycles: int) -> List[Dict]:
        """Generate immediate recommendations"""
        recommendations = []
        
        if soc < 30:
            recommendations.append({
                'priority': 'high',
                'category': 'battery',
                'action': 'Charge battery immediately',
                'reason': f'Battery level critical at {soc}%'
            })
        
        if temp > 50:
            recommendations.append({
                'priority': 'medium',
                'category': 'temperature',
                'action': 'Check device ventilation',
                'reason': f'Temperature elevated at {temp}°C'
            })
        
        if cycles > 500:
            recommendations.append({
                'priority': 'low',
                'category': 'maintenance',
                'action': 'Consider battery health check',
                'reason': f'High cycle count: {cycles}'
            })
        
        return recommendations
    
    def _answer_consumption_query(self, query: str) -> Dict:
        """Answer consumption-related queries"""
        df = self.monitor.get_historical_data(7)
        
        if df.empty:
            return {'answer': 'No consumption data available yet.'}
        
        avg_daily = float(df['watts_out'].sum() / 1000 / len(df['timestamp'].dt.date.unique()))
        peak_usage = int(df['watts_out'].max())
        
        return {
            'answer': f"Your average daily power consumption is {avg_daily:.2f} kWh. Peak usage was {peak_usage}W.",
            'data': {
                'average_daily_kwh': avg_daily,
                'peak_watts': peak_usage,
                'total_energy_kwh': float(df['watts_out'].sum() / 1000)
            }
        }
    
    def _answer_battery_query(self, query: str) -> Dict:
        """Answer battery-related queries"""
        current = self.analyze_current_status()
        
        if 'error' in current:
            return {'answer': 'Unable to fetch battery data.'}
        
        battery = current['battery_status']
        health = current['battery_health']
        
        return {
            'answer': f"Battery is at {int(battery['soc'])}% with {int(health['cycles'])} charge cycles. Health score: {float(health['health_score']):.1f}%.",
            'data': battery
        }
    
    def _answer_efficiency_query(self, query: str) -> Dict:
        """Answer efficiency-related queries"""
        historical = self.analyze_historical_patterns(7)
        
        if 'error' in historical:
            return {'answer': 'Unable to analyze efficiency data.'}
        
        efficiency = historical['efficiency_analysis']
        
        return {
            'answer': f"Your average efficiency is {float(efficiency['average_efficiency']):.1f}% with a {efficiency['efficiency_trend']} trend.",
            'data': efficiency
        }
    
    def _answer_cost_query(self, query: str) -> Dict:
        """Answer cost-related queries"""
        historical = self.analyze_historical_patterns(7)
        
        if 'error' in historical:
            return {'answer': 'Unable to analyze cost data.'}
        
        costs = historical['cost_analysis']
        
        return {
            'answer': f"Your average daily energy cost is ${float(costs['average_daily_cost']):.2f}. Total cost for the period: ${float(costs['total_cost']):.2f}.",
            'data': costs
        }
    
    def _answer_prediction_query(self, query: str) -> Dict:
        """Answer prediction-related queries"""
        prediction = self.predict_energy_needs(24)
        
        if 'error' in prediction:
            return {'answer': 'Unable to generate prediction.'}
        
        return {
            'answer': f"Predicted energy needs for tomorrow: {float(prediction['total_predicted_kwh']):.2f} kWh with {prediction['confidence_level']} confidence.",
            'data': prediction
        }
    
    def _answer_comparison_query(self, query: str) -> Dict:
        """Answer comparison-related queries"""
        # This would need more sophisticated logic for different time periods
        return {
            'answer': "I can compare different time periods. Please specify what you'd like to compare (e.g., 'this week vs last week').",
            'suggestions': [
                "Compare this week vs last week",
                "Compare today vs yesterday",
                "Compare this month vs last month"
            ]
        }
    
    def _answer_recommendation_query(self, query: str) -> Dict:
        """Answer recommendation-related queries"""
        recommendations = self.generate_smart_recommendations()
        
        if 'error' in recommendations:
            return {'answer': 'Unable to generate recommendations.'}
        
        immediate_actions = recommendations.get('immediate_actions', [])
        optimization_tips = recommendations.get('optimization_tips', [])
        
        if immediate_actions:
            action = immediate_actions[0]
            return {
                'answer': f"Priority recommendation: {action['action']}. Reason: {action['reason']}",
                'data': recommendations
            }
        elif optimization_tips:
            tip = optimization_tips[0]
            return {
                'answer': f"Optimization tip: {tip['action']}. Reason: {tip['reason']}",
                'data': recommendations
            }
        else:
            return {
                'answer': "Your system is operating optimally. No immediate recommendations needed.",
                'data': recommendations
            }

# Example usage and testing
if __name__ == "__main__":
    # Initialize monitor and AI assistant
    monitor = EcoFlowMonitor()
    ai = EcoFlowAIAssistant(monitor)
    
    # Test AI assistant
    print("🤖 EcoFlow AI Assistant Test")
    print("=" * 50)
    
    # Test current status analysis
    print("\n📊 Current Status Analysis:")
    status = ai.analyze_current_status()
    print(json.dumps(status, indent=2))
    
    # Test natural language query
    print("\n💬 Natural Language Query Test:")
    query = "What's my average daily power consumption?"
    answer = ai.answer_natural_language_query(query)
    print(f"Q: {query}")
    print(f"A: {answer['answer']}")
    
    # Test recommendations
    print("\n🎯 Smart Recommendations:")
    recommendations = ai.generate_smart_recommendations()
    print(json.dumps(recommendations, indent=2)) 