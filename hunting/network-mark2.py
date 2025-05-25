import os
from datetime import datetime
import psutil
import time
import logging
import ipaddress
import socket
import concurrent.futures
from ipwhois import IPWhois
from ipwhois.exceptions import IPDefinedError

# Set up logging directory
log_directory = 'logs'
os.makedirs(log_directory, exist_ok=True)

def get_log_filename():
    """Generate a log filename with the current timestamp (new file every minute)."""
    return os.path.join(log_directory, f"network_{datetime.now().strftime('%Y%m%d_%H%M')}.log")

def setup_logging():
    """Set up logging with the new filename."""
    logging.basicConfig(
        filename=get_log_filename(),
        level=logging.INFO,
        format='%(message)s',
        force=True  # Forces reconfiguration of logging
    )

# Get hostname once
hostname = socket.gethostname()

def get_process_name(pid):
    """Return the process name for the given PID, or a fallback string."""
    if pid is None:
        return "N/A"
    try:
        return psutil.Process(pid).name()
    except (psutil.NoSuchProcess, psutil.AccessDenied):
        return "Unknown"

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

def get_resolved_name(ip):
    """Attempt to resolve DNS first, then fallback to AS lookup."""
    dns_name = get_dns_name(ip)
    as_name = 'skipped-dns' if dns_name != 'none' else get_as_name(ip)
    return dns_name, as_name 

def monitor_network_connections(interval):
    setup_logging()  # Initialize logging
    logging.info(f"Monitoring network connections at an interval of {interval} seconds...")

    previous_connections = {}
    current_minute = datetime.now().minute  # Track current minute

    while True:
        # Rotate log file every minute
        if datetime.now().minute != current_minute:
            setup_logging()
            current_minute = datetime.now().minute

        current_connections = {}
        try:
            connections = psutil.net_connections(kind='inet')
        except Exception as e:
            logging.error(f"Error retrieving network connections: {e}")
            time.sleep(interval)
            continue

        for conn in connections:
            # Skip loopback and unspecified addresses
            if conn.laddr and conn.laddr[0] in ("127.0.0.1", "::1", "::", "0.0.0.0"):
                continue

            # Skip private IPs (only log internet traffic)
            if conn.raddr:
                remote_ip = conn.raddr[0]
                try:
                    if ipaddress.ip_address(remote_ip).is_private:
                        continue
                except ValueError:
                    continue
            else:
                continue  # Skip connections with no remote address

            key = (conn.pid, conn.laddr, conn.raddr, conn.status)
            current_connections[key] = conn

        created_keys = set(current_connections) - set(previous_connections)
        terminated_keys = set(previous_connections) - set(current_connections)

        # Log new connections
        for key in created_keys:
            conn = current_connections[key]
            process_name = get_process_name(conn.pid)
            remote_dns, as_name = get_resolved_name(conn.raddr[0])

            logging.info(
                f"timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} - "
                f"Hostname: {hostname}, event: connection created, "
                f"pid: {conn.pid}, process: {process_name}, "
                f"dnsname: {remote_dns}, "
                f"sourceip: {conn.laddr[0]}, sourceport: {conn.laddr[1]}, "
                f"destip: {conn.raddr[0]}, destport: {conn.raddr[1]}, "
                f"asname: {as_name}, status: {conn.status} "
            )

        # Efficiently update previous_connections
        previous_connections.clear()
        previous_connections.update(current_connections)

        time.sleep(interval)

if __name__ == '__main__':    
    monitor_network_connections(0.1)

