import os
import time
import winreg
import pandas as pd
from datetime import datetime
import common.attributes as attr
import common.logger as logfunc

def format_row_with_keys(row):
    return " | ".join(f"{col}: {row[col]}" for col in row.index if pd.notna(row[col]))

def enum_run_keys(hive, path):
    """Enumerates entries under a Run/RunOnce registry key."""
    entries = []
    try:
        key = winreg.OpenKey(hive, path)
        for i in range(winreg.QueryInfoKey(key)[1]):
            name, value, _ = winreg.EnumValue(key, i)
            entries.append({
                "source": f"{hive_name(hive)}\\{path}",
                "entry": name,
                "path": value
            })
        winreg.CloseKey(key)
    except FileNotFoundError:
        pass
    return entries

def hive_name(hive):
    return {
        winreg.HKEY_LOCAL_MACHINE: "HKLM",
        winreg.HKEY_CURRENT_USER: "HKCU"
    }.get(hive, str(hive))

def enum_startup_folder_entries():
    """Lists .lnk files from common Startup folders."""
    startup_dirs = [
        os.path.expandvars(r"%APPDATA%\Microsoft\Windows\Start Menu\Programs\Startup"),
        os.path.expandvars(r"%ProgramData%\Microsoft\Windows\Start Menu\Programs\Startup")
    ]
    entries = []
    for folder in startup_dirs:
        if os.path.exists(folder):
            for item in os.listdir(folder):
                if item.endswith(".lnk"):
                    entries.append({
                        "source": folder,
                        "entry": item,
                        "path": os.path.join(folder, item)
                    })
    return entries

def fetch_autoruns(log_directory, ready_directory):
    logger = logfunc.setup_logging(log_directory, ready_directory, "AutorunsMonitor", "autoruns")

    # Gather autorun entries
    entries = []

    # Run keys (HKLM + HKCU)
    reg_paths = [
        (winreg.HKEY_LOCAL_MACHINE, r"Software\Microsoft\Windows\CurrentVersion\Run"),
        (winreg.HKEY_LOCAL_MACHINE, r"Software\Microsoft\Windows\CurrentVersion\RunOnce"),
        (winreg.HKEY_CURRENT_USER, r"Software\Microsoft\Windows\CurrentVersion\Run"),
        (winreg.HKEY_CURRENT_USER, r"Software\Microsoft\Windows\CurrentVersion\RunOnce")
    ]
    for hive, path in reg_paths:
        entries.extend(enum_run_keys(hive, path))

    # Startup folder .lnk files
    entries.extend(enum_startup_folder_entries())

    # Convert to DataFrame
    df = pd.DataFrame(entries)

    if df.empty:
        return

    # Add metadata
    df["timestamp"] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    df["hostname"] = attr.get_hostname()
    df["sid"] = attr.get_computer_sid() or ''
    df["ec2_instance_id"] = attr.get_ec2_instance_id() or ''
    df["event"] = "autorun"
    # Column order
    final_order = [
        "timestamp", "hostname", 'event',
        "source", "entry", "path", "sid", "ec2_instance_id"
    ]
    df = df[[col for col in final_order if col in df.columns]]

    for line in df.apply(format_row_with_keys, axis=1):
        logger.info(line)

    logfunc.clear_handlers(log_directory, ready_directory, logger)

def run():
    interval = attr.get_config_value('Windows', 'AutorunInterval', 43200.0, 'float')
    log_directory = 'tmp-windows-autoruns' if attr.get_config_value('Windows', 'RunDatabaseOperations', False, 'bool') else 'tmp'
    ready_directory = 'ready'
    debug_generator_directory = 'debuggeneratorlogs'
    os.makedirs(debug_generator_directory, exist_ok=True)
    os.makedirs(log_directory, exist_ok=True)
    os.makedirs(ready_directory, exist_ok=True)
    print('autorunslog running')
    while True:
        fetch_autoruns(log_directory, ready_directory)
        time.sleep(interval)

run()