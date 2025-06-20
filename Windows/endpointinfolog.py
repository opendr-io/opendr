import time
from datetime import datetime
import os
import common.attributes as attr
import common.logger as logfunc

log_line_count = 0

def log_data(log_directory, ready_directory):
  interval = attr.get_config_value('Windows', 'EndpointInterval', 43200.0, 'float')
  while True:
    logger = logfunc.setup_logging(log_directory, ready_directory, "EndpointMonitor", "endpoint")
    global log_line_count
    # Configure logging for the new file
    data = (
        f"timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} | "
        f"hostname: {attr.get_hostname()} | private_ips: {attr.get_private_ips()} | public_ip: {attr.get_public_ip()} | "
        f"sid: {attr.get_computer_sid() or ''} | ec2_instance_id: {attr.get_ec2_instance_id() or ''}"
      )
    # Log to the newly created file
    logger.info(data)
    log_line_count += 1
    logfunc.enter_debug_logs('endpoint-info', f"Running total log lines written: {log_line_count}  \n")
    logfunc.clear_handlers(log_directory, ready_directory, logger)
    time.sleep(interval)  # Log every 12 hours - or choose an interval

def run():
  log_directory = 'tmp-endpoint-info' if attr.get_config_value('Windows', 'RunDatabaseOperations', False, 'bool') else 'tmp'
  ready_directory = 'ready'
  debug_generator_directory = 'debuggeneratorlogs'
  os.makedirs(debug_generator_directory, exist_ok=True)
  os.makedirs(log_directory, exist_ok=True)
  os.makedirs(ready_directory, exist_ok=True)
  log_data(log_directory, ready_directory)

run()