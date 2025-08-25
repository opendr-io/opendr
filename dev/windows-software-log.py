import os
import winreg
from datetime import datetime
import time
import common.attributes as attr
from common.logger import LoggingModule
from typing import NoReturn

class WindowsSoftwareLogger():
  def __init__(self):
    self.sid: str = attr.get_computer_sid()
    self.hostname: str = attr.get_hostname()
    self.instance_id: str = attr.get_ec2_instance_id()
    self.interval: float = attr.get_config_value('Windows', 'SoftwareInterval', 43200.0, 'float')
    self.logger = None
    self.previous_processes: set[int] = set()
    self.setup_logger()
    self.log_existing()
    print('WindowsProcessLogger Initialization complete')

  def setup_logger(self) -> None:
    log_directory: str = 'tmp-software-inventory' if attr.get_config_value('General', 'RunDatabaseOperations', False, 'bool') else 'tmp'
    ready_directory: str = 'ready'
    debug_generator_directory: str = 'debuggeneratorlogs'
    os.makedirs(debug_generator_directory, exist_ok=True)
    os.makedirs(log_directory, exist_ok=True)
    os.makedirs(ready_directory, exist_ok=True)
    self.logger: LoggingModule  = LoggingModule(log_directory, ready_directory, "ProcessMonitor", "process")

  @staticmethod
  def get_installed_software() -> list[tuple]:
    """Retrieve installed software from Windows registry."""
    software_list: list[tuple] = []
    registry_paths: list[str] = [
        r"SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall",
        r"SOFTWARE\WOW6432Node\Microsoft\Windows\CurrentVersion\Uninstall"
    ]
    for path in registry_paths:
      try:
        reg_key: winreg.HKEYType = winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, path)
        for i in range(0, winreg.QueryInfoKey(reg_key)[0]):
          sub_key_name: str = winreg.EnumKey(reg_key, i)
          sub_key: winreg.HKEYType = winreg.OpenKey(reg_key, sub_key_name)
          try:
            name = winreg.QueryValueEx(sub_key, "DisplayName")[0]
            version = winreg.QueryValueEx(sub_key, "DisplayVersion")[0]
            software_list.append((name, version))
          except FileNotFoundError:
            continue
          finally:
            sub_key.Close()
        reg_key.Close()
      except FileNotFoundError:
        continue
    return software_list

  def monitor_events(self) -> None:
    """Logs installed software with system metadata."""
    self.logger.check_logging_interval()
    for name, version in self.get_installed_software():
        log_entry = (
          f"timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} | "
          f"hostname: {self.hostname} | "
          f"program: {name} | version: {version} | "
          f"instanceid: {self.instance_id} | sid: {self.sid}"
        )
        self.logger.write_log(log_entry)
        if int(time.time()) % 10 == 0:
          self.logger.write_debug_log(f'timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} | '
                          f'hostname: {self.hostname} | source: software | platform: windows | event: progress | '
                          f'message: {self.logger.log_line_count} log lines written | value: {self.logger.log_line_count}')

    self.logger.clear_handlers()