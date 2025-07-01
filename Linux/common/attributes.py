import socket
import requests
import psutil
#import win32security
import os
import configparser
import pathlib
import subprocess

config = configparser.ConfigParser()
config.read(pathlib.Path(__file__).parent.absolute() / "../../agentconfig.ini")

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

# List all services and their statuses on a linux machine
def get_all_service_statuses() -> list:
    try:
        output = subprocess.check_output(
            ['systemctl', 'list-units', '--type=service', '--no-pager', '--no-legend'],
            stderr=subprocess.DEVNULL
        ).decode('utf-8')

        services = []
        for line in output.strip().split('\n'):
            if line:
                parts = line.split(None, 4)
                service_name = parts[0]
                load_state = parts[1]
                active_state = parts[2]
                sub_state = parts[3]
                description = parts[4] if len(parts) > 4 else ''
                services.append({
                    'name': service_name,
                    'load_state': load_state,
                    'active_state': active_state,
                    'sub_state': sub_state,
                    'description': description
                })
        return services
    except subprocess.CalledProcessError:
        return []

def get_config_value(section: str, key: str, default, type: str='str'):
    match type:
        case 'str':
            return config.get(section, key, fallback=default)
        case 'int':
            return config.getint(section, key, fallback=default)
        case 'float':
            return config.getfloat(section, key, fallback=default)
        case 'bool':
            return config.getboolean(section, key, fallback=default)
        case _:
            return config.get(section, key, fallback=default)