import wmi
import win32file
import win32api
import time
from threading import Thread
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

class USBFileLogger(FileSystemEventHandler):
    def on_created(self, event):
        print(f"[CREATED] {event.src_path}")

    def on_deleted(self, event):
        print(f"[DELETED] {event.src_path}")

    def on_modified(self, event):
        print(f"[MODIFIED] {event.src_path}")

    def on_moved(self, event):
        print(f"[RENAMED] {event.src_path} -> {event.dest_path}")

def get_usb_drives():
    drives = win32api.GetLogicalDriveStrings().split('\000')[:-1]
    return [
        d for d in drives
        if win32file.GetDriveType(d) == win32file.DRIVE_REMOVABLE and not d.startswith(('A:', 'B:'))
    ]

def monitor_usb(drive):
    print(f"[MONITORING] {drive}")
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

    print("[WAITING FOR USB]")
    while True:
        event = watcher()
        print("[USB INSERTED] Event detected")
        time.sleep(1)  # allow mount time

        usb_drives = get_usb_drives()
        for drive in usb_drives:
            Thread(target=monitor_usb, args=(drive,), daemon=True).start()

if __name__ == "__main__":
    watch_usb_events()
