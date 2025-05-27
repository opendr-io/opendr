import os
import sys
import psutil
from datetime import datetime
import time
import common.attributes as attr
import common.logger as logfunc
from typing import NoReturn

if os.name != 'nt':
  sys.exit("platform not supported (Windows only)")

# Create log directory
log_line_count: int = 0

def log_services(log_directory: str, ready_directory: str) -> None:
  """Logs running Windows services, formatted in a single line per service."""
  logger = logfunc.setup_logging(log_directory, ready_directory, "ServiceMonitor", "services")
  
  hostname: str = attr.get_hostname()
  computer_sid: str = attr.get_computer_sid()
  global log_line_count
  # print(f"Logging to: {log_file}")  # Print log filename for tracking

  for service in psutil.win_service_iter():
    try:
      info = service.as_dict()
      if info['status'] == 'running': 
        service_info = (
          f"timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} | "
          f"hostname: {hostname} | username: {info['username']} | "
          f"pid: {info['pid']} | servicename: {info['name']!r} | displayname: {info['display_name']!r} | "
          f"status: {info['status']} | start: {info['start_type']} | "
          f"executable: {info['binpath']} | "
          f"sid: {computer_sid} | "
        )
        logger.info(service_info)
        log_line_count += 1
    except Exception as e:
      print(e)

  logfunc.enter_debug_logs('windows-services', f"Running total log lines written: {log_line_count}  \n")
  logfunc.clear_handlers(log_directory, ready_directory, logger)

def run() -> NoReturn:
  interval: float = attr.get_config_value('Windows', 'ServiceInterval', 43200.0, 'float')
  log_directory: str = 'tmp-windows-services' if attr.get_config_value('Windows', 'RunDatabaseOperations', False, 'bool') else 'tmp'
  ready_directory: str = 'ready'
  debug_generator_directory: str = 'debuggeneratorlogs'
  os.makedirs(debug_generator_directory, exist_ok=True)
  os.makedirs(log_directory, exist_ok=True)
  os.makedirs(ready_directory, exist_ok=True)
  print('windowsserviceslog running')
  while True:
    log_services(log_directory, ready_directory)
    time.sleep(interval)  # Twice a day by default, can be increased or decreased

run()