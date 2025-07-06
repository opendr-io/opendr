import time
from datetime import datetime
import os
from typing import NoReturn
import common.attributes as attr
import common.logger as logfunc

log_line_count: int = 0

def log_data(log_directory: str, ready_directory: str) -> NoReturn:
  interval: float = attr.get_config_value('MacOS', 'EndpointInterval', 43200.0, 'float')
  while True:
    logger = logfunc.setup_logging(log_directory, ready_directory, "EndpointMonitor", "endpoint")
    global log_line_count
    # Configure logging for the new file
    data: str = (
        f"timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} | "
        f"hostname: {attr.get_hostname()} | private_ips: {attr.get_private_ips()} | public_ip: {attr.get_public_ip()} | "
        f"ec2_instance_id: {attr.get_ec2_instance_id() or ''} | uuid: {attr.get_mac_computer_uuid() or ''}"
      )
    # Log to the newly created file
    logger.info(data)
    log_line_count += 1
    logfunc.enter_debug_logs('endpoint-info', f"Running total log lines written: {log_line_count}  \n")
    logfunc.clear_handlers(log_directory, ready_directory, logger)
    time.sleep(interval)  # Log every 60 minutes - or choose an interval

def run() -> NoReturn:
  log_directory: str = 'tmp-endpoint-info' if attr.get_config_value('MacOS', 'RunDatabaseOperations', False, 'bool') else 'tmp'
  ready_directory: str = 'ready'
  debug_generator_directory: str = 'debuggeneratorlogs'
  os.makedirs(debug_generator_directory, exist_ok=True)
  os.makedirs(log_directory, exist_ok=True)
  os.makedirs(ready_directory, exist_ok=True)
  log_data(log_directory, ready_directory)

run()