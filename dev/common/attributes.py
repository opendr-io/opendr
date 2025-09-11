import socket
import requests
import subprocess
import psutil
import win32security
import os
import configparser
import pathlib
import concurrent.futures
from ipwhois import IPWhois
from ipwhois.exceptions import IPDefinedError

config = configparser.ConfigParser()
config.read(pathlib.Path(__file__).parent.absolute() / "../../agentconfig.ini")

def get_hostname() -> str:
    return socket.gethostname()

def get_computer_sid() -> str:
    return win32security.ConvertSidToStringSid(
        win32security.GetFileSecurity(
        os.environ['SYSTEMROOT'], win32security.OWNER_SECURITY_INFORMATION
        ).GetSecurityDescriptorOwner()
    )

def get_mac_computer_uuid() -> str:
    """
    Retrieves the hardware UUID of a macOS machine.
    """
    try:
        # Command to get the IOPlatformUUID
        command = "ioreg -d2 -c IOPlatformExpertDevice | awk -F\\\" '/IOPlatformUUID/{print $(NF-1)}'"
        
        # Execute the command and capture the output
        uuid_output = subprocess.check_output(command, shell=True, text=True).strip()
        
        return uuid_output
    except subprocess.CalledProcessError:
        # This handles cases where the command fails
        print("Error: Failed to execute ioreg command.")
        return None
    except FileNotFoundError:
        # This handles cases where ioreg might not be available
        print("Error: 'ioreg' command not found. This script is intended for macOS.")
        return None

# Gets the Linux system UUID from the DMI product_uuid or systemd machine-id
def get_system_uuid():
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

def get_dns_name(ip):
    """Perform a non-blocking reverse DNS lookup."""
    with concurrent.futures.ThreadPoolExecutor() as executor:
        future = executor.submit(socket.gethostbyaddr, ip)
        try:
            return future.result(timeout=2)[0]  # Timeout after 2 seconds
        except (socket.herror, socket.gaierror, concurrent.futures.TimeoutError):
            return 'none'  # Populate 'none' if DNS lookup fails

def get_as_name(ip):
    """Perform an AS (Autonomous System) lookup if DNS resolution fails."""
    try:
        obj = IPWhois(ip)
        result = obj.lookup_rdap(depth=1)
        return result.get("asn_description", "Unknown ASN")
    except IPDefinedError:
        return "Private IP"
    except Exception:
        return "Unknown ASN"

class LoggerParent():
    def __init__(self):
        self.sid: str = ''
        match config.get('General', 'OperatingSystem', fallback='Windows'):
            case "Windows":
                self.sid = get_computer_sid() or ''
            case "MacOS":
                self.sid = get_mac_computer_uuid() or ''
            case "Linux":
                self.sid = get_system_uuid() or ''
            case _:
                self.sid = get_computer_sid() or ''
        self.hostname: str = get_hostname()
        self.ec2_instance_id: str = get_ec2_instance_id() or ''
        self.logger = None

    def setup_logger(self) -> None:
        print("setup_logger not created")
    
    def log_existing(self) -> None:
        print("log_existing not created")
    
    def monitor_events(self) -> None:
        print("monitor_events not created")
