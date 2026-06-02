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

def get_process_details(pid: int|None) -> dict:
    if pid is None:
        return {
            'process_name': 'N/A',
            'username': 'N/A',
            'creation_time': 'N/A',
        }

    try:
        proc = psutil.Process(pid)
        return {
            'process_name': proc.name(),
            'username': proc.username(),
            'creation_time': proc.create_time(),
        }
    except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
        return {
            'process_name': 'Unknown',
            'username': 'N/A',
            'creation_time': 'N/A',
        }

def format_creation_time(creation_time) -> str:
    if creation_time == 'N/A':
        return 'N/A'
    return datetime.fromtimestamp(creation_time).strftime('%Y-%m-%d %H:%M:%S.%f')

def build_connection_snapshot(conn) -> tuple[tuple, dict]:
    process_details = get_process_details(conn.pid)
    remote_ip = conn.raddr[0] if conn.raddr else "N/A"
    remote_port = conn.raddr[1] if conn.raddr else "N/A"

    data = {
        'pid': conn.pid,
        'process_name': process_details['process_name'],
        'username': process_details['username'],
        'creation_time': process_details['creation_time'],
        'source_ip': conn.laddr[0],
        'source_port': conn.laddr[1],
        'destination_ip': remote_ip,
        'destination_port': remote_port,
        'status': conn.status,
    }
    key = (
        conn.pid,
        process_details['creation_time'],
        conn.laddr,
        conn.raddr,
        conn.status,
    )
    return key, data

def log_connection(logger: LoggingModule, event: str, conn_info: dict) -> None:
    """Logs a network connection event (created/terminated/existing)."""
    logger.write_log(
        f"timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} | "
        f"hostname: {hostname} | username: {conn_info['username']} | "
        f"category: {event} | process: {conn_info['process_name']} | processid: {conn_info['pid']} | "
        f"creationtime: {format_creation_time(conn_info['creation_time'])} | "
        f"sourceip: {conn_info['source_ip']} | sourceport: {conn_info['source_port']} | "
        f"destinationip: {conn_info['destination_ip']} | destinationport: {conn_info['destination_port']} | "
        f"status: {conn_info['status']} | sid: {sid}"
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

    key, conn_info = build_connection_snapshot(conn)
    initial_connections[key] = conn_info

    log_connection(logger, "network_existing", conn_info)
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

      key, conn_info = build_connection_snapshot(conn)
      current_connections[key] = conn_info

    created_keys = set(current_connections.keys()) - set(previous_connections.keys())
    terminated_keys = set(previous_connections.keys()) - set(current_connections.keys())

    for key in created_keys:
      log_connection(logger, "network_connection", current_connections[key])

    for key in terminated_keys:
      log_connection(logger, "network_termination", previous_connections[key])

    if int(time.time()) % 10 == 0:
      logger.write_debug_log(f"timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} | "
                      f"hostname: {hostname} | source: network | platform: windows | event: progress | "
                      f"message: {logger.log_line_count} log lines written | value: {logger.log_line_count}")

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
