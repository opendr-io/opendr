import os
import time
import common.attributes as attr
import common.logger as logfunc
from datetime import datetime
from typing import NoReturn

hostname: str = attr.get_hostname()
uuid = attr.get_system_uuid()

log_line_count: int = 0

def log_data(log_directory: str, ready_directory: str) -> NoReturn:
    interval = attr.get_config_value('Linux', 'ServiceInterval', 43200.0, 'float')
    while True:
        logger = logfunc.setup_logging(log_directory, ready_directory, "ServiceMonitor", "services")
        global log_line_count
        services: list[dict] = attr.get_all_service_statuses()
        for service in services:
            logger.info((
                f"timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} | hostname: {hostname} | "
                f"name: {service['name']} | active: {service['active_state']} | sub: ({service['sub_state']}) | "
                f"description: {service['description']} | uuid: {uuid}"
                ))
            log_line_count += 1

        logfunc.enter_debug_logs('linux-services', f"Running total log lines written: {log_line_count}  \n")
        logfunc.clear_handlers(log_directory, ready_directory, logger)
        time.sleep(interval)  # Log every 60 minutes - or choose an interval

def run() -> NoReturn:
    log_directory: str = 'tmp-linux-services' if attr.get_config_value('Linux', 'RunDatabaseOperations', False, 'bool') else 'tmp'
    ready_directory: str = 'ready'
    debug_generator_directory: str = 'debuggeneratorlogs'
    os.makedirs(debug_generator_directory, exist_ok=True)
    os.makedirs(log_directory, exist_ok=True)
    os.makedirs(ready_directory, exist_ok=True)
    log_data(log_directory, ready_directory)

run()