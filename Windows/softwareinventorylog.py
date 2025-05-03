import os
import winreg
from datetime import datetime
import time
import common.attributes as attr
import common.logger as logfunc

log_line_count = 0

def get_installed_software():
  """Retrieve installed software from Windows registry."""
  software_list = []
  registry_paths = [
      r"SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall",
      r"SOFTWARE\WOW6432Node\Microsoft\Windows\CurrentVersion\Uninstall"
  ]
  for path in registry_paths:
    try:
      reg_key = winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, path)
      for i in range(0, winreg.QueryInfoKey(reg_key)[0]):
        sub_key_name = winreg.EnumKey(reg_key, i)
        sub_key = winreg.OpenKey(reg_key, sub_key_name)
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

def log_installed_software(log_directory, ready_directory):
  """Logs installed software with system metadata."""
  # log_file = setup_logging(log_directory, ready_directory)
  logger = logfunc.setup_logging(log_directory, ready_directory, "SoftwareMonitor", "installed_software")
  hostname = attr.get_hostname()
  sid = attr.get_computer_sid()
  instance_id = attr.get_ec2_instance_id()
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

def run():
  interval = attr.get_config_value('Windows', 'SoftwareInterval', 43200.0, 'float')
  log_directory = 'tmp-software-inventory'
  ready_directory = 'ready'
  debug_generator_directory = 'debuggeneratorlogs'
  os.makedirs(debug_generator_directory, exist_ok=True)
  os.makedirs(log_directory, exist_ok=True)
  os.makedirs(ready_directory, exist_ok=True)
  while True:
    log_installed_software(log_directory, ready_directory)
    time.sleep(interval)  # Twice a day by default, can be increased or decreased

run()