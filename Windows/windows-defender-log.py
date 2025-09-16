import subprocess
import re
import os
import time
from dateutil.parser import parse
from datetime import datetime
from common.logger import LoggingModule
import common.attributes as attr
from typing import NoReturn

hostname: str = attr.get_hostname()
computer_sid: str = attr.get_computer_sid() or ''

def fetch_defender_events() -> list[dict]:
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
        record["sid"] = computer_sid

    records = [{val: record[key] for key, val in column_names.items()} for record in records]

    return records

def log_existing_data(logger: LoggingModule) -> set:
    prev_records: set = set()
    record_data: list[dict] = fetch_defender_events()
    for record in record_data:
        if (record.get('timestamp', ''), record.get('event_id', ''), record.get('title', '')) in prev_records:
            continue
        prev_records.add((record.get('timestamp', ''), record.get('event_id', ''), record.get('title', '')))
        logger.write_log(" | ".join([f"{key}: {record[key]}" for key in record]))
    return prev_records

def log_defender_events(logger: LoggingModule) -> NoReturn:
    interval = attr.get_config_value('Windows', 'DefenderInterval', 60.0, 'float')
    prev_records: set = log_existing_data(logger)

    while True:
        logger.check_logging_interval()
        record_data: list[dict] = fetch_defender_events()
        for record in record_data:
            if (record.get('timestamp', ''), record.get('event_id', ''), record.get('title', '')) in prev_records:
                continue
            record["event"] = "new defender event"
            logger.write_log(" | ".join([f"{key}: {record[key]}" for key in record]))
            prev_records.add((record.get('timestamp', ''), record.get('event_id', ''), record.get('title', '')))

        logger.write_debug_log(f"timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} | "
                        f"hostname: {hostname} | source: defender | platform: windows | event: progress | "
                        f"message: {logger.log_line_count} log lines written | value: {logger.log_line_count}")
        time.sleep(interval)

def run():
    log_directory = 'tmp-windows-defender' if attr.get_config_value('General', 'RunDatabaseOperations', False, 'bool') else 'tmp'
    ready_directory = 'ready'
    debug_generator_directory = 'debuggeneratorlogs'
    os.makedirs(debug_generator_directory, exist_ok=True)
    os.makedirs(log_directory, exist_ok=True)
    os.makedirs(ready_directory, exist_ok=True)
    print('windowsdefenderlog running')
    logger: LoggingModule  = LoggingModule(log_directory, ready_directory, "DefenderMonitor", "defender")
    log_defender_events(logger)

run()
