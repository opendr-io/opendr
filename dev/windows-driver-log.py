import subprocess
import json
import os
import time
from datetime import datetime
import common.attributes as attr
from common.logger import LoggingModule

class WindowsDriverLogger():
    def __init__(self):
        self.sid: str = attr.get_computer_sid()
        self.hostname: str = attr.get_hostname()
        self.ec2_instance_id: str = attr.get_ec2_instance_id() or ''
        self.interval: float = attr.get_config_value('Windows', 'DriverInterval', 60.0, 'float')
        self.logger = None
        self.prev_drivers: set = set()
        self.setup_logger()
        self.log_existing()
        print('WindowsDriverLogger Initialization complete')

    def setup_logger(self) -> None:
        log_directory: str = 'tmp-windows-drivers' if attr.get_config_value('General', 'RunDatabaseOperations', False, 'bool') else 'tmp'
        ready_directory: str = 'ready'
        debug_generator_directory: str = 'debuggeneratorlogs'
        os.makedirs(debug_generator_directory, exist_ok=True)
        os.makedirs(log_directory, exist_ok=True)
        os.makedirs(ready_directory, exist_ok=True)
        self.logger: LoggingModule = LoggingModule(log_directory, ready_directory, "DriverMonitor", "driver")

    def fetch_defender_events(self) -> list[dict]:
        # PowerShell command to get drivers and convert to JSON
        command: list[str] = [
            "powershell",
            "-NoProfile",
            "-Command",
            "Get-CimInstance Win32_PnPSignedDriver | Select-Object 'Description','Signer','DeviceID','DriverVersion','FriendlyName','IsSigned','PDO' | ConvertTo-Json -Depth 2"
        ]
        result = subprocess.run(command, capture_output=True, text=True, encoding="utf-8")

        try:
            driver_data = json.loads(result.stdout)
        except json.JSONDecodeError as e:
            print("JSON parse error:", e)
            print(result.stdout)
            return []

        for driver in driver_data:
            driver["event"] = "existing driver"
            driver["sid"] = self.sid
            driver["timestamp"] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            driver["hostname"] = self.hostname
            driver["ec2_instance_id"] = self.ec2_instance_id

        column_names = {
            'timestamp': 'timestamp',
            'hostname': 'hostname',
            'event': 'event',
            'Description': 'desc',
            'Signer': 'signer',
            'DeviceID': 'device_id',
            'DriverVersion': 'driver_version',
            'FriendlyName': 'friendly_name',
            'IsSigned': 'is_signed',
            'PDO': 'pdo',
            'ec2_instance_id': 'ec2_instance_id',
            'sid': 'sid'
        }
        driver_data = [{val: driver[key] for key, val in column_names.items()} for driver in driver_data]
        return driver_data

    def log_existing(self) -> None:
        driver_data: list[dict] = self.fetch_defender_events()
        for data in driver_data:
            self.prev_drivers.add((data['driver_version'], data['device_id'], data['pdo']))
            self.logger.write_log(" | ".join([f"{key}: {data[key]}" for key in data]))

    def monitor_events(self) -> None:
        self.logger.check_logging_interval()
        driver_data: list[dict] = self.fetch_defender_events()
        for data in driver_data:
            if (data['driver_version'], data['device_id'], data['pdo']) in self.prev_drivers:
                continue
            data["event"] = "new driver found"
            data["timestamp"] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            self.prev_drivers.add((data['driver_version'], data['device_id'], data['pdo']))
            self.logger.write_log(" | ".join([f"{key}: {data[key]}" for key in data]))

        self.logger.write_debug_log(f'timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} | '
                            f'hostname: {self.hostname} | source: defender | platform: windows | event: progress | '
                            f'message: {self.logger.log_line_count} log lines written | value: {self.logger.log_line_count}')

if __name__ == '__main__':
    driver = WindowsDriverLogger()
    while True:
        driver.monitor_events()
        time.sleep(driver.interval)
