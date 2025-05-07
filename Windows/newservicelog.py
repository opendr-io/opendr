import os
import sys
import psutil
from datetime import datetime
import time
import common.attributes as attr
import common.logger as logfunc

if os.name != 'nt':
    sys.exit("platform not supported (Windows only)")

# Create log directory
log_line_count = 0

def log_services(log_directory, ready_directory, interval):
    """Logs running Windows services, formatted in a single line per service."""
    logger, last_interval  = logfunc.check_logging_interval(log_directory, ready_directory, "NewServiceMonitor", "newservice", None, None)
    hostname = attr.get_hostname()
    computer_sid = attr.get_computer_sid()
    global log_line_count
    previous_services = [service.pid for service in psutil.win_service_iter()]
    while True:
        logger, last_interval = logfunc.check_logging_interval(log_directory, ready_directory, "NewServiceMonitor", "newservice", logger, last_interval)

        for service in psutil.win_service_iter():
            info = service.as_dict()
            if info['pid'] not in previous_services: 
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
                previous_services.append(info['pid'])
        time.sleep(interval)

def run():
    interval = attr.get_config_value('Windows', 'NewServiceInterval', 60.0, 'float')
    log_directory = 'tmp-windows-new-service'
    ready_directory = 'ready'
    debug_generator_directory = 'debuggeneratorlogs'
    os.makedirs(debug_generator_directory, exist_ok=True)
    os.makedirs(log_directory, exist_ok=True)
    os.makedirs(ready_directory, exist_ok=True)
    print('newserviceslog running')
    log_services(log_directory, ready_directory, interval)

run()