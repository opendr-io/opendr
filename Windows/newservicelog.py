import os
import sys
import psutil
from datetime import datetime
import time
import common.attributes as attr
import common.logger as logfunc

if os.name != 'nt':
    sys.exit("platform not supported (Windows only)")

log_line_count = 0
hostname = attr.get_hostname()
computer_sid = attr.get_computer_sid()

def log_existing_services(logger):
    previous_services = []
    for service in psutil.win_service_iter():
        try:
            info = service.as_dict()
            if str((info['pid'], info['name'])) not in previous_services:
                service_info = (
                    f"timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} | "
                    f"hostname: {hostname} | username: {info['username']} | event: existing service | "
                    f"pid: {info['pid']} | servicename: {info['name']!r} | displayname: {info['display_name']!r} | "
                    f"status: {info['status']} | start: {info['start_type']} | "
                    f"executable: {info['binpath']} | sid: {computer_sid}"
                )
                logger.info(service_info)
                log_line_count += 1
                previous_services.append(str((info['pid'], info['name'])))
        except Exception as e:
            print(e)

    return previous_services

def log_services(log_directory, ready_directory, interval):
    """Logs running Windows services, formatted in a single line per service."""
    logger, last_interval  = logfunc.check_logging_interval(log_directory, ready_directory, "NewServiceMonitor", "newservice", None, None)
    previous_services = log_existing_services(logger)
    while True:
        logger, last_interval = logfunc.check_logging_interval(log_directory, ready_directory, "NewServiceMonitor", "newservice", logger, last_interval)

        for service in psutil.win_service_iter():
            try:
                info = service.as_dict()
                if str((info['pid'], info['name'])) not in previous_services:
                    service_info = (
                        f"timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} | "
                        f"hostname: {hostname} | username: {info['username']} | event: new service | "
                        f"pid: {info['pid']} | servicename: {info['name']!r} | displayname: {info['display_name']!r} | "
                        f"status: {info['status']} | start: {info['start_type']} | "
                        f"executable: {info['binpath']} | sid: {computer_sid}"
                    )
                    logger.info(service_info)
                    log_line_count += 1
                    previous_services.append(str((info['pid'], info['name'])))
            except Exception as e:
                print(e)
        time.sleep(interval)

def run():
    interval = attr.get_config_value('Windows', 'NewServiceInterval', 60.0, 'float')
    log_directory = 'tmp-windows-new-service' if attr.get_config_value('General', 'RunDatabaseOperations', False, 'bool') else 'tmp'
    ready_directory = 'ready'
    debug_generator_directory = 'debuggeneratorlogs'
    os.makedirs(debug_generator_directory, exist_ok=True)
    os.makedirs(log_directory, exist_ok=True)
    os.makedirs(ready_directory, exist_ok=True)
    print('newserviceslog running')
    log_services(log_directory, ready_directory, interval)

run()