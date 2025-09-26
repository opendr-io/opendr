import os
import time
import subprocess
from datetime import datetime
import common.attributes as attr
from common.logger import LoggingModule

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

def log_ssh_keys(log_directory: str, ready_directory: str) -> None:
    logger = LoggingModule(log_directory, ready_directory, "SSHKeyMonitor", "sshkey")
    hostname: str = attr.get_hostname()
    timestamp: str = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

    for key in get_ssh_keys():
        entry: str = f"timestamp: {timestamp} | hostname: {hostname} | source: user_sshkey | filepath: {key}"
        logger.write_log(entry)
    
    logger.write_debug_log(f'timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} | '
                        f'hostname: {hostname} | source: ssh | platform: linux | event: progress | '
                        f'message: {logger.log_line_count} log lines written | value: {logger.log_line_count}')
    logger.clear_handlers()

def run():
    interval: float = attr.get_config_value('Linux', 'SSHLogInterval', 43200.0, 'float')
    log_directory: str = 'tmp-ssh-key' if attr.get_config_value('General', 'RunDatabaseOperations', False, 'bool') else 'tmp'
    ready_directory: str = 'ready'
    debug_generator_directory: str = 'debuggeneratorlogs'
    os.makedirs(debug_generator_directory, exist_ok=True)
    os.makedirs(log_directory, exist_ok=True)
    os.makedirs(ready_directory, exist_ok=True)
    print("sshkey running")
    while True:
        log_ssh_keys(log_directory, ready_directory)
        time.sleep(interval)

if __name__ == "__main__":
    run()