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

logger: LoggingModule = None
hostname: str = attr.get_hostname()
computer_sid: str = attr.get_computer_sid()
observers = {}

class USBFileLogger(FileSystemEventHandler):
    def on_created(self, event):
        logger.write_log(f"timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} | "
                        f"hostname: {hostname} | event: file created | "
                        f"filepath: {event.src_path} | sid: {computer_sid}")

    def on_deleted(self, event):
        logger.write_log(f"timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} | "
                        f"hostname: {hostname} | event: file deleted | "
                        f"filepath: {event.src_path} | sid: {computer_sid}")

    def on_modified(self, event):
        logger.write_log(f"timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} | "
                        f"hostname: {hostname} | event: file modified | "
                        f"filepath: {event.src_path} | sid: {computer_sid}")

    def on_moved(self, event):
        logger.write_log(f"timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} | "
                        f"hostname: {hostname} | event: file moved to {event.dest_path} | "
                        f"filepath: {event.src_path} | sid: {computer_sid}")

def get_drive_type(path):
    DRIVE_REMOVABLE = 2
    return ctypes.windll.kernel32.GetDriveTypeW(ctypes.c_wchar_p(path)) == DRIVE_REMOVABLE

def get_usb_drives():
    usb_drives = []
    for part in psutil.disk_partitions(all=False):
        if get_drive_type(part.device):
            usb_drives.append(part.device)
    return usb_drives

def start_usb_watchdog(drive):
    if drive in observers:
        print(f"[!] Already monitoring {drive}")
        return
    observer = Observer()
    event_handler = USBFileLogger()
    observer.schedule(event_handler, path=drive, recursive=True)
    observer.start()
    observers[drive] = observer
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        observer.stop()
    observer.join()

def watch_usb_events():
    interval = attr.get_config_value('Windows', 'UsbInterval', 1.0, 'float')
    previous_drives = get_usb_drives()
    for drive in previous_drives:
        logger.write_log(f"timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} | "
                        f"hostname: {hostname} | event: usb detected | "
                        f"filepath: {drive} | sid: {computer_sid}")
        Thread(target=start_usb_watchdog, args=(drive,), daemon=True).start()

    while True:
        logger.check_logging_interval()
        current_drives = get_usb_drives()
        inserted_drives = set(current_drives) - set(previous_drives)
        
        for drive in inserted_drives:
            logger.write_log(f"timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} | "
                        f"hostname: {hostname} | event: usb inserted | "
                        f"filepath: {drive} | sid: {computer_sid}")
            Thread(target=start_usb_watchdog, args=(drive,), daemon=True).start()
        
        removed_drives = set(previous_drives) - set(current_drives)
        for drive in removed_drives:
            observer = observers.pop(drive, None)
            observer.stop()
            observer.join()
            logger.write_log(f"timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} | "
                        f"hostname: {hostname} | event: usb removed | "
                        f"filepath: {drive} | sid: {computer_sid}")

        previous_drives = current_drives
        time.sleep(interval)

if __name__ == "__main__":
    log_directory = 'tmp-user-info' if attr.get_config_value('General', 'RunDatabaseOperations', False, 'bool') else 'tmp'
    ready_directory = 'ready'
    debug_generator_directory = 'debuggeneratorlogs'
    os.makedirs(debug_generator_directory, exist_ok=True)
    os.makedirs(log_directory, exist_ok=True)
    os.makedirs(ready_directory, exist_ok=True)
    logger = LoggingModule(log_directory, ready_directory, "USBMonitor", "usb")
    watch_usb_events()
