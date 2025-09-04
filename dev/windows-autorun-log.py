import os
import winreg
import time
from datetime import datetime
import common.attributes as attr
from common.logger import LoggingModule

class WindowsAutorunLogger():
    def __init__(self):
        self.sid: str = attr.get_computer_sid()
        self.hostname: str = attr.get_hostname()
        self.ec2_instance_id: str = attr.get_ec2_instance_id() or ''
        self.interval: float = attr.get_config_value('Windows', 'AutorunInterval', 60.0, 'float')
        self.logger = None
        self.prev_autoruns: set = set()
        self.setup_logger()
        self.log_existing()
        print('WindowsAutorunLogger Initialization complete')

    def setup_logger(self) -> None:
        log_directory: str = 'tmp-windows-autoruns' if attr.get_config_value('General', 'RunDatabaseOperations', False, 'bool') else 'tmp'
        ready_directory: str = 'ready'
        debug_generator_directory: str = 'debuggeneratorlogs'
        os.makedirs(debug_generator_directory, exist_ok=True)
        os.makedirs(log_directory, exist_ok=True)
        os.makedirs(ready_directory, exist_ok=True)
        self.logger: LoggingModule = LoggingModule(log_directory, ready_directory, "AutorunsMonitor", "autoruns")

    def enum_run_keys(self, hive, path) -> list:
        """Enumerates entries under a Run/RunOnce registry key."""
        entries = []
        try:
            key = winreg.OpenKey(hive, path)
            for i in range(winreg.QueryInfoKey(key)[1]):
                name, value, _ = winreg.EnumValue(key, i)
                entries.append({
                    "source": f"{self.hive_name(hive)}\\{path}",
                    "entry": name,
                    "path": value
                })
            winreg.CloseKey(key)
        except FileNotFoundError:
            pass
        return entries

    @staticmethod
    def hive_name(hive):
        return {
            winreg.HKEY_LOCAL_MACHINE: "HKLM",
            winreg.HKEY_CURRENT_USER: "HKCU"
        }.get(hive, str(hive))

    def enum_startup_folder_entries(self) -> list:
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

    def fetch_autorun_events(self) -> list[dict]:
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
            entries.extend(self.enum_run_keys(hive, path))

        # Startup folder .lnk files
        entries.extend(self.enum_startup_folder_entries())
        
        if not entries:
            return

        for entry in entries:
            entry["timestamp"] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            entry["hostname"] = self.hostname
            entry["sid"] = self.sid
            entry["ec2_instance_id"] = self.ec2_instance_id
            entry["event"] = "existing autorun"

        final_order: list[str] = [
            "timestamp", "hostname", "event",
            "source", "entry", "path", "sid", "ec2_instance_id"
        ]
        entries = [{key: entry[key] for key in final_order} for entry in entries]
        return entries

    def log_existing(self) -> None:
        autorun_data: list[dict] = self.fetch_autorun_events()
        for data in autorun_data:
            self.prev_autoruns.add((data['source'], data['entry'], data['path']))
            self.logger.write_log(" | ".join([f"{key}: {data[key]}" for key in data]))

    def monitor_events(self) -> None:
        self.logger.check_logging_interval()
        autorun_data: list[dict] = self.fetch_autorun_events()
        for data in autorun_data:
            if (data['source'], data['entry'], data['path']) in self.prev_autoruns:
                continue
            data["event"] = "new autorun found"
            self.prev_autoruns.add((data['source'], data['entry'], data['path']))
            self.logger.write_log(" | ".join([f"{key}: {data[key]}" for key in data]))

        self.logger.write_debug_log(f'timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} | '
                            f'hostname: {self.hostname} | source: autorun | platform: windows | event: progress | '
                            f'message: {self.logger.log_line_count} log lines written | value: {self.logger.log_line_count}')

if __name__ == '__main__':
    autorun = WindowsAutorunLogger()
    while True:
        autorun.monitor_events()
        time.sleep(autorun.interval)
