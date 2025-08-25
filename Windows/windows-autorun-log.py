import os
import time
import winreg
import pandas as pd
from datetime import datetime
import common.attributes as attr
from common.logger import LoggingModule

hostname: str = attr.get_hostname()
computer_sid: str = attr.get_computer_sid() or ''
ec2_instance_id: str = attr.get_ec2_instance_id() or ''
timestamp: str = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

def format_row_with_keys(row):
    return " | ".join(f"{col}: {row[col]}" for col in row.index if pd.notna(row[col]))

def enum_run_keys(hive, path) -> list:
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

def enum_startup_folder_entries() -> list:
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

def fetch_autorun_events() -> pd.DataFrame:
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

    df["timestamp"] = timestamp
    df["hostname"] = hostname
    df["sid"] = computer_sid
    df["ec2_instance_id"] = ec2_instance_id
    df["event"] = "existing autorun"

    final_order: list[str] = [
        "timestamp", "hostname", 'event',
        "source", "entry", "path", "sid", "ec2_instance_id"
    ]
    df = df[[col for col in final_order if col in df.columns]]
    return df

def log_autoruns(logger: LoggingModule) -> None:
    interval = attr.get_config_value('Windows', 'AutorunInterval', 60.0, 'float')
    prev_df: pd.DataFrame = fetch_autorun_events()
    lines = prev_df.apply(format_row_with_keys, axis=1)
    for line in lines:
        logger.write_log(line)

    while True:
        logger.check_logging_interval()
        cur_df: pd.DataFrame = fetch_autorun_events()
        df_new: pd.DataFrame = pd.concat([cur_df, prev_df, prev_df]).drop_duplicates(keep=False)
        df_new["event"] = "new autorun found"
        df_new["timestamp"] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        lines = df_new.apply(format_row_with_keys, axis=1)
        for line in lines:
            logger.write_log(line)

        prev_df = cur_df
        logger.write_debug_log(f'timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} | '
                            f'hostname: {hostname} | source: autorun | platform: windows | event: progress | '
                            f'message: {logger.log_line_count} log lines written | value: {logger.log_line_count}')
        time.sleep(interval)

def run():
    log_directory = 'tmp-windows-autoruns' if attr.get_config_value('General', 'RunDatabaseOperations', False, 'bool') else 'tmp'
    ready_directory = 'ready'
    debug_generator_directory = 'debuggeneratorlogs'
    os.makedirs(debug_generator_directory, exist_ok=True)
    os.makedirs(log_directory, exist_ok=True)
    os.makedirs(ready_directory, exist_ok=True)
    print('autorunslog running')
    logger: LoggingModule  = LoggingModule(log_directory, ready_directory, "AutorunsMonitor", "autoruns")
    log_autoruns(logger)

run()