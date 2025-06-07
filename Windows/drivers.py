import subprocess
import pandas as pd
import json
import os
import time
from dateutil.parser import parse
import common.attributes as attr
import common.logger as logfunc

# format output
def format_row_with_keys(row):
    return " | ".join(f"{col}: {row[col]}" for col in row.index if pd.notna(row[col]))

def fetch_drivers(log_directory, ready_directory):
    logger = logfunc.setup_logging(log_directory, ready_directory, "DriverMonitor", "driver")

    # PowerShell command to get drivers and convert to JSON
    command = [
        "powershell",
        "-NoProfile",
        "-Command",
        "Get-CimInstance Win32_PnPSignedDriver | Select-Object * | ConvertTo-Json -Depth 3"
    ]
    result = subprocess.run(command, capture_output=True, text=True, encoding="utf-8")

    # JSON  to DataFrame
    try:
        driver_data = json.loads(result.stdout)
        dfd = pd.DataFrame(driver_data)
    except json.JSONDecodeError as e:
        print("JSON parse error:", e)
        print(result.stdout)
    # Fields to retain and optional renaming
    keep = [
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

    desired_order = [
        "timestamp",
        "name",
        "hostname",
        "username",
        "description"
    ]
    dfd = dfd[[col for col in desired_order if col in dfd.columns]]
    dfd['timestamp'] = dfd['timestamp'].apply(lambda x: parse(x) if x else '')
    dfd["event"] = "driver"
    dfd["sid"] = attr.get_computer_sid()
    lines = dfd.apply(format_row_with_keys, axis=1)
    for line in lines:
        logger.info(line)
    logfunc.clear_handlers(log_directory, ready_directory, logger)

def run():
    #interval = attr.get_config_value('Windows', 'driverInterval', 43200.0, 'float')
    interval = 60
    log_directory = 'tmp-windows-drivers'
    ready_directory = 'ready'
    debug_generator_directory = 'debuggeneratorlogs'
    os.makedirs(debug_generator_directory, exist_ok=True)
    os.makedirs(log_directory, exist_ok=True)
    os.makedirs(ready_directory, exist_ok=True)
    print('driverlog running')
    while True:
        fetch_drivers(log_directory, ready_directory)
        time.sleep(interval)  # Twice a day by default, can be increased or decreased

run()