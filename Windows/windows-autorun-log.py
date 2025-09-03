import os
import time
import winreg
from datetime import datetime
import common.attributes as attr
from common.logger import LoggingModule

hostname: str = attr.get_hostname()
computer_sid: str = attr.get_computer_sid() or ''
ec2_instance_id: str = attr.get_ec2_instance_id() or ''

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

def fetch_autorun_events() -> list[dict]:
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
    
    if not entries:
        return

    for entry in entries:
        entry["timestamp"] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        entry["hostname"] = hostname
        entry["sid"] = computer_sid
        entry["ec2_instance_id"] = ec2_instance_id
        entry["event"] = "existing autorun"

    final_order: list[str] = [
        "timestamp", "hostname", "event",
        "source", "entry", "path", "sid", "ec2_instance_id"
    ]
    entries = [{key: entry[key] for key in final_order} for entry in entries]
    return entries

def log_existing_data(logger: LoggingModule) -> set:
    prev_autoruns: set = set()
    autorun_data: list[dict] = fetch_autorun_events()
    for data in autorun_data:
        prev_autoruns.add((data['source'], data['entry'], data['path']))
        logger.write_log(" | ".join([f"{key}: {data[key]}" for key in data]))
    return prev_autoruns

def log_autoruns(logger: LoggingModule) -> None:
    interval = attr.get_config_value('Windows', 'AutorunInterval', 60.0, 'float')
    prev_autoruns: set = log_existing_data(logger)

    while True:
        logger.check_logging_interval()
        autorun_data: list[dict] = fetch_autorun_events()
        for data in autorun_data:
            if (data['source'], data['entry'], data['path']) in prev_autoruns:
                continue
            data["event"] = "new autorun found"
            prev_autoruns.add((data['source'], data['entry'], data['path']))
            logger.write_log(" | ".join([f"{key}: {data[key]}" for key in data]))

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