import re
import paramiko
import time
from utils.logger import logger  # Assuming this logger is configured properly

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
        raw = self.run_in_shell("top -bn1 | grep 'CPU:'")
        lines = raw.splitlines()

        cpu_line = "?"
        for line in lines:
            if line.startswith("CPU:"):
                cpu_line = line.strip()
                break

        formatted = f"[ROUTER ] {cpu_line}" + "\n"
        logger.info(formatted)
        return formatted


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

