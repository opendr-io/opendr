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

def fetch_hotfixes(log_directory, ready_directory):
    logger = logfunc.setup_logging(log_directory, ready_directory, "HotfixMonitor", "hotfix")

    # PowerShell command to get hotfixes and convert to JSON
    command = [
        "powershell",
        "-Command",
        "Get-HotFix | Select-Object HotFixID, Description, InstalledOn, InstalledBy, PSComputerName | ConvertTo-Json"
    ]
    result = subprocess.run(command, capture_output=True, text=True, encoding="utf-8")

    # JSON  to DataFrame
    try:
        hotfix_data = json.loads(result.stdout)
        # If only one item is returned, make it a list
        if isinstance(hotfix_data, dict):
            hotfix_data = [hotfix_data]

        dfh = pd.DataFrame(hotfix_data)
    except json.JSONDecodeError as e:
        print("JSON parse error:", e)
        print(result.stdout)

    # If InstalledOn is a dictionary, extract the 'DateTime' field
    dfh['InstalledOn'] = dfh['InstalledOn'].apply(lambda x: x.get('DateTime') if isinstance(x, dict) else x)
    dfh = dfh.sort_values(by='InstalledOn', ascending=False)

    dfh = dfh.rename(columns={
        "InstalledOn": "timestamp",
        "HotFixID": "name",
        "PSComputerName": "hostname",
        "InstalledBy": "username",
        "Description": "description"
    })

    desired_order = [
        "timestamp",
        "name",
        "hostname",
        "username",
        "description"
    ]
    dfh = dfh[[col for col in desired_order if col in dfh.columns]]
    dfh['timestamp'] = dfh['timestamp'].apply(lambda x: parse(x) if x else '')
    dfh["event"] = "hotfix"
    dfh["sid"] = attr.get_computer_sid()
    lines = dfh.apply(format_row_with_keys, axis=1)
    for line in lines:
        logger.info(line)
    logfunc.clear_handlers(log_directory, ready_directory, logger)

def run():
    interval = attr.get_config_value('Windows', 'HotfixInterval', 43200.0, 'float')
    log_directory = 'tmp-windows-hotfixes' if attr.get_config_value('Windows', 'RunDatabaseOperations', False, 'bool') else 'tmp'
    ready_directory = 'ready'
    debug_generator_directory = 'debuggeneratorlogs'
    os.makedirs(debug_generator_directory, exist_ok=True)
    os.makedirs(log_directory, exist_ok=True)
    os.makedirs(ready_directory, exist_ok=True)
    print('hotfixlog running')
    while True:
        fetch_hotfixes(log_directory, ready_directory)
        time.sleep(interval)  # Twice a day by default, can be increased or decreased

run()