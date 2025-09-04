import subprocess
import re
import os
import time
from dateutil.parser import parse
from datetime import datetime
from common.logger import LoggingModule
import common.attributes as attr

class WindowsDefenderLogger():
    def __init__(self):
        self.sid: str = attr.get_computer_sid()
        self.hostname: str = attr.get_hostname()
        self.interval: float = attr.get_config_value('Windows', 'DefenderInterval', 60.0, 'float')
        self.logger = None
        self.prev_records: set = set()
        self.setup_logger()
        self.log_existing()
        print('WindowsDefenderLogger Initialization complete')

    def setup_logger(self) -> None:
        log_directory: str = 'tmp-windows-defender' if attr.get_config_value('General', 'RunDatabaseOperations', False, 'bool') else 'tmp'
        ready_directory: str = 'ready'
        debug_generator_directory: str = 'debuggeneratorlogs'
        os.makedirs(debug_generator_directory, exist_ok=True)
        os.makedirs(log_directory, exist_ok=True)
        os.makedirs(ready_directory, exist_ok=True)
        self.logger: LoggingModule = LoggingModule(log_directory, ready_directory, "DefenderMonitor", "defender")

    def fetch_defender_events(self) -> list[dict]:
        # PowerShell command to fetch Event ID 1116
        command = [
            "powershell.exe",
            "-NoProfile",
            "-ExecutionPolicy", "Bypass",
            "-Command",
            "Get-WinEvent -LogName 'Microsoft-Windows-Windows Defender/Operational' | Where-Object { $_.Id -eq 1116 } | Select-Object TimeCreated, Id, Message | Format-List * "
        ]

        result = subprocess.run(command, capture_output=True, text=True, encoding='utf-8')

        # split entries on 'TimeCreated :' but keep the delimiter
        entries = re.split(r'(?=TimeCreated\s+:)', result.stdout.strip())

        # read into a dictionary
        records = []
        for entry in entries:
            record = {}
            lines = entry.strip().splitlines()
            for line in lines:
                line = line.strip()
                if not line:
                    continue
                # Split on first colon
                if re.match(r'^https?://', line):
                    # Put the URL in the correct field
                    record["For more information please see the following"] = line.strip()
                elif ':' in line:
                    key, value = line.split(':', 1)
                    record[key.strip()] = value.strip()
                else:
                    # Continuation of previous key's value
                    if record:
                        last_key = list(record.keys())[-1]
                        record[last_key] += ' ' + line.strip()

            if record:
                records.append(record)

        if not records:
            return []
        
        column_names: dict = {
            "TimeCreated": "timestamp",
            "event": "event",
            "User": "username",
            "Name": "title",
            "Severity": "severity",
            "Category": "category",
            "Process Name": "executable",
            "Path": "file_path",
            "Id": "event_id",
            "ID": "threat_id",
            "Detection Origin": "origin",
            "Detection Type": "type",
            "Detection Source": "source",
            "Message": "description",
            "For more information please see the following": "references",
            "sid": "sid"
        }
        
        for record in records:
            record['TimeCreated'] = parse(record['TimeCreated']) if record['TimeCreated'] else ''
            record["event"] = "existing defender event"
            record["sid"] = self.sid

        records = [{val: record[key] for key, val in column_names.items()} for record in records]

        return records

    def log_existing(self) -> None:
        record_data: list[dict] = self.fetch_defender_events()
        for record in record_data:
            if (record.get('timestamp', ''), record.get('event_id', ''), record.get('title', '')) in self.prev_records:
                continue
            self.prev_records.add((record.get('timestamp', ''), record.get('event_id', ''), record.get('title', '')))
            self.logger.write_log(" | ".join([f"{key}: {record[key]}" for key in record]))

    def monitor_events(self) -> None:
        self.logger.check_logging_interval()
        record_data: list[dict] = self.fetch_defender_events()
        for record in record_data:
            if (record.get('timestamp', ''), record.get('event_id', ''), record.get('title', '')) in self.prev_records:
                continue
            record["event"] = "new defender event"
            self.logger.write_log(" | ".join([f"{key}: {record[key]}" for key in record]))
            self.prev_records.add((record.get('timestamp', ''), record.get('event_id', ''), record.get('title', '')))

        self.logger.write_debug_log(f'timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} | '
                        f'hostname: {self.hostname} | source: defender | platform: windows | event: progress | '
                        f'message: {self.logger.log_line_count} log lines written | value: {self.logger.log_line_count}')

if __name__ == '__main__':
    defender = WindowsDefenderLogger()
    while True:
        defender.monitor_events()
        time.sleep(defender.interval)
