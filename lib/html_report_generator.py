"""
Professional HTML Report Generator for Test Results
Creates clean, multi-page HTML reports with minimal styling
"""
from datetime import datetime
from typing import List, Dict, Any
import os
import shutil
from collections import defaultdict


class HTMLReportGenerator:
    def __init__(self, output_dir: str = "test_reports"):
        """Initialize HTML report generator"""
        self.output_dir = output_dir
        os.makedirs("test_reports", exist_ok=True)
        self.report_dir = None
    
    def _aggregate_router_data(self, all_tests: List[Dict]) -> Dict:
        """Aggregate test data by router"""
        aggregated = defaultdict(lambda: {
            'router_name': None,
            'router_model': None,
            'router_firmware': None,
            'router_mac': None,
            'total_tests': 0,
            'passed_tests': 0,
            'failed_tests': 0,
            'total_duration': 0,
            'features': defaultdict(list),
            'failed_tests_details': []
        })
        
        for test in all_tests:
            router_mac = test.get('router_mac')
            if not router_mac:
                continue
            
            router_data = aggregated[router_mac]
            
            if not router_data['router_name']:
                router_data['router_name'] = test.get('router_name', 'Unknown')
                router_data['router_model'] = test.get('router_model', 'Unknown')
                router_data['router_firmware'] = test.get('router_firmware', 'Unknown')
                router_data['router_mac'] = router_mac
            
            router_data['total_tests'] += 1
            status = test.get('status', '').lower()
            if status == 'passed':
                router_data['passed_tests'] += 1
            else:
                router_data['failed_tests'] += 1
                router_data['failed_tests_details'].append(test)
            
            # Calculate test duration
            start_time = test.get('start_time')
            end_time = test.get('end_time')
            if start_time and end_time:
                try:
                    if isinstance(start_time, str):
                        start_time = datetime.fromisoformat(start_time.replace('Z', '+00:00'))
                    if isinstance(end_time, str):
                        end_time = datetime.fromisoformat(end_time.replace('Z', '+00:00'))
                    
                    duration = (end_time - start_time).total_seconds()
                    router_data['total_duration'] += duration
                except:
                    pass
            
            feature_name = test.get('feature_name', 'Unknown Feature')
            router_data['features'][feature_name].append(test)
        
        return dict(aggregated)
    
    def _format_duration(self, total_seconds: float) -> str:
        """Format total seconds as HH:MM:SS"""
        total_seconds = int(total_seconds)
        hours = total_seconds // 3600
        minutes = (total_seconds % 3600) // 60
        seconds = total_seconds % 60
        return f"{hours:02d}:{minutes:02d}:{seconds:02d}"
    
    def _format_date(self, date_str) -> str:
        """Format date to US format"""
        if not date_str:
            return 'N/A'
        
        try:
            if isinstance(date_str, str):
                dt = datetime.fromisoformat(date_str.replace('Z', '+00:00'))
            else:
                dt = date_str
            return dt.strftime('%m/%d/%Y %H:%M:%S')
        except:
            return str(date_str)
    
    def _get_header_html(self) -> str:
        """Generate consistent header with logos for all pages"""
        return """
        <div class="header">
            <div class="inside-header">
                <h1>Test Execution Report</h1>
                <div class="subtitle">Router Performance Analysis</div>
            </div>
            <div>
                <img src="../../logo/cognizant_logo.png" alt="Cognizant Logo" style="height:25px; margin-right:20px;">
                <img src="../../logo/charter_logo.png" alt="Charter Logo" style="height:25px;">
            </div>
        </div>
        """
    
    def _get_footer_html(self) -> str:
        """Generate consistent footer for all pages"""
        return """
        <div class="footer">
            <p>All rights reserved © Cognizant Technology Solutions</p>
        </div>
        """
    
    def _get_css(self) -> str:
        """Get minimal professional CSS styling"""
        return """
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }
        
        body {
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            line-height: 1.6;
            color: #333;
            background: #f8f9fa;
            padding: 20px;
        }
        
        .container {
            max-width: 1200px;
            margin: 0 auto;
            background: #fff;
            box-shadow: 0 2px 8px rgba(0,0,0,0.1);
            min-height: calc(100vh - 40px);
            display: flex;
            flex-direction: column;
        }
        
        .content-wrapper {
            flex: 1;
            padding: 30px;
        }
        
        .header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            background: #fcfeff;
            color: black;
            padding: 20px 30px;
            border-bottom: 1px solid #bdc3c7;
        }
        
        .header h1 {
            font-size: 24px;
            font-weight: 600;
            margin-bottom: 5px;
        }
        
        .header .subtitle {
            font-size: 13px;
            opacity: 0.9;
        }
        
        .header img { 
            vertical-align: middle;
        }
        
        .inside-header { 
            display: inline-block; 
        }
        
        .nav {
            background: #ecf0f1;
            padding: 12px 30px;
            border-bottom: 1px solid #bdc3c7;
        }
        
        .nav a {
            color: #2980b9;
            text-decoration: none;
            margin-right: 20px;
            font-weight: 500;
            padding: 6px 12px;
            border-radius: 3px;
            transition: background 0.2s;
        }
        
        .nav a:hover {
            background: #d5dbdb;
        }
        
        h2 {
            font-size: 20px;
            margin: 30px 0 15px 0;
            padding-bottom: 8px;
            border-bottom: 2px solid #3498db;
            color: #2c3e50;
        }
        
        h3 {
            font-size: 18px;
            margin: 20px 0 10px 0;
            color: #34495e;
        }
        
        table {
            width: 100%;
            border-collapse: collapse;
            margin: 15px 0;
            border: 1px solid #bdc3c7;
            background: #fff;
        }
        
        th {
            background: #dce8f5;
            color: black;
            padding: 12px;
            text-align: left;
            font-weight: 600;
            font-size: 13px;
            border: 1px solid #2c3e50;
        }
        
        td {
            padding: 10px 12px;
            border: 1px solid #bdc3c7;
            font-size: 14px;
        }
        
        tbody tr:nth-child(even) {
            background: #f8f9fa;
        }
        
        tbody tr:hover {
            background: #e8f4f8;
        }
        
        .pass {
            color: #27ae60;
            font-weight: 600;
        }
        
        .fail {
            color: #e74c3c;
            font-weight: 600;
        }
        
        .info-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 15px;
            margin: 20px 0;
        }
        
        .info-card {
            padding: 15px;
            border: 1px solid #bdc3c7;
            background: #ecf0f1;
        }
        
        .info-card label {
            display: block;
            font-weight: 600;
            margin-bottom: 5px;
            font-size: 12px;
            color: #7f8c8d;
            text-transform: uppercase;
        }
        
        .info-card .value {
            font-size: 18px;
            font-weight: 600;
            color: #2c3e50;
        }
        
        .recent-test-section {
            margin: 70px 0;
            background: #fff;
        }
        
        .recent-test-section h2 {
            color: #2c3e50;
            margin-top: 0;
            border-bottom: 2px solid #3498db;
        }
        
        .test-status-badge {
            display: inline-block;
            padding: 8px 16px;
            border-radius: 4px;
            font-weight: 600;
            font-size: 14px;
            margin: 10px 0;
        }
        
        .test-status-badge.passed {
            background: #d4edda;
            color: #155724;
            border: 1px solid #c3e6cb;
        }
        
        .test-status-badge.failed {
            background: #f8d7da;
            color: #721c24;
            border: 1px solid #f5c6cb;
        }
        
        .test-details-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
            gap: 15px;
            margin: 20px 0;
        }
        
        .detail-box {
            padding: 12px;
            background: #f8f9fa;
            border: 1px solid #dee2e6;
            border-radius: 4px;
        }
        
        .detail-box strong {
            color: #495057;
            display: block;
            margin-bottom: 5px;
            font-size: 12px;
            text-transform: uppercase;
        }
        
        .detail-box .value {
            color: #212529;
            font-size: 15px;
        }
        
        .steps-table {
            margin: 15px 0;
        }
        
        .steps-table td {
            font-size: 13px;
        }
        
        .step-passed {
            background: #d4edda !important;
            color: #155724;
        }
        
        .step-failed {
            background: #f8d7da !important;
            color: #721c24;
        }
        
        .step-skipped {
            background: #fff3cd !important;
            color: #856404;
        }
        
        .charts-section {
            margin: 25px 0;
        }
        
        .chart-container {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(400px, 1fr));
            gap: 20px;
            margin: 20px 0;
        }
        
        .chart-box {
            border: 1px solid #dee2e6;
            padding: 15px;
            background: #fff;
            text-align: center;
        }
        
        .chart-box h4 {
            margin-bottom: 10px;
            color: #495057;
            font-size: 16px;
        }
        
        .chart-box img {
            max-width: 100%;
            height: auto;
            border: 1px solid #dee2e6;
        }
        
        .failure-message {
            background: #fff5f5;
            border-left: 4px solid #e74c3c;
            padding: 15px;
            margin: 15px 0;
            border-radius: 4px;
        }
        
        .failure-message strong {
            color: #c0392b;
            display: block;
            margin-bottom: 8px;
        }
        
        .failure-message pre {
            background: #fff;
            padding: 10px;
            border: 1px solid #f5c6cb;
            border-radius: 3px;
            overflow-x: auto;
            font-size: 12px;
            margin-top: 8px;
        }
        
        .footer {
            text-align: center;
            padding: 20px;
            background: #fcfeff;
            color: black;
            font-size: 12px;
            border-top: 1px solid #bdc3c7;
        }
        
        .footer p {
            margin: 5px 0;
        }
        
        @media print {
            .nav {
                display: none;
            }
            body {
                background: #fff;
            }
            .container {
                box-shadow: none;
            }
        }
        
        @media (max-width: 768px) {
            .info-grid, .test-details-grid, .chart-container {
                grid-template-columns: 1fr;
            }
        }
        """
    
    def _generate_recent_test_section(self, all_tests: List[Dict]) -> str:
        """Generate recent test execution details section"""
        
        if not all_tests:
            return ""
        
        # Get the most recent test
        recent_test = sorted(all_tests, key=lambda x: x.get('test_time', ''), reverse=True)[0]
        
        status = recent_test.get('status', 'unknown').lower()
        status_class = 'passed' if status == 'passed' else 'failed'
        status_icon = '✅' if status == 'passed' else '❌'
        
        html = f"""
        <div class="recent-test-section">
            <h2>Most Recent Test Execution</h2>
            
            <div style="margin: 15px 0;">
                <span class="test-status-badge {status_class}">
                    {status_icon} Test {status.upper()}
                </span>
                <span style="margin-left: 15px; color: #7f8c8d;">
                    Executed on {self._format_date(recent_test.get('test_time'))}
                </span>
            </div>
            
            <h3>Test Information</h3>
            <div class="test-details-grid">
                <div class="detail-box">
                    <strong>Router Name</strong>
                    <div class="value">{recent_test.get('router_name', 'N/A')}</div>
                </div>
                <div class="detail-box">
                    <strong>Router Model</strong>
                    <div class="value">{recent_test.get('router_model', 'N/A')}</div>
                </div>
                <div class="detail-box">
                    <strong>MAC Address</strong>
                    <div class="value" style="font-family: monospace;">{recent_test.get('router_mac', 'N/A')}</div>
                </div>
                <div class="detail-box">
                    <strong>Firmware Version</strong>
                    <div class="value">{recent_test.get('router_firmware', 'N/A')}</div>
                </div>
                <div class="detail-box">
                    <strong>Feature Tested</strong>
                    <div class="value">{recent_test.get('feature_name', 'N/A')}</div>
                </div>
                <div class="detail-box">
                    <strong>Scenario</strong>
                    <div class="value">{recent_test.get('scenario_name', 'N/A')}</div>
                </div>
                <div class="detail-box">
                    <strong>Number of Clients</strong>
                    <div class="value">{recent_test.get('number_of_clients', 'N/A')}</div>
                </div>
                <div class="detail-box">
                    <strong>Test Duration</strong>
                    <div class="value">{self._format_duration((datetime.fromisoformat(str(recent_test.get('end_time', '')).replace('Z', '+00:00')) - datetime.fromisoformat(str(recent_test.get('start_time', '')).replace('Z', '+00:00'))).total_seconds()) if recent_test.get('start_time') and recent_test.get('end_time') else 'N/A'}</div>
                </div>
            </div>
"""
        
        # Performance Metrics
        if any([recent_test.get('router_avg_cpu_creation'), recent_test.get('router_avg_cpu_test'), recent_test.get('time_taken')]):
            html += """
            <h3>Performance Metrics</h3>
            <div class="test-details-grid">
"""
            
            if recent_test.get('router_avg_cpu_creation') is not None:
                html += f"""
                <div class="detail-box">
                    <strong>CPE CPU (Client Creation)</strong>
                    <div class="value">{recent_test.get('router_avg_cpu_creation', 0):.2f}%</div>
                </div>
"""
            
            if recent_test.get('router_avg_cpu_test') is not None:
                html += f"""
                <div class="detail-box">
                    <strong>CPE CPU (During Test)</strong>
                    <div class="value">{recent_test.get('router_avg_cpu_test', 0):.2f}%</div>
                </div>
"""
            
            if recent_test.get('time_taken') is not None:
                html += f"""
                <div class="detail-box">
                    <strong>Time Taken</strong>
                    <div class="value">{recent_test.get('time_taken', 0):.2f} seconds</div>
                </div>
"""
            
            html += """
            </div>
"""
        
        # Test Steps Details
        steps_data = recent_test.get('steps_data', [])
        if steps_data:
            html += """
            <h3>Test Steps Execution</h3>
            <table class="steps-table">
                <thead>
                    <tr>
                        <th style="width: 100px;">Step Type</th>
                        <th>Step Description</th>
                        <th style="width: 100px;">Status</th>
                        <th style="width: 300px;">Details</th>
                    </tr>
                </thead>
                <tbody>
"""
            
            for step in steps_data:
                step_status = step.get('status', 'unknown')
                step_class = f"step-{step_status.lower()}" if step_status in ['passed', 'failed', 'skipped'] else ""
                step_icon = '✅' if step_status == 'passed' else '❌' if step_status == 'failed' else '⏭️'
                
                failure_msg = step.get('failure_message', '') if step_status != 'passed' else ''
                
                html += f"""
                    <tr class="{step_class}">
                        <td><strong>{step.get('keyword', 'Step')}</strong></td>
                        <td>{step.get('name', 'N/A')}</td>
                        <td style="text-align: center;">{step_icon} {step_status.upper()}</td>
                        <td style="font-size: 12px;">{failure_msg}</td>
                    </tr>
"""
            
            html += """
                </tbody>
            </table>
"""
        
        # Failure Details (if test failed)
        if status == 'failed':
            failure_reason = recent_test.get('failure_reason', 'Unknown error')
            html += f"""
            <div class="failure-message">
                <strong>Failure Details:</strong>
                <pre>{failure_reason}</pre>
            </div>
"""
        
        # Charts Section - Look for chart images in test_reports directory
        chart_files = []
        if os.path.exists('test_reports'):
            for file in os.listdir('test_reports'):
                if file.endswith('.png') and any(keyword in file.lower() for keyword in ['cpu', 'time', 'chart', 'graph']):
                    chart_files.append(file)
        
        # Sort to get most recent charts (assuming timestamp in filename)
        chart_files.sort(reverse=True)
        
        if chart_files:
            html += """
            <h3>Performance Charts</h3>
            <div class="charts-section">
                <div class="chart-container">
"""
            
            # Copy charts to report directory and display them
            chart_titles = {
                'cpu': 'CPE CPU Utilization',
                'time': 'Time Taken Analysis',
                'linux': 'Linux CPU Utilization'
            }
            
            displayed_charts = set()
            for chart_file in chart_files[:6]:  # Limit to 6 most recent charts
                # Determine chart type
                chart_type = None
                for key in chart_titles.keys():
                    if key in chart_file.lower():
                        chart_type = key
                        break
                
                # Avoid duplicate chart types
                if chart_type and chart_type not in displayed_charts:
                    displayed_charts.add(chart_type)
                    
                    # Copy chart to report directory
                    src_path = os.path.join('test_reports', chart_file)
                    if self.report_dir and os.path.exists(src_path):
                        dst_path = os.path.join(self.report_dir, chart_file)
                        try:
                            shutil.copy2(src_path, dst_path)
                            
                            html += f"""
                    <div class="chart-box">
                        <h4>{chart_titles.get(chart_type, 'Performance Chart')}</h4>
                        <img src="{chart_file}" alt="{chart_titles.get(chart_type, 'Chart')}">
                    </div>
"""
                        except Exception as e:
                            print(f"Warning: Could not copy chart {chart_file}: {e}")
            
            html += """
                </div>
            </div>
"""
        
        html += """
        </div>
        """
        
        return html
    
    def _generate_summary_page(self, aggregated_data: Dict, timestamp: str, all_tests: List[Dict]) -> str:
        """Generate summary/index page"""
        
        total_tests = sum(d['total_tests'] for d in aggregated_data.values())
        total_passed = sum(d['passed_tests'] for d in aggregated_data.values())
        total_failed = sum(d['failed_tests'] for d in aggregated_data.values())
        total_routers = len(aggregated_data)
        
        html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Test Report - Summary</title>
    <style>{self._get_css()}</style>
</head>
<body>
    <div class="container">
        {self._get_header_html()}
        
        <div class="nav">
            <a href="index.html">Summary</a>
            <a href="failures.html">Failure Analysis</a>
        </div>
        
        <div class="content-wrapper">
            <h2>Overview</h2>
            
            <div class="info-grid">
                <div class="info-card">
                    <label>Total Routers</label>
                    <div class="value">{total_routers}</div>
                </div>
                <div class="info-card">
                    <label>Total Tests</label>
                    <div class="value">{total_tests}</div>
                </div>
                <div class="info-card">
                    <label>Passed Tests</label>
                    <div class="value pass">{total_passed}</div>
                </div>
                <div class="info-card">
                    <label>Failed Tests</label>
                    <div class="value fail">{total_failed}</div>
                </div>
                <div class="info-card">
                    <label>Pass Rate</label>
                    <div class="value">{(total_passed/total_tests*100 if total_tests > 0 else 0):.1f}%</div>
                </div>
            </div>
            
            <h2>Router Summary</h2>
            
            <table>
                <thead>
                    <tr>
                        <th>Router Name</th>
                        <th>Model</th>
                        <th>MAC Address</th>
                        <th>Total Tests</th>
                        <th>Passed</th>
                        <th>Failed</th>
                        <th>Pass Rate</th>
                        <th>Total Duration</th>
                        <th>Details</th>
                    </tr>
                </thead>
                <tbody>
"""
        
        for router_mac, router_data in sorted(aggregated_data.items(), 
                                             key=lambda x: x[1]['router_name']):
            router_name = router_data['router_name']
            router_model = router_data['router_model']
            total = router_data['total_tests']
            passed = router_data['passed_tests']
            failed = router_data['failed_tests']
            pass_rate = (passed / total * 100) if total > 0 else 0
            
            # Create safe filename
            filename = f"{router_name}_{router_model}".replace(' ', '_').replace('/', '_')
            
            html += f"""
                <tr>
                    <td><strong>{router_name}</strong></td>
                    <td>{router_model}</td>
                    <td style="font-family: monospace;">{router_data['router_mac']}</td>
                    <td>{total}</td>
                    <td class="pass">{passed}</td>
                    <td class="fail">{failed}</td>
                    <td>{pass_rate:.1f}%</td>
                    <td>{self._format_duration(router_data['total_duration'])}</td>
                    <td><a href="{filename}.html">View Details →</a></td>
                </tr>
"""
        
        html += """
                </tbody>
            </table>
"""
        
        # Add Recent Test Section
        html += self._generate_recent_test_section(all_tests)
        
        html += """
        </div>
        
        """ + self._get_footer_html() + """
    </div>
</body>
</html>
"""
        
        return html
    
    def _generate_router_page(self, router_mac: str, router_data: Dict) -> str:
        """Generate individual router detail page"""
        
        router_name = router_data['router_name']
        router_model = router_data['router_model']
        
        html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{router_name} - {router_model}</title>
    <style>{self._get_css()}</style>
</head>
<body>
    <div class="container">
        {self._get_header_html()}
        
        <div class="nav">
            <a href="index.html">← Back to Summary</a>
            <a href="failures.html">Failure Analysis</a>
        </div>
        
        <div class="content-wrapper">
            <h2>Router Information - {router_name} ({router_model})</h2>
            
            <div class="info-grid">
                <div class="info-card">
                    <label>Router Name</label>
                    <div class="value">{router_name}</div>
                </div>
                <div class="info-card">
                    <label>Model</label>
                    <div class="value">{router_model}</div>
                </div>
                <div class="info-card">
                    <label>MAC Address</label>
                    <div class="value" style="font-family: monospace;">{router_data['router_mac']}</div>
                </div>
                <div class="info-card">
                    <label>Firmware</label>
                    <div class="value">{router_data['router_firmware']}</div>
                </div>
                <div class="info-card">
                    <label>Total Tests</label>
                    <div class="value">{router_data['total_tests']}</div>
                </div>
                <div class="info-card">
                    <label>Passed</label>
                    <div class="value pass">{router_data['passed_tests']}</div>
                </div>
                <div class="info-card">
                    <label>Failed</label>
                    <div class="value fail">{router_data['failed_tests']}</div>
                </div>
                <div class="info-card">
                    <label>Total Duration</label>
                    <div class="value">{self._format_duration(router_data['total_duration'])}</div>
                </div>
            </div>
            
            <h2>Test History</h2>
"""
        
        # Organize tests by feature
        for feature_name, tests in sorted(router_data['features'].items()):
            html += f"""
            <h3>Feature: {feature_name}</h3>
            
            <table>
                <thead>
                    <tr>
                        <th>Date</th>
                        <th>Scenario</th>
                        <th>Clients</th>
                        <th>Status</th>
                        <th>CPE CPU (Create %)</th>
                        <th>CPE CPU (Test %)</th>
                        <th>Duration</th>
                        <th>Steps</th>
                    </tr>
                </thead>
                <tbody>
"""
            
            # Sort by date (newest first)
            sorted_tests = sorted(tests, key=lambda x: x.get('test_time', ''), reverse=True)
            
            for test in sorted_tests:
                status = test.get('status', 'unknown').lower()
                status_class = 'pass' if status == 'passed' else 'fail'
                
                # Calculate duration
                start_time = test.get('start_time')
                end_time = test.get('end_time')
                duration = '00:00:00'
                if start_time and end_time:
                    try:
                        if isinstance(start_time, str):
                            start_time = datetime.fromisoformat(start_time.replace('Z', '+00:00'))
                        if isinstance(end_time, str):
                            end_time = datetime.fromisoformat(end_time.replace('Z', '+00:00'))
                        duration = self._format_duration((end_time - start_time).total_seconds())
                    except:
                        pass
                
                # Get values or N/A
                clients = test.get('number_of_clients')
                clients_display = str(clients) if clients is not None else 'N/A'
                
                cpu_create = test.get('router_avg_cpu_creation')
                cpu_create_display = f"{cpu_create:.2f}" if cpu_create is not None else 'N/A'
                
                cpu_test = test.get('router_avg_cpu_test')
                cpu_test_display = f"{cpu_test:.2f}" if cpu_test is not None else 'N/A'
                
                # Get step summary
                steps_data = test.get('steps_data', [])
                if steps_data:
                    passed_steps = sum(1 for s in steps_data if s.get('status') == 'passed')
                    total_steps = len(steps_data)
                    step_summary = f"{passed_steps}/{total_steps}"
                else:
                    step_summary = "N/A"
                
                html += f"""
                    <tr>
                        <td>{self._format_date(test.get('test_time'))}</td>
                        <td>{test.get('scenario_name', 'N/A')}</td>
                        <td>{clients_display}</td>
                        <td class="{status_class}">{status.upper()}</td>
                        <td>{cpu_create_display}</td>
                        <td>{cpu_test_display}</td>
                        <td>{duration}</td>
                        <td>{step_summary}</td>
                    </tr>
"""
            
            html += """
                </tbody>
            </table>
"""
        
        html += """
        </div>
        
        """ + self._get_footer_html() + """
    </div>
</body>
</html>
"""
        
        return html
    
    def _generate_failures_page(self, aggregated_data: Dict) -> str:
        """Generate failure analysis page"""
        
        html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Failure Analysis</title>
    <style>{self._get_css()}</style>
</head>
<body>
    <div class="container">
        {self._get_header_html()}
        
        <div class="nav">
            <a href="index.html">← Back to Summary</a>
        </div>
        
        <div class="content-wrapper">
            <h2>Failure Analysis</h2>
"""
        
        # Collect all failures
        all_failures = []
        for router_mac, router_data in aggregated_data.items():
            for test in router_data['failed_tests_details']:
                test['_router_name'] = router_data['router_name']
                test['_router_model'] = router_data['router_model']
                all_failures.append(test)
        
        if not all_failures:
            html += """
            <p style="text-align: center; padding: 60px; color: #7f8c8d; font-size: 16px;">
                ✓ No failed tests found. All tests passed successfully!
            </p>
"""
        else:
            # Sort by date (newest first)
            all_failures.sort(key=lambda x: x.get('test_time', ''), reverse=True)
            
            html += f"""
            <p style="margin-bottom: 20px; color: #7f8c8d;">
                Total Failed Tests: <strong style="color: #e74c3c; font-size: 18px;">{len(all_failures)}</strong>
            </p>
            
            <table>
                <thead>
                    <tr>
                        <th>Router</th>
                        <th>Feature</th>
                        <th>Scenario</th>
                        <th>Date</th>
                        <th>Failed Step</th>
                        <th>Status</th>
                        <th>Error Message</th>
                    </tr>
                </thead>
                <tbody>
"""
            
            for test in all_failures:
                steps_data = test.get('steps_data', [])
                failed_step = None
                error_message = test.get('failure_reason', 'Unknown error')
                step_status = 'FAILED'
                
                # Find failed step
                for step in steps_data:
                    if step.get('status') in ['failed', 'undefined']:
                        failed_step = f"{step.get('keyword', '')} {step.get('name', '')}"
                        error_message = step.get('failure_message', error_message)
                        step_status = step.get('status', 'FAILED').upper()
                        break
                
                if not failed_step:
                    failed_step = test.get('scenario_name', 'Unknown')
                
                # Highlight UNDEFINED steps differently
                row_style = ' style="background: #fff3cd;"' if step_status == 'UNDEFINED' else ''
                
                html += f"""
                    <tr{row_style}>
                        <td><strong>{test['_router_name']}-{test['_router_model']}</strong></td>
                        <td>{test.get('feature_name', 'N/A')}</td>
                        <td>{test.get('scenario_name', 'N/A')}</td>
                        <td>{self._format_date(test.get('test_time'))}</td>
                        <td style="font-family: monospace; font-size: 13px;">{failed_step}</td>
                        <td class="fail">{step_status}</td>
                        <td style="font-family: monospace; font-size: 12px; max-width: 400px;">{error_message}</td>
                    </tr>
"""
            
            html += """
                </tbody>
            </table>
"""
        
        html += """
        </div>
        
        """ + self._get_footer_html() + """
    </div>
</body>
</html>
"""
        
        return html
    
    def generate_html_report(self, all_tests: List[Dict]) -> str:
        """Generate multi-page HTML report"""
        
        if not all_tests:
            return self._generate_empty_report()
        
        # Create timestamped directory for this report
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        self.report_dir = os.path.join("test_reports", f"report_{timestamp}")
        os.makedirs(self.report_dir, exist_ok=True)
        
        # Aggregate data
        aggregated_data = self._aggregate_router_data(all_tests)
        
        # Generate summary page (index.html)
        summary_html = self._generate_summary_page(aggregated_data, timestamp, all_tests)
        with open(os.path.join(self.report_dir, 'index.html'), 'w', encoding='utf-8') as f:
            f.write(summary_html)
        
        # Generate individual router pages
        for router_mac, router_data in aggregated_data.items():
            router_name = router_data['router_name']
            router_model = router_data['router_model']
            filename = f"{router_name}_{router_model}".replace(' ', '_').replace('/', '_')
            
            router_html = self._generate_router_page(router_mac, router_data)
            with open(os.path.join(self.report_dir, f'{filename}.html'), 'w', encoding='utf-8') as f:
                f.write(router_html)
        
        # Generate failures page
        failures_html = self._generate_failures_page(aggregated_data)
        with open(os.path.join(self.report_dir, 'failures.html'), 'w', encoding='utf-8') as f:
            f.write(failures_html)
        
        # Set permissions for all files
        self._set_permissions()
        
        # Return path to index page
        return os.path.join(self.report_dir, 'index.html')
    
    def _set_permissions(self):
        """Set read permissions for all files in report directory"""
        try:
            # Set directory permissions
            os.chmod(self.report_dir, 0o755)
            
            # Set file permissions for all files
            for filename in os.listdir(self.report_dir):
                filepath = os.path.join(self.report_dir, filename)
                if os.path.isfile(filepath):
                    os.chmod(filepath, 0o644)
        except Exception as e:
            print(f"Warning: Could not set permissions: {e}")
    
    def _generate_empty_report(self) -> str:
        """Generate empty state report"""
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        self.report_dir = os.path.join("test_reports", f"report_{timestamp}")
        os.makedirs(self.report_dir, exist_ok=True)
        
        html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Test Report - No Data</title>
    <style>{self._get_css()}</style>
</head>
<body>
    <div class="container">
        {self._get_header_html()}
        <div class="content-wrapper">
            <p style="text-align: center; padding: 60px; color: #7f8c8d; font-size: 16px;">
                No test data available. Run some tests to generate a report.
            </p>
        </div>
        {self._get_footer_html()}
    </div>
</body>
</html>
"""
        
        filepath = os.path.join(self.report_dir, 'index.html')
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(filepath)
        
        self._set_permissions()
        
        return filepath