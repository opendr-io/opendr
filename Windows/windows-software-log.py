import os
import winreg
from datetime import datetime
import time
import common.attributes as attr
import common.logger as logfunc
import logging
from typing import NoReturn

log_line_count: int = 0

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

def log_installed_software(log_directory: str, ready_directory: str) -> None:
  """Logs installed software with system metadata."""
  logger: logging.Logger = logfunc.setup_logging(log_directory, ready_directory, "SoftwareMonitor", "installed_software")
  hostname: str = attr.get_hostname()
  sid: str = attr.get_computer_sid()
  instance_id: str = attr.get_ec2_instance_id()
  global log_line_count
  for name, version in get_installed_software():
      log_entry = (
        f"timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} | "
        f"hostname: {hostname} | "
        f"program: {name} | version: {version} | "
        f"instanceid: {instance_id} | sid: {sid}"
      )
      logger.info(log_entry)
      log_line_count += 1
      if int(time.time()) % 10 == 0:
        logfunc.enter_debug_logs('software-inventory', f"Running total log lines written: {log_line_count}  \n")

  logfunc.clear_handlers(log_directory, ready_directory, logger)

def run() -> NoReturn:
  interval: float = attr.get_config_value('Windows', 'SoftwareInterval', 43200.0, 'float')
  log_directory: str = 'tmp-software-inventory' if attr.get_config_value('Windows', 'RunDatabaseOperations', False, 'bool') else 'tmp'
  ready_directory: str = 'ready'
  debug_generator_directory: str = 'debuggeneratorlogs'
  os.makedirs(debug_generator_directory, exist_ok=True)
  os.makedirs(log_directory, exist_ok=True)
  os.makedirs(ready_directory, exist_ok=True)
  while True:
    log_installed_software(log_directory, ready_directory)
    time.sleep(interval)  # Twice a day by default, can be increased or decreased

run()