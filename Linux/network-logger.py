import os
from datetime import datetime
import psutil
import time
import logging
import ipaddress
import common.attributes as attr
from common.logger import check_logging_interval, enter_debug_logs, move_existing_temp_files

# Global counter for log lines written
log_line_count = 0

# Retrieve system details once
#sid = attr.get_computer_sid()
uuid = attr.get_system_uuid()
hostname = attr.get_hostname()

def log_connection(logger, event, conn):
    """Logs a network connection event (created/terminated/existing)."""
    process_name = attr.get_process_name(conn.pid)
    global log_line_count

    # Get remote address
    remote_ip = conn.raddr[0] if conn.raddr else "N/A"
    remote_port = conn.raddr[1] if conn.raddr else "N/A"

    # Get username if possible
    try:
        username = psutil.Process(conn.pid).username()
    except (psutil.NoSuchProcess, psutil.AccessDenied):
        username = "N/A"

    logger.info(
        f"timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} | "
        f"hostname: {hostname} |  username: {username}  | "
        f"event: {event} | process: {process_name}   pid: {conn.pid} | "       
        f"sourceip: {conn.laddr[0]} | sourceport: {conn.laddr[1]} | "
        f"destip: {remote_ip} | destport: {remote_port} | "
        f"status: {conn.status} | uuid: {uuid}"
    )

    log_line_count += 1

def log_initial_connections(log_directory, ready_directory):
  """Log all currently active connections before starting real-time monitoring."""
  logger, last_interval = check_logging_interval(log_directory, ready_directory, "NetworkMonitor", "network", None, None)

  try:
    connections = psutil.net_connections(kind='inet')
  except Exception as e:
    logging.error(f"Error retrieving existing network connections: {e}")
    return {}

  initial_connections = {}

  for conn in connections:
    if conn.laddr and conn.laddr[0] in ("127.0.0.1", "::1", "::", "0.0.0.0"):
      continue
    if conn.raddr and ipaddress.ip_address(conn.raddr[0]).is_private:
      continue

    key = (conn.pid, conn.laddr, conn.raddr, conn.status)
    initial_connections[key] = conn
    
    log_connection(logger, "existing connection", conn)
  return initial_connections, logger, last_interval  # Return initial snapshot for comparison in monitoring

def monitor_network_connections(log_directory, ready_directory, interval):
  """Continuously monitor new and terminated connections, rotating logs every minute."""
  previous_connections, logger, last_interval = log_initial_connections(log_directory, ready_directory)  # Log all existing connections first
  
  while True:
    logger, last_interval = check_logging_interval(log_directory, ready_directory, "NetworkMonitor", "network", logger, last_interval)

    current_connections = {}
    try:
      connections = psutil.net_connections(kind='inet')
    except Exception as e:
      logging.error(f"Error retrieving network connections: {e}")
      time.sleep(interval)
      continue

    for conn in connections:
      if conn.laddr and conn.laddr[0] in ("127.0.0.1", "::1", "::", "0.0.0.0"):
        continue
      if conn.raddr and ipaddress.ip_address(conn.raddr[0]).is_private:
        continue

      key = (conn.pid, conn.laddr, conn.raddr, conn.status)
      current_connections[key] = conn

    created_keys = set(current_connections.keys()) - set(previous_connections.keys())
    terminated_keys = set(previous_connections.keys()) - set(current_connections.keys())

    for key in created_keys:
      log_connection(logger, "connection created", current_connections[key])

    for key in terminated_keys:
      log_connection(logger, "connection terminated", previous_connections[key])

    enter_debug_logs('network', f"Running total log lines written: {log_line_count}  \n")
    previous_connections = current_connections.copy()
    
    time.sleep(interval)

def run():
  log_directory = 'tmp-network'
  ready_directory = 'ready'
  os.makedirs(log_directory, exist_ok=True)
  os.makedirs(ready_directory, exist_ok=True)
  move_existing_temp_files(log_directory, ready_directory)
  interval = attr.get_config_value('Linux', 'NetworkInterval', 0.1, 'float')
  monitor_network_connections(log_directory, ready_directory, interval)

run()