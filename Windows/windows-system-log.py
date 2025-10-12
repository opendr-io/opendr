import os
import psutil
from datetime import datetime
import time
import common.attributes as attr
from common.logger import LoggingModule
from typing import NoReturn

hostname: str = attr.get_hostname()
sid: str = attr.get_computer_sid()

def log_installed_software(logger: LoggingModule) -> NoReturn:
    """Logs installed software with system metadata."""
    prev_read = psutil.disk_io_counters().read_bytes/100000
    prev_write = psutil.disk_io_counters().write_bytes/100000
    prev_rec = psutil.net_io_counters().bytes_recv/100000
    prev_sent = psutil.net_io_counters().bytes_sent/100000
    while True:
        logger.check_logging_interval()
        cur_read = psutil.disk_io_counters().read_bytes/100000
        cur_write = psutil.disk_io_counters().write_bytes/100000
        cur_rec = psutil.net_io_counters().bytes_recv/100000
        cur_sent = psutil.net_io_counters().bytes_sent/100000

        log_entry = (
            f"timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} | "
            f"hostname: {hostname} | event: system check | "
            f"cpu_usage: {psutil.cpu_percent()}% | cpu_freq: {round(psutil.cpu_freq().current, 2)}Hz | ram_usage: {psutil.virtual_memory().percent}% | "
            f"disk_read: {round((cur_read - prev_read)/10, 2)} MB/s | disk_write: {round((cur_write - prev_write)/10, 2)} MB/s | "
            f"network_received: {round((cur_rec - prev_rec)/10, 2)} MB/s | network_sent: {round((cur_sent - prev_sent)/10, 2)} MB/s | "
            f"process_count: {len(psutil.pids())} | sid: {sid}"
        )
        logger.write_log(log_entry)
        prev_read, prev_write, prev_rec, prev_sent = cur_read, cur_write, cur_rec, cur_sent
        if int(time.time()) % 10 == 0:
            logger.write_debug_log(f'timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} | '
                                f'hostname: {hostname} | source: system | platform: windows | event: progress | '
                                f'message: {logger.log_line_count} log lines written | value: {logger.log_line_count}')
        time.sleep(10.0)

def run() -> NoReturn:
    log_directory: str = 'tmp-system' if attr.get_config_value('General', 'RunDatabaseOperations', False, 'bool') else 'tmp'
    ready_directory: str = 'ready'
    debug_generator_directory: str = 'debuggeneratorlogs'
    os.makedirs(debug_generator_directory, exist_ok=True)
    os.makedirs(log_directory, exist_ok=True)
    os.makedirs(ready_directory, exist_ok=True)
    logger: LoggingModule  = LoggingModule(log_directory, ready_directory, "SystemMonitor", "system")
    log_installed_software(logger)

run()