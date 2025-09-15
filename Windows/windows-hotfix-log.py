import subprocess
import json
import os
import time
from datetime import datetime
from dateutil.parser import parse
import common.attributes as attr
from common.logger import LoggingModule

hostname: str = attr.get_hostname()
computer_sid: str = attr.get_computer_sid() or ''

def fetch_hotfix_events() -> list[dict]:
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
        hotfix["sid"] = computer_sid

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

def log_existing_data(logger: LoggingModule) -> set:
    prev_hotfixes: set = set()
    hotfix_data: list[dict] = fetch_hotfix_events()
    for data in hotfix_data:
        prev_hotfixes.add((data['name'], data['description']))
        logger.write_log(" | ".join([f"{key}: {data[key]}" for key in data]))
    return prev_hotfixes

def fetch_hotfixes(logger: LoggingModule):
    interval = attr.get_config_value('Windows', 'HotfixInterval', 60.0, 'float')
    prev_hotfixes: set = log_existing_data(logger)

    while True:
        logger.check_logging_interval()
        hotfix_data: list[dict] = fetch_hotfix_events()
        for data in hotfix_data:
            if (data['name'], data['description']) in prev_hotfixes:
                continue
            data["event"] = "new hotfix found"
            prev_hotfixes.add((data['name'], data['description']))
            logger.write_log(" | ".join([f"{key}: {data[key]}" for key in data]))

        logger.write_debug_log(f"timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} | "
                            f"hostname: {hostname} | source: hotfix | platform: windows | event: progress | "
                            f"message: {logger.log_line_count} log lines written | value: {logger.log_line_count}")
        time.sleep(interval)

def run():
    log_directory = 'tmp-windows-hotfixes' if attr.get_config_value('General', 'RunDatabaseOperations', False, 'bool') else 'tmp'
    ready_directory = 'ready'
    debug_generator_directory = 'debuggeneratorlogs'
    os.makedirs(debug_generator_directory, exist_ok=True)
    os.makedirs(log_directory, exist_ok=True)
    os.makedirs(ready_directory, exist_ok=True)
    print('hotfixlog running')
    logger: LoggingModule = LoggingModule(log_directory, ready_directory, "HotfixMonitor", "hotfix")
    fetch_hotfixes(logger)

run()