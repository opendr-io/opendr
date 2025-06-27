import os
import time
import common.attributes as attr
import common.logger as logfunc
from datetime import datetime

hostname = attr.get_hostname()
uuid = attr.get_system_uuid()

log_line_count = 0

def log_data(log_directory, ready_directory):
    interval = attr.get_config_value('Linux', 'NewServiceInterval', 60.0, 'float')
    previous_services = [str((service['name'], service['description'])) for service in attr.get_all_service_statuses()]
    logger, last_interval = logfunc.check_logging_interval(log_directory, ready_directory, "NewServiceMonitor", "newservice", None, None)
    global log_line_count
    while True:
        services = attr.get_all_service_statuses()
        for service in services:
            if str((service['name'], service['description'])) not in previous_services:
                logger.info((
                    f"timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} | hostname: {hostname} | "
                    f"name: {service['name']} | active: {service['active_state']} | sub: ({service['sub_state']}) | "
                    f"description: {service['description']} | uuid: {uuid}"
                    ))
                previous_services.append(str((service['name'], service['description'])))
                log_line_count += 1

        logfunc.enter_debug_logs('linux-newservice', f"Running total log lines written: {log_line_count}  \n")
        logger, last_interval = logfunc.check_logging_interval(log_directory, ready_directory, "NewServiceMonitor", "newservice", logger, last_interval)
        time.sleep(interval)

def run():
    log_directory = 'tmp-linux-new-service' if attr.get_config_value('Linux', 'RunDatabaseOperations', False, 'bool') else 'tmp'
    ready_directory = 'ready'
    debug_generator_directory = 'debuggeneratorlogs'
    os.makedirs(debug_generator_directory, exist_ok=True)
    os.makedirs(log_directory, exist_ok=True)
    os.makedirs(ready_directory, exist_ok=True)
    log_data(log_directory, ready_directory)

run()