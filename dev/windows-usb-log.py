import time
import os
from threading import Thread
from datetime import datetime
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
import psutil
import ctypes
import common.attributes as attr
from common.logger import LoggingModule


class WindowsUsbLogger(attr.LoggerParent):
    def __init__(self):
        super().__init__()
        self.interval: float = attr.get_config_value('Windows', 'UsbInterval', 1.0, 'float')
        self.logger = None
        self.previous_drives: set = set()
        self.observers: dict = {}
        self.setup_logger()
        self.log_existing()
        print('WindowsUsbLogger Initialization complete')

    def setup_logger(self) -> None:
        log_directory: str = 'tmp-user-info' if attr.get_config_value('General', 'RunDatabaseOperations', False, 'bool') else 'tmp'
        ready_directory: str = 'ready'
        debug_generator_directory: str = 'debuggeneratorlogs'
        os.makedirs(debug_generator_directory, exist_ok=True)
        os.makedirs(log_directory, exist_ok=True)
        os.makedirs(ready_directory, exist_ok=True)
        self.logger: LoggingModule = LoggingModule(log_directory, ready_directory, "USBMonitor", "usb")
        
    class USBFileLogger(FileSystemEventHandler, attr.LoggerParent):
        def __init__(self, logger):
            super().__init__()
            self.logger: LoggingModule = logger

        def on_created(self, event):
            self.logger.write_log(f"timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} | "
                            f"hostname: {self.hostname} | event: file created | "
                            f"filepath: {event.src_path} | sid: {self.sid}")

        def on_deleted(self, event):
            self.logger.write_log(f"timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} | "
                            f"hostname: {self.hostname} | event: file deleted | "
                            f"filepath: {event.src_path} | sid: {self.sid}")

        def on_modified(self, event):
            self.logger.write_log(f"timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} | "
                            f"hostname: {self.hostname} | event: file modified | "
                            f"filepath: {event.src_path} | sid: {self.sid}")

        def on_moved(self, event):
            self.logger.write_log(f"timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} | "
                            f"hostname: {self.hostname} | event: file moved to {event.dest_path} | "
                            f"filepath: {event.src_path} | sid: {self.sid}")

    @staticmethod
    def get_drive_type(path):
        DRIVE_REMOVABLE = 2
        return ctypes.windll.kernel32.GetDriveTypeW(ctypes.c_wchar_p(path)) == DRIVE_REMOVABLE

    def get_usb_drives(self):
        usb_drives = []
        for part in psutil.disk_partitions(all=False):
            if self.get_drive_type(part.device):
                usb_drives.append(part.device)
        return usb_drives

    def start_usb_watchdog(self, drive):
        if drive in self.observers:
            print(f"[!] Already monitoring {drive}")
            return
        observer = Observer()
        event_handler = self.USBFileLogger(self.logger)
        observer.schedule(event_handler, path=drive, recursive=True)
        observer.start()
        self.observers[drive] = observer
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            observer.stop()
        observer.join()
        
    def log_existing(self):
        self.previous_drives = self.get_usb_drives()
        for drive in self.previous_drives:
            self.logger.write_log(f"timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} | "
                            f"hostname: {self.hostname} | event: usb detected | "
                            f"filepath: {drive} | sid: {self.sid}")
            Thread(target=self.start_usb_watchdog, args=(drive,), daemon=True).start()

    def monitor_events(self):
        self.logger.check_logging_interval()
        current_drives = self.get_usb_drives()
        inserted_drives = set(current_drives) - set(self.previous_drives)
        
        for drive in inserted_drives:
            self.logger.write_log(f"timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} | "
                        f"hostname: {self.hostname} | event: usb inserted | "
                        f"filepath: {drive} | sid: {self.sid}")
            Thread(target=self.start_usb_watchdog, args=(drive,), daemon=True).start()
        
        removed_drives = set(self.previous_drives) - set(current_drives)
        for drive in removed_drives:
            observer = self.observers.pop(drive, None)
            observer.stop()
            observer.join()
            self.logger.write_log(f"timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} | "
                        f"hostname: {self.hostname} | event: usb removed | "
                        f"filepath: {drive} | sid: {self.sid}")

        self.previous_drives = current_drives

if __name__ == '__main__':
    usb = WindowsUsbLogger()
    while True:
        usb.monitor_events()
        time.sleep(usb.interval)