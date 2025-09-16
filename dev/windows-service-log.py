import os
import psutil
from datetime import datetime
import time
import common.attributes as attr
from common.logger import LoggingModule


class WindowsServiceLogger(attr.LoggerParent):
    def __init__(self):
        super().__init__()
        self.interval: float = attr.get_config_value('Windows', 'ServiceInterval', 60.0, 'float')
        self.previous_services: set = set()
        self.setup_logger()
        self.log_existing()
        print('WindowsServiceLogger Initialization complete')

    def setup_logger(self) -> None:
        log_directory: str = 'tmp-windows-service' if attr.get_config_value('General', 'RunDatabaseOperations', False, 'bool') else 'tmp'
        ready_directory: str = 'ready'
        debug_generator_directory: str = 'debuggeneratorlogs'
        os.makedirs(debug_generator_directory, exist_ok=True)
        os.makedirs(log_directory, exist_ok=True)
        os.makedirs(ready_directory, exist_ok=True)
        self.logger: LoggingModule = LoggingModule(log_directory, ready_directory, "ServiceMonitor", "services")

    def log_existing(self) -> None:
        for service in psutil.win_service_iter():
            try:
                info = service.as_dict()
                if str((info['pid'], info['name'])) in self.previous_services:
                    continue
                service_info = (
                    f"timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} | "
                    f"hostname: {self.hostname} | username: {info['username']} | event: existing service | "
                    f"pid: {info['pid']} | servicename: {info['name']!r} | displayname: {info['display_name']!r} | "
                    f"status: {info['status']} | start: {info['start_type']} | "
                    f"executable: {info['binpath']} | sid: {self.sid}"
                )
                self.logger.write_log(service_info)
                self.previous_services.add(str((info['pid'], info['name'])))
            except Exception as e:
                print(e)

    def monitor_events(self) -> None:
        """Logs running Windows services, formatted in a single line per service."""
        self.logger.check_logging_interval()

        for service in psutil.win_service_iter():
            try:
                info = service.as_dict()
                if str((info['pid'], info['name'])) in self.previous_services:
                    continue
                service_info = (
                    f"timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} | "
                    f"hostname: {self.hostname} | username: {info['username']} | event: new service | "
                    f"pid: {info['pid']} | servicename: {info['name']!r} | displayname: {info['display_name']!r} | "
                    f"status: {info['status']} | start: {info['start_type']} | "
                    f"executable: {info['binpath']} | sid: {self.sid}"
                )
                self.logger.write_log(service_info)
                self.previous_services.add(str((info['pid'], info['name'])))
            except Exception as e:
                print(e)

if __name__ == '__main__':
    service = WindowsServiceLogger()
    while True:
        service.monitor_events()
        time.sleep(service.interval)
