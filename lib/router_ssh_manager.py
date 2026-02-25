import asyncio
from datetime import datetime
import re
import paramiko
import time
from utils.logger import logger  # Assuming this logger is configured properly
import os

class RouterSSHManager:
    def __init__(self, host, username, password, timeout=10):
        self.host = host
        self.username = username
        self.password = password
        self.timeout = timeout
        self.ssh = None
        self.shell = None

    def connect(self):
        if self.ssh:
            return
        self.ssh = paramiko.SSHClient()
        self.ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        self.ssh.connect(
            self.host,
            username=self.username,
            password=self.password,
            timeout=self.timeout,
        )

        logger.info(f"Connected to router {self.host} via SSH")

        self.shell = self.ssh.invoke_shell()
        self.shell.settimeout(2)
        time.sleep(0.5)

    def disconnect(self):
        if self.shell:
            self.shell.close()
            self.shell = None
        if self.ssh:
            self.ssh.close()
            logger.info("Disconnected from router SSH")
            self.ssh = None

    def run_in_shell(self, command):
        if not self.shell:
            self.connect()
        try:
            self.shell.send(command + "\n")
            time.sleep(0.5)
            output = self.shell.recv(65535).decode(errors="ignore")
            return output.strip()
        except Exception as e:
            logger.error(f"Shell command failed: {e}")
            return ""

    def get_health(self):
        """
        Get router CPU usage using mpstat
        
        Returns:
            Formatted string with CPU metrics
        """
        # Run mpstat once with 1 second interval
        raw = self.run_in_shell("mpstat 1 1")
        lines = raw.splitlines()
        
        # Find the line with "all" CPU stats
        cpu_line = None
        for line in lines:
            if 'all' in line and not line.startswith('Linux'):
                cpu_line = line.strip()
                break
        
        if not cpu_line:
            logger.warning("Could not parse mpstat output")
            return "[ROUTER ] CPU: N/A\n"
        
        # Parse mpstat output
        # Format: 07:02:21  all  %usr  %nice  %sys  %iowait  %irq  %soft  %steal  %guest  %idle
        # Example: 07:02:21  all  2.66  0.00   2.34  0.00     0.17  0.67   0.00    0.00    94.15
        
        parts = cpu_line.split()
        
        try:
            # mpstat columns (after timestamp and "all"):
            # 0: timestamp, 1: "all", 2: %usr, 3: %nice, 4: %sys, 5: %iowait, 
            # 6: %irq, 7: %soft, 8: %steal, 9: %guest, 10: %idle
            
            usr = float(parts[2])
            sys = float(parts[4])
            irq = float(parts[6])
            soft = float(parts[7])
            idle = float(parts[10])
            
            # Format similar to top output for consistency
            formatted = (f"[ROUTER ] CPU: {usr:4.0f}% usr {sys:4.0f}% sys "
                        f"{irq:4.0f}% irq {soft:4.0f}% sirq {idle:4.0f}% idle\n")
            
            logger.info(formatted)
            return formatted
            
        except (IndexError, ValueError) as e:
            logger.error(f"Error parsing mpstat output: {e}")
            logger.error(f"Raw line: {cpu_line}")
            return "[ROUTER ] CPU: Parse Error\n"


    @staticmethod
    def extract_router_info(data):

        lines = data.split('\n') if isinstance(data, str) else data
        
        router_info = {
            'router_mac': 'Not Found',
            'router_firmware': 'Not Found',
            'router_name': 'Not Found',
            'router_model': 'Not Found'
        }
        
        for line in lines:
            if 'id' in line and '|' in line:
                match = re.search(r'id\s*\|\s*([a-fA-F0-9]{12})', line)
                if match:
                    router_info['router_mac'] = match.group(1)
            elif 'firmware_version' in line:  # Look for 'firmware_version'
                match = re.search(r'firmware_version\s*\|\s*([^\s|]+)', line)
                if match:
                    router_info['router_firmware'] = match.group(1).strip()
            elif 'vendor_name' in line:  # Look for 'vendor_name'
                match = re.search(r'vendor_name\s*\|\s*([^\s|]+)', line)
                if match:
                    router_info['router_name'] = match.group(1).strip()
            elif 'model' in line:  # Look for 'model'
                match = re.search(r'model\s*\|\s*([^\s|]+)', line)
                if match:
                    router_info['router_model'] = match.group(1).strip()
        
        return router_info

    def get_router_info(self):
        raw = self.run_in_shell("ovsh s AWLAN_Node")
        
        if raw:
            data = RouterSSHManager.extract_router_info(raw)
            return data
        else:
            logger.error("Failed to retrieve router info")
            return {}

