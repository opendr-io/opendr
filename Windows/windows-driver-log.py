import subprocess
import pandas as pd
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

hostname: str = attr.get_hostname()
computer_sid: str = attr.get_computer_sid() or ''
ec2_instance_id: str = attr.get_ec2_instance_id() or ''

# format output
def format_row_with_keys(row) -> str:
    return " | ".join(f"{col}: {row[col]}" for col in row.index if pd.notna(row[col]))

def fetch_defender_events() -> pd.DataFrame:
    # PowerShell command to get drivers and convert to JSON
    command: list[str] = [
        "powershell",
        "-NoProfile",
        "-Command",
        "Get-CimInstance Win32_PnPSignedDriver | Select-Object * | ConvertTo-Json -Depth 3"
    ]
    result = subprocess.run(command, capture_output=True, text=True, encoding="utf-8")

    # JSON  to DataFrame
    try:
        driver_data = json.loads(result.stdout)
        dfd: pd.DataFrame = pd.DataFrame(driver_data)
    except json.JSONDecodeError as e:
        print("JSON parse error:", e)
        print(result.stdout)
        return pd.DataFrame()
    # Fields to retain and optional renaming
    keep: list[str] = [
        'Description','ClassGuid','CompatID','DeviceClass','DeviceID','DeviceName',
        'DriverDate','DriverName','DriverProviderName','DriverVersion','FriendlyName',
        'HardWareID','InfName','IsSigned','Location','Manufacturer','PDO','Signer'
    ]
    dfd = dfd[[col for col in keep if col in dfd.columns]]
    dfd = dfd.rename(columns={
        'Description': 'desc',
        'ClassGuid': 'class_guid',
        'CompatID': 'compat_id',
        'DeviceClass': 'device_class',
        'DeviceID': 'device_id',
        'DeviceName': 'device_name',
        'DriverDate': 'driver_date',
        'DriverName': 'driver_name',
        'DriverProviderName': 'driver_provider',
        'DriverVersion': 'driver_version',
        'FriendlyName': 'friendly_name',
        'HardWareID': 'hardware_id',
        'InfName': 'inf_name',
        'IsSigned': 'is_signed',
        'Location': 'location',
        'Manufacturer': 'manufacturer',
        'PDO': 'pdo',
        'Signer': 'signer'
    })

    dfd["event"] = "existing driver"
    dfd["sid"] = computer_sid
    dfd["timestamp"] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    dfd["hostname"] = hostname
    dfd["ec2_instance_id"] = ec2_instance_id

    final_order: list[str] = [
        "timestamp", "hostname", "event",
        "name", "desc", "signer","class_guid", "compat_id", "device_class", "device_id",  "device_name",
        "driver_provider", "driver_version", "friendly_name", "hardware_id", "inf_name",
        "is_signed", "location", "manufacturer", "pdo",
        "sid", "ec2_instance_id",
    ]
    dfd = dfd[[col for col in final_order if col in dfd.columns]]
    return dfd

def log_drivers(logger: LoggingModule) -> NoReturn:
    interval: float = attr.get_config_value('Windows', 'DriverInterval', 60.0, 'float')
    logger.check_logging_interval()
    prev_dfd: pd.DataFrame = fetch_defender_events()
    lines = prev_dfd.apply(format_row_with_keys, axis=1)
    for line in lines:
        logger.write_log(line)
    while True:
        logger.check_logging_interval()
        cur_dfd: pd.DataFrame = fetch_defender_events()
        df_new: pd.DataFrame = pd.concat([cur_dfd, prev_dfd, prev_dfd]).drop_duplicates(keep=False)
        df_new["event"] = "new driver found"
        lines = df_new.apply(format_row_with_keys, axis=1)
        for line in lines:
            logger.write_log(line)
        prev_dfd = cur_dfd
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