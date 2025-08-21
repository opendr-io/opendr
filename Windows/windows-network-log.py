import os
from datetime import datetime
import psutil
import time
import logging
import ipaddress
import common.attributes as attr
from common.logger import LoggingModule
from typing import NoReturn

# Retrieve system details once
sid: str = attr.get_computer_sid()
hostname: str = attr.get_hostname()

def log_connection(logger: LoggingModule, event: str, conn) -> None:
    """Logs a network connection event (created/terminated/existing)."""
    process_name: str = attr.get_process_name(conn.pid)

    # Get remote address
    remote_ip = conn.raddr[0] if conn.raddr else "N/A"
    remote_port = conn.raddr[1] if conn.raddr else "N/A"

    # Get username if possible
    username: str
    try:
        username = psutil.Process(conn.pid).username()
    except (psutil.NoSuchProcess, psutil.AccessDenied):
        username = "N/A"

    logger.write_log(
        f"timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} | "
        f"hostname: {hostname} | username: {username} | "
        f"category: {event} | process: {process_name} | processid: {conn.pid} | "
        f"sourceip: {conn.laddr[0]} | sourceport: {conn.laddr[1]} | "
        f"destinationip: {remote_ip} | destinationport: {remote_port} | "
        f"status: {conn.status} | sid: {sid}"
    )

def log_initial_connections(logger: LoggingModule) -> dict:
  """Log all currently active connections before starting real-time monitoring."""
  logger.check_logging_interval()

  try:
    connections = psutil.net_connections(kind='inet')
  except Exception as e:
    logging.error(f"Error retrieving existing network connections: {e}")
    return {}

  initial_connections = {}

  for conn in connections:
    if conn.laddr and conn.laddr[0] in ("127.0.0.1", "::1", "::", "0.0.0.0", "::127.0.0.1"):
      continue
    if conn.raddr and ipaddress.ip_address(conn.raddr[0]).is_private:
      continue

    key = (conn.pid, conn.laddr, conn.raddr, conn.status)
    initial_connections[key] = conn
    
    log_connection(logger, " network_existing", conn)
  return initial_connections  # Return initial snapshot for comparison in monitoring

def monitor_network_connections(logger: LoggingModule, interval: float) -> NoReturn:
  """Continuously monitor new and terminated connections, rotating logs every minute."""
  previous_connections = log_initial_connections(logger)  # Log all existing connections first
  
  while True:
    logger.check_logging_interval()

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
      log_connection(logger, "network_connection", current_connections[key])

    for key in terminated_keys:
      log_connection(logger, "network_termination", previous_connections[key])

    if int(time.time()) % 10 == 0:
      logger.write_debug_log(f'timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} | '
                      f'hostname: {hostname} | source: network | platform: windows | event: progress | '
                      f'message: {logger.log_line_count} log lines written | value: {logger.log_line_count}')

    previous_connections = current_connections.copy()
    time.sleep(interval)

def run() -> NoReturn:
  log_directory: str = 'tmp-network' if attr.get_config_value('General', 'RunDatabaseOperations', False, 'bool') else 'tmp'
  ready_directory: str = 'ready'
  debug_generator_directory: str = 'debuggeneratorlogs'
  os.makedirs(log_directory, exist_ok=True)
  os.makedirs(ready_directory, exist_ok=True)
  os.makedirs(debug_generator_directory, exist_ok=True)

  interval = attr.get_config_value('Windows', 'NetworkInterval', 0.1, 'float')
  logger: LoggingModule  = LoggingModule(log_directory, ready_directory, "NetworkMonitor", "network")
  monitor_network_connections(logger, interval)

run()