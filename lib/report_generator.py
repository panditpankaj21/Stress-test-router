"""
Generate visual reports from test data
"""
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from datetime import datetime
from typing import List, Dict, Any
import os
import statistics



class ReportGenerator:
    def __init__(self, output_dir: str = "test_reports"):
        """Initialize report generator"""
        self.output_dir = output_dir
        os.makedirs(output_dir, exist_ok=True)
        
        # Set style for better-looking plots
        plt.style.use('seaborn-darkgrid')
    
    def generate_router_cpu_plot(self, test_data: List[Dict], current_test: Dict) -> str:
        """
        Generate router CPU utilization over time plot
        Returns: path to saved image
        """
        if not test_data:
            return None
        
        fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(12, 8))
        
        # Sort by test time
        sorted_data = sorted(test_data, key=lambda x: x['test_time'])
        
        # Create readable test labels
        test_labels = [f"Test #{idx}" for idx in range(1, len(sorted_data) + 1)]
        x_positions = range(1, len(test_labels) + 1)
        
        cpu_creation = [d.get('router_avg_cpu_creation', 0) for d in sorted_data]
        cpu_test = [d.get('router_avg_cpu_test', 0) for d in sorted_data]
        
        # Plot 1: Router CPU during creation
        ax1.plot(x_positions, cpu_creation, marker='o', linewidth=2, markersize=6, 
                label='CPE During Creation', color='#2E86AB')
        avg_creation = statistics.mean(cpu_creation) if cpu_creation else 0
        ax1.axhline(y=avg_creation, 
                color='r', linestyle='--', label=f'Average: {avg_creation:.2f}%', alpha=0.7)
        ax1.set_xlabel('Test Number', fontsize=11)
        ax1.set_ylabel('CPE Utilization (%)', fontsize=11)
        ax1.set_title(f'Feature: {current_test.get("feature_name", "Unknown")} with '
                    f'{current_test.get("number_of_clients", 0)} Client\n\n'
                    'CPE Utilization During Client Creation\n', 
                    fontsize=13, fontweight='bold')
        ax1.legend(loc='upper right')
        ax1.grid(True, alpha=0.3, axis='y')
        ax1.set_xticks(x_positions)
        ax1.set_xticklabels(test_labels, rotation=45, ha='right')
        
        # Add some padding to y-axis
        if cpu_creation:
            y_max = max(cpu_creation) * 2
            y_min = min(cpu_creation)
            y_range = y_max - y_min if y_max != y_min else y_max
            ax1.set_ylim(max(0, y_min - y_range * 0.1), y_max + y_range * 0.1)
        
        # Plot 2: Router CPU during test
        ax2.plot(x_positions, cpu_test, marker='s', linewidth=2, markersize=6, 
                label='CPE During Test', color='#A23B72')
        avg_test = statistics.mean(cpu_test) if cpu_test else 0
        ax2.axhline(y=avg_test, 
                color='r', linestyle='--', label=f'Average: {avg_test:.2f}%', alpha=0.7)
        ax2.set_xlabel('Test Number', fontsize=11)
        ax2.set_ylabel('CPE Utilization (%)', fontsize=11)
        ax2.set_title('CPE Utilization During Test Execution', fontsize=13, fontweight='bold')
        ax2.legend(loc='upper right')
        ax2.grid(True, alpha=0.3, axis='y')
        ax2.set_xticks(x_positions)
        ax2.set_xticklabels(test_labels, rotation=45, ha='right')
        
        # Add some padding to y-axis
        if cpu_test:
            y_max = max(cpu_test) * 2
            y_min = min(cpu_test)
            y_range = y_max - y_min if y_max != y_min else y_max
            ax2.set_ylim(max(0, y_min - y_range * 0.1), y_max + y_range * 0.1)
        
        plt.tight_layout()
        
        filename = f"{current_test.get('router_model')}_{current_test.get('router_name')}_cpu_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
        filepath = os.path.join(self.output_dir, filename)
        plt.savefig(filepath, dpi=300, bbox_inches='tight')
        plt.close()
        
        return filepath
    
    def generate_linux_cpu_plot(self, test_data: List[Dict], current_test: Dict) -> str:
        """
        Generate Linux CPU utilization over time plot
        Returns: path to saved image
        """
        if not test_data:
            return None
        
        fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(12, 8))
        
        sorted_data = sorted(test_data, key=lambda x: x['test_time'])
        
        test_times = [d['test_time'] for d in sorted_data]
        cpu_creation = [d.get('linux_avg_cpu_creation', 0) for d in sorted_data]
        cpu_test = [d.get('linux_avg_cpu_test', 0) for d in sorted_data]
        
        # Plot 1: Linux CPU during creation
        ax1.plot(test_times, cpu_creation, marker='o', linewidth=2, markersize=6, 
                label='CPU During Creation', color='#F18F01')
        ax1.axhline(y=statistics.mean(cpu_creation) if cpu_creation else 0, 
                   color='r', linestyle='--', label='Average', alpha=0.7)
        ax1.set_xlabel('Test Time', fontsize=11)
        ax1.set_ylabel('CPU Utilization (%)', fontsize=11)
        ax1.set_title(f'Linux CPU During Client Creation\nFeature: {current_test.get("feature_name", "Unknown")} -'
                     f'{current_test.get("number_of_clients", 0)} Client', fontsize=13, fontweight='bold')
        ax1.legend()
        ax1.grid(True, alpha=0.3)
        ax1.xaxis.set_major_formatter(mdates.DateFormatter('%m/%d %H:%M'))
        plt.setp(ax1.xaxis.get_majorticklabels(), rotation=45, ha='right')
        
        # Plot 2: Linux CPU during test
        ax2.plot(test_times, cpu_test, marker='s', linewidth=2, markersize=6, 
                label='CPU During Test', color='#C73E1D')
        ax2.axhline(y=statistics.mean(cpu_test) if cpu_test else 0, 
                   color='r', linestyle='--', label='Average', alpha=0.7)
        ax2.set_xlabel('Test Time', fontsize=11)
        ax2.set_ylabel('CPU Utilization (%)', fontsize=11)
        ax2.set_title('Linux CPU During Test Execution', fontsize=13, fontweight='bold')
        ax2.legend()
        ax2.grid(True, alpha=0.3)
        ax2.xaxis.set_major_formatter(mdates.DateFormatter('%m/%d %H:%M'))
        plt.setp(ax2.xaxis.get_majorticklabels(), rotation=45, ha='right')
        
        plt.tight_layout()
        
        filename = f"machine_cpu_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
        filepath = os.path.join(self.output_dir, filename)
        plt.savefig(filepath, dpi=300, bbox_inches='tight')
        plt.close()
        
        return filepath
    
    def generate_time_taken_plot(self, test_data: List[Dict], current_test: Dict) -> str:
        """
        Generate time taken to create clients plot
        Returns: path to saved image
        """
        if not test_data:
            return None
        
        fig, ax = plt.subplots(figsize=(12, 6))
        
        sorted_data = sorted(test_data, key=lambda x: x['test_time'])
        
        # Create readable test labels instead of raw dates
        test_labels = []
        time_taken_seconds = []
        
        for idx, d in enumerate(sorted_data, 1):
            # Create label like "Test #1", "Test #2", etc.
            test_labels.append(f"Test #{idx}")
            # Convert time to seconds if it's in minutes
            time_val = d.get('time_taken', 0)
            time_taken_seconds.append(time_val)
        
        # Create x-axis positions
        x_positions = range(1, len(test_labels) + 1)
        
        ax.plot(x_positions, time_taken_seconds, marker='D', linewidth=2, markersize=7, 
            label='Time Taken', color='#06A77D')
        ax.axhline(y=statistics.mean(time_taken_seconds) if time_taken_seconds else 0, 
                color='r', linestyle='--', label=f'Average: {statistics.mean(time_taken_seconds):.2f}s', alpha=0.7)
        
        ax.set_xlabel('Test Number', fontsize=11)
        ax.set_ylabel('Time (seconds)', fontsize=11)
        ax.set_title(f'Feature: {current_test.get("feature_name", "Unknown")} with '
                    f'{current_test.get("number_of_clients", 0)} Client\n\n'
                    f'Time Required to Create Clients\n', 
                    fontsize=13, fontweight='bold')
        ax.legend(loc='upper right')
        ax.grid(True, alpha=0.3, axis='y')
        
        # Set x-axis to show test numbers
        ax.set_xticks(x_positions)
        ax.set_xticklabels(test_labels, rotation=45, ha='right')
        
        # Add some padding to y-axis
        if time_taken_seconds:
            y_max = max(time_taken_seconds) * 2
            y_min = min(time_taken_seconds)
            y_range = y_max - y_min
            ax.set_ylim(max(0, y_min - y_range * 0.1), y_max + y_range * 0.1)
        
        plt.tight_layout()
        
        filename = f"time_taken_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
        filepath = os.path.join(self.output_dir, filename)
        plt.savefig(filepath, dpi=300, bbox_inches='tight')
        plt.close()
        
        return filepath
    
    def calculate_metrics_average(self, test_data: List[Dict]) -> Dict[str, float]:
        """Calculate average of metrics across all tests"""

        all_metrics = {}
        
        for test in test_data:
            metrics = test.get('metrics', {})
            if metrics:
                for key, value in metrics.items():
                    if isinstance(value, (int, float)):
                        if key not in all_metrics:
                            all_metrics[key] = []
                        all_metrics[key].append(value)
        
        # Calculate averages
        averaged_metrics = {}
        for key, values in all_metrics.items():
            if values:
                averaged_metrics[key] = {
                    'average': statistics.mean(values),
                    'min': min(values),
                    'max': max(values),
                    'count': len(values)
                }
        
        return averaged_metrics 
    
    def generate_html_report(
        self, 
        current_test: Dict, 
        historical_data: List[Dict],
        router_cpu_img: str,
        linux_cpu_img: str,
        time_taken_img: str,
        metrics_data: Dict
    ) -> str:
        """Generate comprehensive HTML report"""
        
        # Convert image paths to relative paths
        def get_img_tag(img_path):
            if img_path:
                filename = os.path.basename(img_path)
                return f'<img src="{filename}" alt="Chart" style="max-width: 100%; height: auto; margin: 20px 0;">'
            return '<p style="color: #666;">No data available</p>'
        
        # Build metrics table
        metrics_html = ""
        if metrics_data:
            metrics_html = """
            <div class="section">
                <h2>📊 Metrics Analysis</h2>
                <table>
                    <thead>
                        <tr>
                            <th>Metric</th>
                            <th>Average</th>
                            <th>Min</th>
                            <th>Max</th>
                            <th>Count</th>
                        </tr>
                    </thead>
                    <tbody>
            """
            for metric_name, stats in metrics_data.items():
                metrics_html += f"""
                        <tr>
                            <td>{metric_name}</td>
                            <td>{stats['average']:.2f}</td>
                            <td>{stats['min']:.2f}</td>
                            <td>{stats['max']:.2f}</td>
                            <td>{stats['count']}</td>
                        </tr>
                """
            metrics_html += """
                    </tbody>
                </table>
            </div>
            """
        else:
            metrics_html = """
            <div class="section">
                <h2>📊 Metrics Analysis</h2>
                <p style="color: #666; font-style: italic;">No metrics data available for this test.</p>
            </div>
            """
        
        html_content = f"""
        <!DOCTYPE html>
        <html lang="en">
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>Test Report - {current_test.get('router_name', 'Unknown')}</title>
            <style>
                * {{
                    margin: 0;
                    padding: 0;
                    box-sizing: border-box;
                }}
                
                body {{
                    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantarell, sans-serif;
                    color: #333;
                }}
                
                .container {{
                    margin: 0 auto;
                    background: white;
                    box-shadow: 0 20px 60px rgba(0,0,0,0.3);
                    overflow: hidden;
                }}
                
                .header {{
                    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                    color: white;
                    padding: 40px;
                    text-align: center;
                }}
                
                .header h1 {{
                    font-size: 2.5em;
                    margin-bottom: 10px;
                    text-shadow: 2px 2px 4px rgba(0,0,0,0.2);
                }}
                
                .header .subtitle {{
                    font-size: 1.1em;
                    opacity: 0.9;
                }}
                
                .test-info {{
                    display: grid;
                    grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
                    gap: 20px;
                    padding: 30px;
                    background: #f8f9fa;
                    border-bottom: 1px solid #e0e0e0;
                }}
                
                .info-card {{
                    background: white;
                    padding: 20px;
                    border-radius: 8px;
                    box-shadow: 0 2px 8px rgba(0,0,0,0.1);
                    border-left: 4px solid #667eea;
                }}
                
                .info-card .label {{
                    font-size: 0.85em;
                    color: #666;
                    text-transform: uppercase;
                    letter-spacing: 0.5px;
                    margin-bottom: 8px;
                }}
                
                .info-card .value {{
                    font-size: 1.3em;
                    font-weight: 600;
                    color: #333;
                }}
                
                .status-pass {{
                    color: #28a745;
                }}
                
                .status-fail {{
                    color: #dc3545;
                }}
                
                .content {{
                    padding: 40px;
                }}
                
                .section {{
                    margin-bottom: 50px;
                }}
                
                .section h2 {{
                    font-size: 1.8em;
                    margin-bottom: 20px;
                    color: #333;
                    border-bottom: 3px solid #667eea;
                    padding-bottom: 10px;
                }}
                
                table {{
                    width: 100%;
                    border-collapse: collapse;
                    margin-top: 20px;
                    background: white;
                    box-shadow: 0 2px 8px rgba(0,0,0,0.1);
                    border-radius: 8px;
                    overflow: hidden;
                }}
                
                thead {{
                    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                    color: white;
                }}
                
                th, td {{
                    padding: 15px;
                    text-align: left;
                }}
                
                th {{
                    font-weight: 600;
                    text-transform: uppercase;
                    font-size: 0.9em;
                    letter-spacing: 0.5px;
                }}
                
                tbody tr {{
                    border-bottom: 1px solid #e0e0e0;
                    transition: background 0.2s;
                }}
                
                tbody tr:hover {{
                    background: #f8f9fa;
                }}
                
                tbody tr:last-child {{
                    border-bottom: none;
                }}
                
                .chart-container {{
                    margin: 20px 0;
                    text-align: center;
                    background: #f8f9fa;
                    padding: 50px;
                    border-radius: 8px;
                }}
                
                .footer {{
                    text-align: center;
                    padding: 20px;
                    background: #f8f9fa;
                    color: #666;
                    font-size: 0.9em;
                    border-top: 1px solid #e0e0e0;
                }}
                
                .summary-stats {{
                    display: grid;
                    grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
                    gap: 20px;
                    margin-top: 20px;
                }}
                
                .stat-box {{
                    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                    color: white;
                    padding: 25px;
                    border-radius: 8px;
                    text-align: center;
                    box-shadow: 0 4px 12px rgba(0,0,0,0.15);
                }}
                
                .stat-box .stat-value {{
                    font-size: 2.5em;
                    margin-bottom: 5px;
                }}
                
                .stat-box .stat-label {{
                    font-size: 0.9em;
                    opacity: 0.9;
                }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>Test Execution Report</h1>
                    <div class="subtitle">Automated Performance Analysis</div>
                </div>
                
                <div class="test-info">
                    <div class="info-card">
                        <div class="label">Router Name</div>
                        <div class="value">{current_test.get('router_name', 'N/A')}</div>
                    </div>
                    <div class="info-card">
                        <div class="label">Router Model</div>
                        <div class="value">{current_test.get('router_model', 'N/A')}</div>
                    </div>
                    <div class="info-card">
                        <div class="label">MAC Address</div>
                        <div class="value" style="font-family: monospace;">{current_test.get('router_mac', 'N/A')}</div>
                    </div>
                    <div class="info-card">
                        <div class="label">Firmware</div>
                        <div class="value">{current_test.get('router_firmware', 'N/A')}</div>
                    </div>
                    <div class="info-card">
                        <div class="label">Feature</div>
                        <div class="value">{current_test.get('feature_name', 'N/A')}</div>
                    </div>
                    <div class="info-card">
                        <div class="label">Scenario</div>
                        <div class="value">{current_test.get('scenario_name', 'N/A')}</div>
                    </div>
                    <div class="info-card">
                        <div class="label">Number of Clients</div>
                        <div class="value">{current_test.get('number_of_clients', 'N/A')}</div>
                    </div>
                    <div class="info-card">
                        <div class="label">Status</div>
                        <div class="value status-{current_test.get('status', '').lower()}">{current_test.get('status', 'N/A').upper()}</div>
                    </div>
                </div>
                
                <div class="content">
                    <div class="section">
                        <h2>📈 Summary Statistics</h2>
                        <div class="summary-stats">
                            <div class="stat-box">
                                <div class="stat-value">{len(historical_data)}</div>
                                <div class="stat-label">Total Tests Analyzed</div>
                            </div>
                            <div class="stat-box">
                                <div class="stat-value">{current_test.get('time_taken', 0):.1f}s</div>
                                <div class="stat-label">Current Test Duration</div>
                            </div>
                            <div class="stat-box">
                                <div class="stat-value">{current_test.get('router_avg_cpu_test', 0):.1f}%</div>
                                <div class="stat-label">Router CPU (Test)</div>
                            </div>
                            <div class="stat-box">
                                <div class="stat-value">{current_test.get('linux_avg_cpu_test', 0):.1f}%</div>
                                <div class="stat-label">Linux CPU (Test)</div>
                            </div>
                        </div>
                    </div>
                    
                    <div class="section">
                        <h2>🖥️ Router CPU Utilization Over Time</h2>
                        <div class="chart-container">
                            {get_img_tag(router_cpu_img)}
                        </div>
                    </div>
                    
                    <div class="section">
                        <h2>💻 Linux CPU Utilization Over Time</h2>
                        <div class="chart-container">
                            {get_img_tag(linux_cpu_img)}
                        </div>
                    </div>
                    
                    <div class="section">
                        <h2>⏱️ Time Taken to Create Clients</h2>
                        <div class="chart-container">
                            {get_img_tag(time_taken_img)}
                        </div>
                    </div>
                    
                    {metrics_html}
                </div>
                
                <div class="footer">
                    Generated on {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} | 
                    Test executed at {current_test.get('test_time', datetime.now())}
                </div>
            </div>
        </body>
        </html>
        """
        
        filename = f"test_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.html"
        filepath = os.path.join(self.output_dir, filename)
        
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(html_content)
        
        return filepath