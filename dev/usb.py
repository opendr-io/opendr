import win32file
import win32api
import win32con

def get_usb_drives():
    drives = win32api.GetLogicalDriveStrings().split('\000')[:-1]
    usb_drives = []

    for drive in drives:
        drive_type = win32file.GetDriveType(drive)
        if drive_type == win32file.DRIVE_REMOVABLE:
            # Exclude floppy drives (A:\, B:\)
            if not drive.startswith(('A:', 'B:')):
                usb_drives.append(drive)

    return usb_drives

if __name__ == "__main__":
    print("USB drives found:", get_usb_drives())
