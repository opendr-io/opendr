import subprocess
import pandas as pd
import re
import os
import time
import common.attributes as attr
from datetime import datetime
from common.logger import LoggingModule

prev_records = {}

# output formatted lines
def format_row_with_keys(row):
    return " | ".join(f"{col}: {row[col]}" for col in row.index if pd.notna(row[col]))

def fetch_defender_events(logger: LoggingModule) -> None:
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

        key = (record.get('TimeCreated', ''), record.get('Id', ''), record.get('Name', ''))
        if key not in prev_records:
            records.append(record)
            prev_records[key] = record

    if not records:
        return

    logger.check_logging_interval()
    dfwdf = pd.DataFrame(records)
    dfwdf = dfwdf.rename(columns={
        "TimeCreated": "timestamp",
        "Id": "event_id",
        "Message": "message"
    })

    dfwdf["timestamp"] = pd.to_datetime(dfwdf["timestamp"], errors="coerce", dayfirst=True)
    # Drop rows where all fields except 'timestamp' are NaN
    dfwdf = dfwdf[~dfwdf.drop(columns=['timestamp']).isna().all(axis=1)]
    dfwdf = dfwdf.where(pd.notnull(dfwdf), None)
    dfwdf = dfwdf.drop_duplicates()

    if "Process Name" in dfwdf.columns:
        idx = dfwdf.columns.get_loc("Process Name")
        # Keep only columns up to and including "Process Name"
        dfwdf = dfwdf.iloc[:, :idx + 1]
    dfwdf = dfwdf.drop_duplicates() # remove duplicates

    dfwdf = dfwdf.rename(columns={
        "timestamp": "timestamp",
        "message": "description",
        "For more information please see the following": "references",
        "Name": "title",
        "ID": "threat_id",
        "Severity": "severity",
        "Category": "category",
        "Path": "file_path",
        "Detection Origin": "origin",
        "Detection Type": "type",
        "Detection Source": "source",
        "User": "username",
        "Process Name": "executable"
    })
    dfwdf["event"] = "Windows defender"
    desired_order = [
        "timestamp",
        "event",
        "username",
        "title",
        "severity",
        "category",
        "executable",
        "file_path",
        "event_id", 
        "threat_id",
        "origin",
        "type",
        "source",
        "description",
        "references"
    ]

    dfwdf = dfwdf[[col for col in desired_order if col in dfwdf.columns]]
    dfwdf["sid"] = attr.get_computer_sid()

    lines = dfwdf.apply(format_row_with_keys, axis=1)
    for line in lines:
        logger.write_log(line)

    logger.write_debug_log("timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} | "
                        f"hostname: {attr.get_hostname()} | source: defender | platform: windows | event: progress | "
                        f"message: {logger.log_line_count} log lines written | value: {logger.log_line_count}")
    logger.clear_handlers()

def run():
    interval = attr.get_config_value('Windows', 'DefenderInterval', 60.0, 'float')
    log_directory = 'tmp-windows-defender' if attr.get_config_value('General', 'RunDatabaseOperations', False, 'bool') else 'tmp'
    ready_directory = 'ready'
    debug_generator_directory = 'debuggeneratorlogs'
    os.makedirs(debug_generator_directory, exist_ok=True)
    os.makedirs(log_directory, exist_ok=True)
    os.makedirs(ready_directory, exist_ok=True)
    print('windowsdefenderlog running')
    logger: LoggingModule  = LoggingModule(log_directory, ready_directory, "DefenderMonitor", "defender")
    while True:
        fetch_defender_events(logger)
        time.sleep(interval)  # Twice a day by default, can be increased or decreased

run()
