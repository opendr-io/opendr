import subprocess
import json
import os
import time
from datetime import datetime
from dateutil.parser import parse
import common.attributes as attr
from common.logger import LoggingModule

class WindowsHotfixLogger(attr.LoggerParent):
    def __init__(self):
        super().__init__()
        self.interval: float = attr.get_config_value('Windows', 'HotfixInterval', 60.0, 'float')
        self.prev_hotfixes: set = set()
        self.setup_logger()
        self.log_existing()
        print('WindowsHotfixLogger Initialization complete')

    def setup_logger(self) -> None:
        log_directory: str = 'tmp-windows-autoruns' if attr.get_config_value('General', 'RunDatabaseOperations', False, 'bool') else 'tmp'
        ready_directory: str = 'ready'
        debug_generator_directory: str = 'debuggeneratorlogs'
        os.makedirs(debug_generator_directory, exist_ok=True)
        os.makedirs(log_directory, exist_ok=True)
        os.makedirs(ready_directory, exist_ok=True)
        self.logger: LoggingModule = LoggingModule(log_directory, ready_directory, "HotfixMonitor", "hotfix")

    def fetch_hotfix_events(self) -> list[dict]:
        # PowerShell command to get hotfixes and convert to JSON
        command = [
            "powershell",
            "-Command",
            "Get-HotFix | Select-Object HotFixID, Description, InstalledOn, InstalledBy, PSComputerName | ConvertTo-Json"
        ]
        result = subprocess.run(command, capture_output=True, text=True, encoding="utf-8")

        try:
            hotfix_data = json.loads(result.stdout)
            # If only one item is returned, make it a list
            if isinstance(hotfix_data, dict):
                hotfix_data = [hotfix_data]
        except json.JSONDecodeError as e:
            print("JSON parse error:", e)
            print(result.stdout)
            return []

        for hotfix in hotfix_data:
            hotfix['InstalledOn'] = hotfix['InstalledOn']['DateTime'] if isinstance(hotfix['InstalledOn'], dict) else hotfix['InstalledOn']
            hotfix['InstalledOn'] = parse(hotfix['InstalledOn']) if hotfix['InstalledOn'] else ''
            hotfix["event"] = "existing hotfix"
            hotfix["sid"] = self.sid

        column_names: dict = {
            "InstalledOn": "timestamp",
            "event": "event",
            "HotFixID": "name",
            "PSComputerName": "hostname",
            "InstalledBy": "username",
            "Description": "description",
            "sid": "sid"
        }

        hotfix_data = [{val: hotfix[key] for key, val in column_names.items()} for hotfix in hotfix_data]
        hotfix_data = sorted(hotfix_data, key=lambda x: x['timestamp'], reverse=True)    
        return hotfix_data

    def log_existing(self) -> None:
        hotfix_data: list[dict] = self.fetch_hotfix_events()
        for data in hotfix_data:
            self.prev_hotfixes.add((data['name'], data['description']))
            self.logger.write_log(" | ".join([f"{key}: {data[key]}" for key in data]))

    def monitor_events(self) -> None:
        self.logger.check_logging_interval()
        hotfix_data: list[dict] = self.fetch_hotfix_events()
        for data in hotfix_data:
            if (data['name'], data['description']) in self.prev_hotfixes:
                continue
            data["event"] = "new hotfix found"
            self.prev_hotfixes.add((data['name'], data['description']))
            self.logger.write_log(" | ".join([f"{key}: {data[key]}" for key in data]))

        self.logger.write_debug_log(f'timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} | '
                            f'hostname: {self.hostname} | source: hotfix | platform: windows | event: progress | '
                            f'message: {self.logger.log_line_count} log lines written | value: {self.logger.log_line_count}')

if __name__ == '__main__':
    hotfix = WindowsHotfixLogger()
    while True:
        hotfix.monitor_events()
        time.sleep(hotfix.interval)
