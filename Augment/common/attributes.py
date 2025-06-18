import socket
import socket
import concurrent.futures
from ipwhois import IPWhois
from ipwhois.exceptions import IPDefinedError
import configparser
import pathlib

config = configparser.ConfigParser()
config.read(pathlib.Path(__file__).parent.absolute() / "../../agentconfig.ini")

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