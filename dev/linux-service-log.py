import os
import time
import common.attributes as attr
from common.logger import LoggingModule
from datetime import datetime

class LinuxServiceLogger(attr.LoggerParent):
    def __init__(self):
        super().__init__()
        self.interval: float = attr.get_config_value('Linux', 'ServiceInterval', 60.0, 'float')
        self.previous_services: set = set()
        self.setup_logger()
        self.log_existing()
        print('LinuxServiceLogger Initialization complete')

    def setup_logger(self) -> None:
        log_directory: str = 'tmp-linux-services' if attr.get_config_value('General', 'RunDatabaseOperations', False, 'bool') else 'tmp'
        ready_directory: str = 'ready'
        debug_generator_directory: str = 'debuggeneratorlogs'
        os.makedirs(debug_generator_directory, exist_ok=True)
        os.makedirs(log_directory, exist_ok=True)
        os.makedirs(ready_directory, exist_ok=True)
        self.logger: LoggingModule  = LoggingModule(log_directory, ready_directory, "ServiceMonitor", "services")

    def log_existing(self) -> None:
        services: list[dict] = attr.get_all_service_statuses()
        for service in services:
            self.logger.write_log((
                f"timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} | hostname: {self.hostname} | "
                f"name: {service['name']} | active: {service['active_state']} | sub: ({service['sub_state']}) | "
                f"description: {service['description']} | event: existing service | uuid: {self.sid}"
                ))
            self.previous_services.add((service['name'], service['active_state'], service['description']))

    def monitor_events(self) -> None:
        self.logger.check_logging_interval()
        services: list[dict] = attr.get_all_service_statuses()
        for service in services:
            if (service['name'], service['active_state'], service['description']) in self.previous_services:
                continue
            self.logger.write_log((
                f"timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} | hostname: {self.hostname} | "
                f"name: {service['name']} | active: {service['active_state']} | sub: ({service['sub_state']}) | "
                f"description: {service['description']} | event: new service | uuid: {self.sid}"
                ))
            self.previous_services.add((service['name'], service['active_state'], service['description']))

        self.logger.write_debug_log(f"timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} | "
                            f"hostname: {self.hostname} | source: service | platform: linux | event: progress | "
                            f"message: {self.logger.log_line_count} log lines written | value: {self.logger.log_line_count}")

if __name__ == '__main__':
    service = LinuxServiceLogger()
    while True:
        service.monitor_events()
        time.sleep(service.interval)

