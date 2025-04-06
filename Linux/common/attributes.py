import socket
import requests
import psutil
#import win32security
import os

def get_hostname() -> str:
    return socket.gethostname()

# Gets the Windows host SID
# def get_computer_sid() -> str:
#     return win32security.ConvertSidToStringSid(
#         win32security.GetFileSecurity(
#         os.environ['SYSTEMROOT'], win32security.OWNER_SECURITY_INFORMATION
#         ).GetSecurityDescriptorOwner()
#     )

def get_ec2_instance_id() -> str:
    try:
        response: requests.Response = requests.get("http://169.254.169.254/latest/meta-data/instance-id", timeout=2)
        return response.text
    except requests.RequestException:
        return "No instance ID"

def get_public_ip() -> str:
    try:
        response: requests.Response = requests.get("https://api64.ipify.org?format=text", timeout=5)
        return response.text
    except requests.RequestException:
        return "Unavailable"

def get_private_ips() -> list[str]:
    return [addr.address for _, addr_list in psutil.net_if_addrs().items()
            for addr in addr_list if addr.family == socket.AF_INET]

def get_process_name(pid: int) -> str:
    """Return the process name for the given PID, or a fallback string."""
    if pid is None:
        return "N/A"
    try:
        return psutil.Process(pid).name()
    except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
        return "Unknown"

# Gets the Linux system UUID from the DMI product_uuid or systemd machine-id
def get_system_uuid() -> dict[str, str]:
    primary_path = "/sys/class/dmi/id/product_uuid"
    fallback_path = "/etc/machine-id"
    try:
        with open(primary_path, "r") as f:
            uuid = f.read().strip()
            if uuid and uuid != "00000000-0000-0000-0000-000000000000":
                return {
                    "uuid": uuid,
                    "source": "DMI product_uuid (/sys/class/dmi/id/product_uuid)"
                }
    except FileNotFoundError:
        pass
    try:
        with open(fallback_path, "r") as f:
            return {
                "uuid": f.read().strip(),
                "source": "systemd machine-id (/etc/machine-id)"
            }
    except FileNotFoundError:
        return {
            "uuid": None,
            "source": "UUID not found in either path"
        }