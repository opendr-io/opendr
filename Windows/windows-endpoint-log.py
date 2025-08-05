import time
from datetime import datetime
import os
from typing import NoReturn
import common.attributes as attr
from common.logger import LoggingModule

def log_data(logger: LoggingModule) -> NoReturn:
  interval = attr.get_config_value('Windows', 'EndpointInterval', 43200.0, 'float')
  while True:
    logger.check_logging_interval()
    # Configure logging for the new file
    data = (
        f"timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} | "
        f"hostname: {attr.get_hostname()} | private_ips: {attr.get_private_ips()} | public_ip: {attr.get_public_ip()} | "
        f"sid: {attr.get_computer_sid() or ''} | ec2_instance_id: {attr.get_ec2_instance_id() or ''}"
      )
    # Log to the newly created file
    logger.write_log(data)
    logger.write_debug_log(f'timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} | '
                          f'hostname: {attr.get_hostname()} | source: endpoint | platform: windows | event: progress | '
                          f'message: {logger.log_line_count} log lines written | value: {logger.log_line_count}')
    logger.clear_handlers()
    time.sleep(interval)  # Log every 12 hours - or choose an interval

def run() -> NoReturn:
  log_directory: str = 'tmp-endpoint-info' if attr.get_config_value('General', 'RunDatabaseOperations', False, 'bool') else 'tmp'
  ready_directory: str = 'ready'
  debug_generator_directory: str = 'debuggeneratorlogs'
  os.makedirs(debug_generator_directory, exist_ok=True)
  os.makedirs(log_directory, exist_ok=True)
  os.makedirs(ready_directory, exist_ok=True)
  logger: LoggingModule  = LoggingModule(log_directory, ready_directory, "EndpointMonitor", "endpoint")
  log_data(logger)

run()