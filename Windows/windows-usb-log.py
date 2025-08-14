import wmi
import win32file
import win32api
import time
import os
from threading import Thread
from datetime import datetime
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
import common.attributes as attr
from common.logger import LoggingModule

logger: LoggingModule = None
hostname: str = attr.get_hostname()
computer_sid: str = attr.get_computer_sid()

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

def get_usb_drives():
    drives = win32api.GetLogicalDriveStrings().split('\000')[:-1]
    return [
        d for d in drives
        if win32file.GetDriveType(d) == win32file.DRIVE_REMOVABLE and not d.startswith(('A:', 'B:'))
    ]

def monitor_usb(drive):
    logger.write_log(f"[MONITORING] {drive}")
    observer = Observer()
    event_handler = USBFileLogger()
    observer.schedule(event_handler, path=drive, recursive=True)
    observer.start()
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        observer.stop()
    observer.join()

def watch_usb_events():
    c = wmi.WMI()
    watcher = c.Win32_VolumeChangeEvent.watch_for(notification_type="Creation")

    logger.write_log("[WAITING FOR USB]")
    while True:
        event = watcher()
        logger.write_log("[USB INSERTED] Event detected")
        time.sleep(1)  # allow mount time

        usb_drives = get_usb_drives()
        for drive in usb_drives:
            Thread(target=monitor_usb, args=(drive,), daemon=True).start()

if __name__ == "__main__":
    # interval = attr.get_config_value('Windows', 'UsbInterval', 1.0, 'float')
    log_directory = 'tmp-user-info' if attr.get_config_value('General', 'RunDatabaseOperations', False, 'bool') else 'tmp'
    ready_directory = 'ready'
    debug_generator_directory = 'debuggeneratorlogs'
    os.makedirs(debug_generator_directory, exist_ok=True)
    os.makedirs(log_directory, exist_ok=True)
    os.makedirs(ready_directory, exist_ok=True)
    logger = LoggingModule(log_directory, ready_directory, "USBMonitor", "usb")
    watch_usb_events()
