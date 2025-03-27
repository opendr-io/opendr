import socket
import requests
import psutil
import win32security
import os

def get_hostname() -> str:
    return socket.gethostname()

def get_computer_sid() -> str:
    return win32security.ConvertSidToStringSid(
        win32security.GetFileSecurity(
        os.environ['SYSTEMROOT'], win32security.OWNER_SECURITY_INFORMATION
        ).GetSecurityDescriptorOwner()
    )

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
