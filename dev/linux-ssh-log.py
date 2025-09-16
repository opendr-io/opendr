import os
import time
import subprocess
from datetime import datetime
import common.attributes as attr
from common.logger import LoggingModule

class LinuxSshLogger(attr.LoggerParent):
    def __init__(self):
        super().__init__()
        self.interval: float = attr.get_config_value('Linux', 'SSHLogInterval', 60.0, 'float')
        self.previous_keys: set = set()
        self.setup_logger()
        self.log_existing()
        print('LinuxSshLogger Initialization complete')

    def setup_logger(self) -> None:
        log_directory: str = 'tmp-ssh-key' if attr.get_config_value('General', 'RunDatabaseOperations', False, 'bool') else 'tmp'
        ready_directory: str = 'ready'
        debug_generator_directory: str = 'debuggeneratorlogs'
        os.makedirs(debug_generator_directory, exist_ok=True)
        os.makedirs(log_directory, exist_ok=True)
        os.makedirs(ready_directory, exist_ok=True)
        self.logger: LoggingModule  = LoggingModule(log_directory, ready_directory, "SSHKeyMonitor", "sshkey")

    @staticmethod
    def get_ssh_keys() -> list:
        keys: list = []
        try:
            result = subprocess.run(['find / -type f \\( -name "id_rsa" -o -name "*.pem" -o -name "*.key" \\) -exec grep -l "PRIVATE KEY" {} \\; 2>/dev/null'], shell=True, capture_output=True, text=True)
            if result.returncode != -1:
                for line in result.stdout.strip().splitlines():
                    line = line.strip()
                    keys.append(line)
        except Exception as e:
            print(e)
            return []
        return keys

    def log_existing(self) -> None:
        timestamp: str = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        for key in self.get_ssh_keys():
            entry: str = f"timestamp: {timestamp} | hostname: {self.hostname} | source: user_sshkey | filepath: {key}"
            self.logger.write_log(entry)
            self.previous_keys.add(key)
    
    def monitor_events(self) -> None:
        timestamp: str = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        for key in self.get_ssh_keys():
            if key in self.previous_keys:
                continue
            entry: str = f"timestamp: {timestamp} | hostname: {self.hostname} | source: user_sshkey | filepath: {key}"
            self.logger.write_log(entry)
            self.previous_keys.add(key)
        self.logger.write_debug_log(f'timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} | '
                        f'hostname: {self.hostname} | source: ssh | platform: linux | event: progress | '
                        f'message: {self.logger.log_line_count} log lines written | value: {self.logger.log_line_count}')

if __name__ == '__main__':
    ssh = LinuxSshLogger()
    while True:
        ssh.monitor_events()
        time.sleep(ssh.interval)