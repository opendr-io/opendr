import time
from datetime import datetime
import os
import common.attributes as attr
from common.logger import LoggingModule
from typing import NoReturn


def log_data(log_directory: str, ready_directory: str) -> NoReturn:
  interval: float = attr.get_config_value('Linux', 'EndpointInterval', 43200.0, 'float')
  logger = LoggingModule(log_directory, ready_directory, "EndpointMonitor", "endpoint")
  while True:
    # Configure logging for the new file
    data: str = (
        f"timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} | "
        f"hostname: {attr.get_hostname()} | private_ips: {attr.get_private_ips()} | public_ip: {attr.get_public_ip()} | "
        f"ec2_instance_id: {attr.get_ec2_instance_id() or ''} | computer_uuid: {attr.get_system_uuid() or ''}"
      )
    # Log to the newly created file
    logger.write_log(data)
    logger.clear_handlers()
    time.sleep(interval)

def run() -> NoReturn:
  log_directory: str = 'tmp-endpoint-info' if attr.get_config_value('General', 'RunDatabaseOperations', False, 'bool') else 'tmp'
  ready_directory: str = 'ready'
  debug_generator_directory: str = 'debuggeneratorlogs'
  os.makedirs(debug_generator_directory, exist_ok=True)
  os.makedirs(log_directory, exist_ok=True)
  os.makedirs(ready_directory, exist_ok=True)
  log_data(log_directory, ready_directory)

run()