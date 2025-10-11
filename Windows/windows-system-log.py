import os
import psutil
from datetime import datetime
import time
import common.attributes as attr
from common.logger import LoggingModule

class WindowsSystemLogger(attr.LoggerParent):
    def __init__(self):
        super().__init__()
        self.interval: float = 10.0
        self.prev_records: set = set()
        self.setup_logger()
        self.log_existing()
        print("WindowsSystemLogger Initialization complete")
        self.logger.write_debug_log(
            f"timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} | "
            f"hostname: {self.hostname} | source: system | platform: windows | event: start "
        )

    def setup_logger(self) -> None:
        log_directory: str = (
            "tmp-system"
            if attr.get_config_value("General", "RunDatabaseOperations", False, "bool")
            else "tmp"
        )
        ready_directory: str = "ready"
        debug_generator_directory: str = "debuggeneratorlogs"
        os.makedirs(debug_generator_directory, exist_ok=True)
        os.makedirs(log_directory, exist_ok=True)
        os.makedirs(ready_directory, exist_ok=True)
        self.logger: LoggingModule = LoggingModule(
            log_directory, ready_directory, "SystemMonitor", "system"
        )

    def stop_logger(self) -> None:
        self.logger.write_debug_log(
            f"timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} | "
            f"hostname: {self.hostname} | source: system | platform: windows | event: stop "
        )
        self.logger.clear_handlers()

    def log_existing(self) -> None:
        self.prev_read = psutil.disk_io_counters().read_bytes/100000
        self.prev_write = psutil.disk_io_counters().write_bytes/100000
        self.prev_rec = psutil.net_io_counters().bytes_recv/100000
        self.prev_sent = psutil.net_io_counters().bytes_sent/100000

    def monitor_events(self) -> None:
        self.logger.check_logging_interval()
        cur_read = psutil.disk_io_counters().read_bytes/100000
        cur_write = psutil.disk_io_counters().write_bytes/100000
        cur_rec = psutil.net_io_counters().bytes_recv/100000
        cur_sent = psutil.net_io_counters().bytes_sent/100000

        log_entry = (
            f"timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} | "
            f"hostname: {self.hostname} | event: system check | "
            f"cpu_usage: {psutil.cpu_percent()}% | cpu_freq: {round(psutil.cpu_freq().current, 2)}Hz | ram_usage: {psutil.virtual_memory().percent}% | "
            f"disk_read: {round((cur_read - self.prev_read)/10, 2)} MB/s | disk_write: {round((cur_write - self.prev_write)/10, 2)} MB/s | "
            f"network_received: {round((cur_rec - self.prev_rec)/10, 2)} MB/s | network_sent: {round((cur_sent - self.prev_sent)/10, 2)} MB/s | "
            f"process_count: {len(psutil.pids())} | sid: {self.sid}"
        )
        self.logger.write_log(log_entry)
        self.prev_read, self.prev_write, self.prev_rec, self.prev_sent = cur_read, cur_write, cur_rec, cur_sent
        if int(time.time()) % 10 == 0:
            self.logger.write_debug_log(f'timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} | '
                                f'hostname: {self.hostname} | source: system | platform: windows | event: progress | '
                                f'message: {self.logger.log_line_count} log lines written | value: {self.logger.log_line_count}')

if __name__ == "__main__":
    system = WindowsSystemLogger()
    while True:
        system.monitor_events()
        time.sleep(system.interval)
