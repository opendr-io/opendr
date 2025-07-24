import os
import time
import common.attributes as attr
from common.logger import LoggingModule
from datetime import datetime
from typing import NoReturn

hostname: str = attr.get_hostname()
uuid = attr.get_system_uuid()

def log_initial_inventory(logger: LoggingModule):
    services: list[dict] = attr.get_all_service_statuses()
    seen_services: list[tuple] = []
    for service in services:
        logger.write_log((
            f"timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} | hostname: {hostname} | "
            f"name: {service['name']} | active: {service['active_state']} | sub: ({service['sub_state']}) | "
            f"description: {service['description']} | event: existing service | uuid: {uuid}"
            ))
        seen_services.append((service['name'], service['active_state'], service['description']))
    return seen_services

def log_data(logger: LoggingModule) -> NoReturn:
    interval: float = attr.get_config_value('Linux', 'ServiceInterval', 60.0, 'float')
    seen_services = log_initial_inventory(logger)
    while True:
        logger.check_logging_interval()
        services: list[dict] = attr.get_all_service_statuses()
        for service in services:
            if (service['name'], service['active_state'], service['description']) not in seen_services:
                logger.write_log((
                    f"timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} | hostname: {hostname} | "
                    f"name: {service['name']} | active: {service['active_state']} | sub: ({service['sub_state']}) | "
                    f"description: {service['description']} | event: new service | uuid: {uuid}"
                    ))
                seen_services.append((service['name'], service['active_state'], service['description']))

        logger.write_debug_log(f'timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} | '
                            f'hostname: {hostname} | source: service | platform: linux | event: progress | '
                            f'message: {logger.log_line_count} log lines written | value: {logger.log_line_count}')
        time.sleep(interval)

def run() -> NoReturn:
    log_directory: str = 'tmp-linux-services' if attr.get_config_value('General', 'RunDatabaseOperations', False, 'bool') else 'tmp'
    ready_directory: str = 'ready'
    debug_generator_directory: str = 'debuggeneratorlogs'
    os.makedirs(debug_generator_directory, exist_ok=True)
    os.makedirs(log_directory, exist_ok=True)
    os.makedirs(ready_directory, exist_ok=True)
    logger: LoggingModule = LoggingModule(log_directory, ready_directory, "ServiceMonitor", "services")
    log_data(logger)

run()