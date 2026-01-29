import paramiko
import time
from utils.logger import logger


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
