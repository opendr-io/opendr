import os
from datetime import datetime
import psutil
import time
import logging
import ipaddress
import common.attributes as attr
from common.logger import check_logging_interval, enter_debug_logs
from typing import NoReturn

# Global counter for log lines written
log_line_count: int = 0

# Retrieve system details once
sid: str = attr.get_computer_sid()
hostname: str = attr.get_hostname()

def log_connection(logger: logging.Logger, event: str, conn) -> None:
    """Logs a network connection event (created/terminated/existing)."""
    process_name: str = attr.get_process_name(conn.pid)
    global log_line_count

    # Get remote address
    remote_ip = conn.raddr[0] if conn.raddr else "N/A"
    remote_port = conn.raddr[1] if conn.raddr else "N/A"

    # Get username if possible
    username: str
    try:
        username = psutil.Process(conn.pid).username()
    except (psutil.NoSuchProcess, psutil.AccessDenied):
        username = "N/A"

    logger.info(
        f"timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} | "
        f"hostname: {hostname} |  username: {username}  | "
        f"event: {event} | name: {process_name} | pid: {conn.pid} | "
        f"sourceip: {conn.laddr[0]} | sourceport: {conn.laddr[1]} | "
        f"destip: {remote_ip} | destport: {remote_port} | "
        f"status: {conn.status} | sid: {sid}"
    )

    log_line_count += 1

def log_initial_connections(log_directory: str, ready_directory: str) -> tuple[dict, logging.Logger, int]:
  """Log all currently active connections before starting real-time monitoring."""
  logger, last_interval  = check_logging_interval(log_directory, ready_directory, "NetworkMonitor", "network", None, None)

  try:
    connections = psutil.net_connections(kind='inet')
  except Exception as e:
    logging.error(f"Error retrieving existing network connections: {e}")
    return {}, logger, last_interval

  initial_connections = {}

  for conn in connections:
    if conn.laddr and conn.laddr[0] in ("127.0.0.1", "::1", "::", "0.0.0.0", "::127.0.0.1"):
      continue
    if conn.raddr and ipaddress.ip_address(conn.raddr[0]).is_private:
      continue

    key = (conn.pid, conn.laddr, conn.raddr, conn.status)
    initial_connections[key] = conn
    
    log_connection(logger, "existing connection", conn)
  return initial_connections, logger, last_interval   # Return initial snapshot for comparison in monitoring

def monitor_network_connections(log_directory: str, ready_directory: str, interval: float) -> NoReturn:
  """Continuously monitor new and terminated connections, rotating logs every minute."""
  previous_connections, logger, last_interval  = log_initial_connections(log_directory, ready_directory)  # Log all existing connections first
  
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

def run() -> NoReturn:
  log_directory: str = 'tmp-network' if attr.get_config_value('Windows', 'RunDatabaseOperations', False, 'bool') else 'tmp'
  ready_directory: str = 'ready'
  os.makedirs(log_directory, exist_ok=True)
  os.makedirs(ready_directory, exist_ok=True)

  interval = attr.get_config_value('Windows', 'NetworkInterval', 0.1, 'float')
  monitor_network_connections(log_directory, ready_directory, interval)


run()