import os
import sys
import psutil
from datetime import datetime
import time
import common.attributes as attr
from common.logger import LoggingModule
from typing import NoReturn

if os.name != 'nt':
  sys.exit("platform not supported (Windows only)")

# Create log directory
log_line_count: int = 0

def log_services(logger: LoggingModule, debug_logger: LoggingModule) -> None:
  """Logs running Windows services, formatted in a single line per service."""
  logger.check_logging_interval()
  
  hostname: str = attr.get_hostname()
  computer_sid: str = attr.get_computer_sid()
  global log_line_count

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
        logger.write_log(service_info)
        log_line_count += 1
    except Exception as e:
      print(e)

    debug_logger.check_logging_interval()
    debug_logger.write_log(f'timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} | '
                    f'hostname: {hostname} | source: service | platform: windows | event: progress | '
                    f'message: Running {log_line_count} log lines written | value: {log_line_count}')

  logger.clear_handlers()

def run() -> NoReturn:
  interval: float = attr.get_config_value('Windows', 'ServiceInterval', 43200.0, 'float')
  log_directory: str = 'tmp-windows-services' if attr.get_config_value('General', 'RunDatabaseOperations', False, 'bool') else 'tmp'
  ready_directory: str = 'ready'
  debug_generator_directory: str = 'debuggeneratorlogs'
  os.makedirs(debug_generator_directory, exist_ok=True)
  os.makedirs(log_directory, exist_ok=True)
  os.makedirs(ready_directory, exist_ok=True)
  print('windowsserviceslog running')
  logger: LoggingModule  = LoggingModule(log_directory, ready_directory, "ServiceMonitor", "services")
  debug_logger: LoggingModule = LoggingModule(debug_generator_directory, ready_directory, "DebugMonitor", "debug")
  while True:
    log_services(logger, debug_logger)
    time.sleep(interval)  # Twice a day by default, can be increased or decreased

run()