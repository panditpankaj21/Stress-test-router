"""
Auto-updating Excel Statistics Generator
Creates a comprehensive test history with clickable navigation and visual progress bars
"""
from openpyxl import Workbook, load_workbook
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.chart import BarChart, Reference
from openpyxl.utils import get_column_letter
from datetime import datetime
from typing import List, Dict, Any
import os
from collections import defaultdict


class ExcelStatisticsGenerator:
    def __init__(self, excel_path: str = "test_reports/test_statistics.xlsx"):
        """Initialize Excel statistics generator"""
        self.excel_path = excel_path
        self.ensure_excel_exists()
        
        # Define color schemes
        self.colors = {
            'header': '366092',
            'pass': '92D050',      # Green
            'fail': 'FF0000',      # Red
            'subheader': 'D9E1F2',
            'link': '0563C1',
            'border': '000000'
        }
        
        # Define styles
        self.header_font = Font(name='Calibri', size=12, bold=True, color='FFFFFF')
        self.subheader_font = Font(name='Calibri', size=11, bold=True)
        self.normal_font = Font(name='Calibri', size=10)
        self.bold_font = Font(name='Calibri', size=10, bold=True)
        self.link_font = Font(name='Calibri', size=10, color=self.colors['link'], underline='single')
        
        self.thin_border = Border(
            left=Side(style='thin'),
            right=Side(style='thin'),
            top=Side(style='thin'),
            bottom=Side(style='thin')
        )
    
    def ensure_excel_exists(self):
        """Ensure the Excel file and directory exist"""
        os.makedirs(os.path.dirname(self.excel_path), exist_ok=True)
        if not os.path.exists(self.excel_path):
            wb = Workbook()
            wb.save(self.excel_path)
            wb.close()
    
    def _get_router_sheet_name(self, router_name: str, router_model: str) -> str:
        """Generate safe sheet name: Name-Model"""
        sheet_name = f"{router_name}-{router_model}"
        # Excel sheet names max 31 chars, no special chars
        sheet_name = sheet_name[:31]
        for char in ['/', '\\', '?', '*', '[', ']', ':']:
            sheet_name = sheet_name.replace(char, '_')
        return sheet_name
    
    def _aggregate_router_data(self, all_tests: List[Dict]) -> Dict:
        """
        Aggregate test data by router
        
        Returns:
        {
            'router_mac': {
                'router_name': 'Name',
                'router_model': 'Model',
                'router_firmware': 'Firmware',
                'total_tests': count,
                'passed_tests': count,
                'failed_tests': count,
                'features': {
                    'feature_name': [list of tests]
                }
            }
        }
        """
        aggregated = defaultdict(lambda: {
            'router_name': None,
            'router_model': None,
            'router_firmware': None,
            'router_mac': None,
            'total_tests': 0,
            'passed_tests': 0,
            'failed_tests': 0,
            'features': defaultdict(list)
        })
        
        for test in all_tests:
            router_mac = test.get('router_mac')
            if not router_mac:
                continue
            
            router_data = aggregated[router_mac]
            
            # Set router info (from most recent test data)
            if not router_data['router_name']:
                router_data['router_name'] = test.get('router_name', 'Unknown')
                router_data['router_model'] = test.get('router_model', 'Unknown')
                router_data['router_firmware'] = test.get('router_firmware', 'Unknown')
                router_data['router_mac'] = router_mac
            
            # Count tests
            router_data['total_tests'] += 1
            status = test.get('status', '').lower()
            if status == 'passed':
                router_data['passed_tests'] += 1
            else:
                router_data['failed_tests'] += 1
            
            # Group by feature
            feature_name = test.get('feature_name', 'Unknown Feature')
            router_data['features'][feature_name].append(test)
        
        return dict(aggregated)
    
    def _create_progress_bar_cells(self, ws, row: int, col: int, 
                                   passed: int, total: int, bar_width: int = 20):
        """
        Create a visual progress bar using colored cells
        
        Args:
            ws: Worksheet
            row: Starting row
            col: Starting column
            passed: Number of passed tests
            total: Total number of tests
            bar_width: Width of progress bar in cells
        """
        if total == 0:
            pass_percentage = 0
        else:
            pass_percentage = (passed / total) * 100
        
        # Calculate how many cells should be green
        green_cells = int((passed / total) * bar_width) if total > 0 else 0
        
        # Create progress bar
        for i in range(bar_width):
            cell = ws.cell(row=row, column=col + i)
            cell.border = self.thin_border
            
            if i < green_cells:
                # Green (passed)
                cell.fill = PatternFill(start_color=self.colors['pass'], 
                                       end_color=self.colors['pass'], 
                                       fill_type='solid')
            else:
                # Red (failed)
                cell.fill = PatternFill(start_color=self.colors['fail'], 
                                       end_color=self.colors['fail'], 
                                       fill_type='solid')
        
        # Add percentage text after the bar
        percentage_cell = ws.cell(row=row, column=col + bar_width)
        percentage_cell.value = f"{pass_percentage:.1f}%"
        percentage_cell.font = self.bold_font
        percentage_cell.alignment = Alignment(horizontal='left', vertical='center')
    
    def _create_summary_sheet(self, wb: Workbook, aggregated_data: Dict):
        """Create or update the summary sheet"""
        
        # Remove existing summary sheet if present
        if "Test Summary" in wb.sheetnames:
            wb.remove(wb["Test Summary"])
        
        ws = wb.create_sheet("Test Summary", 0)
        
        # Title
        ws.merge_cells('A1:C1')
        ws['A1'] = '📊 Router Test Statistics - Summary'
        ws['A1'].font = self.header_font
        ws['A1'].fill = PatternFill(start_color=self.colors['header'], 
                                    end_color=self.colors['header'], 
                                    fill_type='solid')
        ws['A1'].alignment = Alignment(horizontal='center', vertical='center')
        ws.row_dimensions[1].height = 30
        
        # Last updated
        row = 3
        ws[f'A{row}'] = 'Last Updated:'
        ws[f'B{row}'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        ws[f'A{row}'].font = self.bold_font
        ws.merge_cells(f'B{row}:C{row}')
        
        # Headers for router list
        row += 2
        headers = ['Router Name', 'Tests (Passed/Total)', 'Success Rate']
        for col_idx, header in enumerate(headers, start=1):
            cell = ws.cell(row=row, column=col_idx)
            cell.value = header
            cell.font = self.header_font
            cell.fill = PatternFill(start_color=self.colors['header'], 
                                   end_color=self.colors['header'], 
                                   fill_type='solid')
            cell.border = self.thin_border
            cell.alignment = Alignment(horizontal='center', vertical='center')
        
        ws.row_dimensions[row].height = 25
        
        # Router data rows
        row += 1
        for router_mac, router_data in sorted(aggregated_data.items(), 
                                             key=lambda x: x[1]['router_name']):
            router_name = router_data['router_name']
            router_model = router_data['router_model']
            total_tests = router_data['total_tests']
            passed_tests = router_data['passed_tests']
            
            # Router name as clickable link
            sheet_name = self._get_router_sheet_name(router_name, router_model)
            router_display = f"{router_name}-{router_model}"
            
            cell = ws.cell(row=row, column=1)
            cell.value = router_display
            cell.hyperlink = f"#{sheet_name}!A1"
            cell.font = self.link_font
            cell.border = self.thin_border
            cell.alignment = Alignment(horizontal='left', vertical='center')
            
            # Tests count
            cell = ws.cell(row=row, column=2)
            cell.value = f"{passed_tests}/{total_tests}"
            cell.border = self.thin_border
            cell.alignment = Alignment(horizontal='center', vertical='center')
            cell.font = self.normal_font
            
            # Progress bar (starts at column 3, spans 20 cells)
            self._create_progress_bar_cells(ws, row, 3, passed_tests, total_tests, bar_width=20)
            
            row += 1
        
        # Legend
        row += 2
        ws[f'A{row}'] = 'Legend:'
        ws[f'A{row}'].font = self.bold_font
        
        row += 1
        ws[f'A{row}'] = 'Green'
        ws[f'A{row}'].fill = PatternFill(start_color=self.colors['pass'], 
                                        end_color=self.colors['pass'], 
                                        fill_type='solid')
        ws[f'A{row}'].border = self.thin_border
        ws[f'B{row}'] = 'Passed Tests'
        
        row += 1
        ws[f'A{row}'] = 'Red'
        ws[f'A{row}'].fill = PatternFill(start_color=self.colors['fail'], 
                                        end_color=self.colors['fail'], 
                                        fill_type='solid')
        ws[f'A{row}'].border = self.thin_border
        ws[f'B{row}'] = 'Failed Tests'
        
        # Adjust column widths
        ws.column_dimensions['A'].width = 35
        ws.column_dimensions['B'].width = 18
        for i in range(3, 24):  # Progress bar columns
            ws.column_dimensions[get_column_letter(i)].width = 2
    
    def _create_router_detail_sheet(self, wb: Workbook, router_mac: str, router_data: Dict):
        """
        STEP 3: Create detailed sheet for a specific router
        Shows all test results organized by feature with complete details
        """
        
        router_name = router_data['router_name']
        router_model = router_data['router_model']
        sheet_name = self._get_router_sheet_name(router_name, router_model)
        
        # Remove existing sheet if present
        if sheet_name in wb.sheetnames:
            wb.remove(wb[sheet_name])
        
        ws = wb.create_sheet(sheet_name)
        
        # Title
        ws.merge_cells('A1:I1')
        ws['A1'] = f'🔧 {router_name}-{router_model} - Detailed Test History'
        ws['A1'].font = self.header_font
        ws['A1'].fill = PatternFill(start_color=self.colors['header'], 
                                    end_color=self.colors['header'], 
                                    fill_type='solid')
        ws['A1'].alignment = Alignment(horizontal='center', vertical='center')
        ws.row_dimensions[1].height = 30
        
        # Router details
        row = 3
        details = [
            ('Router Name:', router_name),
            ('Model:', router_model),
            ('MAC Address:', router_data['router_mac']),
            ('Firmware:', router_data['router_firmware']),
            ('Total Tests:', router_data['total_tests']),
            ('Passed:', router_data['passed_tests']),
            ('Failed:', router_data['failed_tests'])
        ]
        
        for label, value in details:
            ws[f'A{row}'] = label
            ws[f'A{row}'].font = self.bold_font
            ws[f'B{row}'] = value
            ws[f'B{row}'].font = self.normal_font
            row += 1
        
        # Back to summary link
        row += 1
        ws[f'A{row}'] = '← Back to Summary'
        ws[f'A{row}'].hyperlink = "#'Test Summary'!A1"
        ws[f'A{row}'].font = self.link_font
        
        # Feature-wise test details
        row += 3
        
        for feature_name, tests in sorted(router_data['features'].items()):
            # Feature header
            ws.merge_cells(f'A{row}:I{row}')
            ws[f'A{row}'] = f'📁 {feature_name}'
            ws[f'A{row}'].font = self.subheader_font
            ws[f'A{row}'].fill = PatternFill(start_color=self.colors['subheader'], 
                                            end_color=self.colors['subheader'], 
                                            fill_type='solid')
            ws[f'A{row}'].alignment = Alignment(horizontal='left', vertical='center')
            ws[f'A{row}'].border = self.thin_border
            row += 1
            
            # Test table headers (removed Linux CPU columns)
            headers = [
                'Date', 'Time', 'Scenario', 'Clients', 'Status', 
                'Router CPE\n(Creation %)', 'Router CPE\n(Test %)', 
                'Time Taken (s)', 'Failure Reason'
            ]
            
            for col_idx, header in enumerate(headers, start=1):
                cell = ws.cell(row=row, column=col_idx)
                cell.value = header
                cell.font = Font(name='Calibri', size=9, bold=True, color='FFFFFF')
                cell.fill = PatternFill(start_color=self.colors['header'], 
                                    end_color=self.colors['header'], 
                                    fill_type='solid')
                cell.border = self.thin_border
                cell.alignment = Alignment(horizontal='center', vertical='center', wrap_text=True)
            
            ws.row_dimensions[row].height = 30
            row += 1
            
            # Sort tests by date (newest first)
            sorted_tests = sorted(tests, 
                                key=lambda x: x.get('test_time', ''), 
                                reverse=True)
            
            # Test data rows
            for test in sorted_tests:
                # Parse test time
                test_time = test.get('test_time', '')
                if test_time:
                    if isinstance(test_time, str):
                        try:
                            dt = datetime.fromisoformat(test_time.replace('Z', '+00:00'))
                            test_date = dt.strftime('%d %b %Y')  # Format: 17 Feb 2026
                            test_time_str = dt.strftime('%H:%M:%S')
                        except:
                            test_date = test_time[:10] if len(test_time) >= 10 else 'N/A'
                            test_time_str = 'N/A'
                    else:
                        test_date = test_time.strftime('%d %b %Y')  # Format: 17 Feb 2026
                        test_time_str = test_time.strftime('%H:%M:%S')
                else:
                    test_date = 'N/A'
                    test_time_str = 'N/A'
                
                status = test.get('status', 'unknown').lower()
                failure_reason = test.get('failure_reason', '') if status != 'passed' else ''
                
                # Data (removed Linux CPU columns)
                data_row = [
                    test_date,
                    test_time_str,
                    test.get('scenario_name', 'N/A'),
                    test.get('number_of_clients', 'N/A'),
                    test.get('status', 'unknown').upper(),
                    round(test.get('router_avg_cpu_creation', 0), 2),
                    round(test.get('router_avg_cpu_test', 0), 2),
                    round(test.get('time_taken', 0), 2),
                    failure_reason
                ]
                
                for col_idx, value in enumerate(data_row, start=1):
                    cell = ws.cell(row=row, column=col_idx)
                    cell.value = value
                    cell.border = self.thin_border
                    cell.alignment = Alignment(horizontal='center', vertical='center')
                    cell.font = Font(name='Calibri', size=9)
                    
                    # Color code status column
                    if col_idx == 5:  # Status column
                        if status == 'passed':
                            cell.fill = PatternFill(start_color=self.colors['pass'], 
                                                end_color=self.colors['pass'], 
                                                fill_type='solid')
                            cell.font = Font(name='Calibri', size=9, bold=True, color='FFFFFF')
                        else:
                            cell.fill = PatternFill(start_color=self.colors['fail'], 
                                                end_color=self.colors['fail'], 
                                                fill_type='solid')
                            cell.font = Font(name='Calibri', size=9, bold=True, color='FFFFFF')
                    
                    # Failure reason - left align and wrap
                    if col_idx == 9:  # Failure reason column (now column 9 instead of 11)
                        cell.alignment = Alignment(horizontal='left', vertical='center', wrap_text=True)
                
                row += 1
            
            row += 2  # Space between features
        
        # Adjust column widths
        ws.column_dimensions['A'].width = 14  # Date (wider for "17 Feb 2026" format)
        ws.column_dimensions['B'].width = 10  # Time
        ws.column_dimensions['C'].width = 20  # Scenario
        ws.column_dimensions['D'].width = 8   # Clients
        ws.column_dimensions['E'].width = 10  # Status
        ws.column_dimensions['F'].width = 14  # CPE CPU (Creation)
        ws.column_dimensions['G'].width = 14  # CPE CPU (Test)
        ws.column_dimensions['H'].width = 14  # Time Taken
        ws.column_dimensions['I'].width = 40  # Failure Reason
    
    def update_statistics(self, all_tests: List[Dict]):
        """
        Update the Excel statistics file with all test data
        
        Args:
            all_tests: List of all test documents from MongoDB
        """
        # Aggregate data by router
        aggregated_data = self._aggregate_router_data(all_tests)
        
        # Load or create workbook
        wb = load_workbook(self.excel_path)
        
        # Remove default sheet if it exists
        if 'Sheet' in wb.sheetnames:
            wb.remove(wb['Sheet'])
        
        # Create summary sheet
        self._create_summary_sheet(wb, aggregated_data)
        
        # Create detail sheets for each router
        for router_mac, router_data in aggregated_data.items():
            self._create_router_detail_sheet(wb, router_mac, router_data)
        
        # Save workbook
        wb.save(self.excel_path)
        
        # Set file permissions to be readable/writable by all
        try:
            os.chmod(self.excel_path, 0o666)
        except:
            pass  # Permission change might fail on some systems
        
        return self.excel_path