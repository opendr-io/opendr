import time
from datetime import datetime
import os
import common.attributes as attr
from common.logger import LoggingModule

class MacOSEndpointLogger(attr.LoggerParent):
  def __init__(self):
    super().__init__()
    self.interval: float = attr.get_config_value('MacOS', 'EndpointInterval', 60.0, 'float')
    self.previous_info: set = set()
    self.setup_logger()
    self.log_existing()
    print('MacOSEndpointLogger Initialization complete')

  def setup_logger(self) -> None:
    log_directory: str = 'tmp-endpoint-info' if attr.get_config_value('General', 'RunDatabaseOperations', False, 'bool') else 'tmp'
    ready_directory: str = 'ready'
    debug_generator_directory: str = 'debuggeneratorlogs'
    os.makedirs(debug_generator_directory, exist_ok=True)
    os.makedirs(log_directory, exist_ok=True)
    os.makedirs(ready_directory, exist_ok=True)
    self.logger: LoggingModule = LoggingModule(log_directory, ready_directory, "EndpointMonitor", "endpoint")

  def log_existing(self) -> None:
    data: str = (
        f"timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} | "
        f"hostname: {self.hostname} | event: endpoint identified | "
        f"private_ips: {attr.get_private_ips()} | public_ip: {attr.get_public_ip()} | "
        f"ec2_instance_id: {self.ec2_instance_id} | sid: {self.sid}"
      )
    self.logger.write_log(data)
    self.previous_info.add((self.hostname, ''.join(attr.get_private_ips()), attr.get_public_ip()))

  def monitor_events(self) -> None:
    self.logger.check_logging_interval()
    if (self.hostname, ''.join(attr.get_private_ips()), attr.get_public_ip()) in self.previous_info:
      return
    data: str = (
      f"timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} | "
      f"hostname: {self.hostname} | event: endpoint modified | "
      f"private_ips: {attr.get_private_ips()} | public_ip: {attr.get_public_ip()} | "
      f"ec2_instance_id: {self.ec2_instance_id} | uuid: {self.sid}"
    )
    self.logger.write_log(data)
    self.previous_info.add((self.hostname, ''.join(attr.get_private_ips()), attr.get_public_ip()))
    self.logger.write_debug_log(f"timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} | "
                          f"hostname: {self.hostname} | source: endpoint | platform: macos | event: progress | "
                          f"message: {self.logger.log_line_count} log lines written | value: {self.logger.log_line_count}")

if __name__ == '__main__':
    endpoint = MacOSEndpointLogger()
    while True:
        endpoint.monitor_events()
        time.sleep(endpoint.interval)

