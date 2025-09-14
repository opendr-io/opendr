import time
from datetime import datetime
import os
import common.attributes as attr
from common.logger import LoggingModule
from typing import NoReturn

hostname: str = attr.get_hostname()
uuid: str = attr.get_system_uuid() or ''
ec2_instance_id: str = attr.get_ec2_instance_id() or ''

def log_existing(logger: LoggingModule) -> set:
  previous_info: set = set()
  data: str = (
      f"timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} | "
      f"hostname: {hostname} | event: endpoint identified | "
      f"private_ips: {attr.get_private_ips()} | public_ip: {attr.get_public_ip()} | "
      f"ec2_instance_id: {ec2_instance_id} | uuid: {uuid}"
    )
  logger.write_log(data)
  previous_info.add((hostname, ''.join(attr.get_private_ips()), attr.get_public_ip()))
  return previous_info

def log_data(logger: LoggingModule) -> NoReturn:
  interval: float = attr.get_config_value('Linux', 'EndpointInterval', 43200.0, 'float')
  previous_info: set = log_existing(logger)
  while True:
    logger.check_logging_interval()
    if (hostname, ''.join(attr.get_private_ips()), attr.get_public_ip()) in previous_info:
      time.sleep(interval)
      continue
    data: str = (
      f"timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} | "
      f"hostname: {hostname} | event: endpoint modified | "
      f"private_ips: {attr.get_private_ips()} | public_ip: {attr.get_public_ip()} | "
      f"ec2_instance_id: {ec2_instance_id} | uuid: {uuid}"
    )
    logger.write_log(data)
    previous_info.add((hostname, ''.join(attr.get_private_ips()), attr.get_public_ip()))
    logger.write_debug_log(f'timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} | '
                        f'hostname: {hostname} | source: endpoint | platform: linux | event: progress | '
                        f'message: {logger.log_line_count} log lines written | value: {logger.log_line_count}')
    time.sleep(interval)

def run() -> NoReturn:
  log_directory: str = 'tmp-endpoint-info' if attr.get_config_value('General', 'RunDatabaseOperations', False, 'bool') else 'tmp'
  ready_directory: str = 'ready'
  debug_generator_directory: str = 'debuggeneratorlogs'
  os.makedirs(debug_generator_directory, exist_ok=True)
  os.makedirs(log_directory, exist_ok=True)
  os.makedirs(ready_directory, exist_ok=True)
  logger = LoggingModule(log_directory, ready_directory, "EndpointMonitor", "endpoint")
  log_data(logger)

run()