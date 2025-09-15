import subprocess
import json
import os
import time
from datetime import datetime
import common.attributes as attr
from common.logger import LoggingModule
from typing import NoReturn

# Enumerates Windows Plug and Play drivers
# Not all Windows drivers will be output here, but 
# most hardware device activations on a Windows PC
# should be detected by this component.

timestamp: str = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
hostname: str = attr.get_hostname()
computer_sid: str = attr.get_computer_sid() or ''
ec2_instance_id: str = attr.get_ec2_instance_id() or ''

def fetch_defender_events() -> list[dict]:
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
        driver["sid"] = computer_sid
        driver["timestamp"] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        driver["hostname"] = hostname
        driver["ec2_instance_id"] = ec2_instance_id

    column_names: dict = {
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

def log_existing_data(logger: LoggingModule) -> set:
    prev_drivers: set = set()
    driver_data: list[dict] = fetch_defender_events()
    for data in driver_data:
        prev_drivers.add((data['driver_version'], data['device_id'], data['pdo']))
        logger.write_log(" | ".join([f"{key}: {data[key]}" for key in data]))
    return prev_drivers

def log_drivers(logger: LoggingModule) -> NoReturn:
    interval: float = attr.get_config_value('Windows', 'DriverInterval', 60.0, 'float')
    prev_drivers: set = log_existing_data(logger)

    while True:
        logger.check_logging_interval()
        driver_data: list[dict] = fetch_defender_events()
        for data in driver_data:
            if (data['driver_version'], data['device_id'], data['pdo']) in prev_drivers:
                continue
            data["event"] = "new driver found"
            prev_drivers.add((data['driver_version'], data['device_id'], data['pdo']))
            logger.write_log(" | ".join([f"{key}: {data[key]}" for key in data]))

        logger.write_debug_log(f"timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} | "
                            f"hostname: {hostname} | source: defender | platform: windows | event: progress | "
                            f"message: {logger.log_line_count} log lines written | value: {logger.log_line_count}")
        time.sleep(interval)

def run() -> NoReturn:
    log_directory = 'tmp-windows-drivers' if attr.get_config_value('General', 'RunDatabaseOperations', False, 'bool') else 'tmp'
    ready_directory = 'ready'
    debug_generator_directory = 'debuggeneratorlogs'
    os.makedirs(debug_generator_directory, exist_ok=True)
    os.makedirs(log_directory, exist_ok=True)
    os.makedirs(ready_directory, exist_ok=True)
    print('driverlog running')
    logger: LoggingModule  = LoggingModule(log_directory, ready_directory, "DriverMonitor", "driver")
    log_drivers(logger)

run()