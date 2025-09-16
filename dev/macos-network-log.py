import os
from datetime import datetime
import psutil
import time
import logging
import ipaddress
from typing import NoReturn
import common.attributes as attr
from common.logger import LoggingModule

class MacOSNetworkLogger(attr.LoggerParent):
  def __init__(self):
    super().__init__()
    self.interval: float = attr.get_config_value('MacOS', 'NetworkInterval', 0.1, 'float')
    self.previous_connections: dict = {}
    self.setup_logger()
    self.log_existing()
    print('MacOSNetworkLogger Initialization complete')

  def setup_logger(self) -> None:
    log_directory: str = 'tmp-network' if attr.get_config_value('General', 'RunDatabaseOperations', False, 'bool') else 'tmp'
    ready_directory: str = 'ready'
    debug_generator_directory: str = 'debuggeneratorlogs'
    os.makedirs(debug_generator_directory, exist_ok=True)
    os.makedirs(log_directory, exist_ok=True)
    os.makedirs(ready_directory, exist_ok=True)
    self.logger: LoggingModule  = LoggingModule(log_directory, ready_directory, "NetworkMonitor", "network")

  def log_connection(self, event: str, conn) -> None:
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

    self.logger.write_log(
        f"timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} | "
        f"hostname: {self.hostname} | username: {username} | "
        f"category: {event} | process: {process_name} | processid: {conn.pid} | "
        f"sourceip: {conn.laddr[0]} | sourceport: {conn.laddr[1]} | "
        f"destinationip: {remote_ip} | destinationport: {remote_port} | "
        f"status: {conn.status} | uuid: {self.sid}"
    )

  def log_existing(self) -> None:
    """Log all currently active connections before starting real-time monitoring."""
    self.logger.check_logging_interval()

    try:
      connections = psutil.net_connections(kind='inet')
    except Exception as e:
      logging.error(f"Error retrieving existing network connections: {e}")
      return {}

    for conn in connections:
      if conn.laddr and conn.laddr[0] in ("127.0.0.1", "::1", "::", "0.0.0.0", "::127.0.0.1"):
        continue
      if conn.raddr and ipaddress.ip_address(conn.raddr[0]).is_private:
        continue

      key = (conn.pid, conn.laddr, conn.raddr, conn.status)
      self.previous_connections[key] = conn

      self.log_connection("network_existing", conn)

  def monitor_events(self) -> None:
    """Continuously monitor new and terminated connections, rotating logs every minute."""
    self.logger.check_logging_interval()

    current_connections = {}
    try:
      connections = psutil.net_connections(kind='inet')
    except Exception as e:
      logging.error(f"Error retrieving network connections: {e}")
      return

    for conn in connections:
      if conn.laddr and conn.laddr[0] in ("127.0.0.1", "::1", "::", "0.0.0.0"):
        continue
      if conn.raddr and ipaddress.ip_address(conn.raddr[0]).is_private:
        continue

      key = (conn.pid, conn.laddr, conn.raddr, conn.status)
      current_connections[key] = conn

    created_keys = set(current_connections.keys()) - set(self.previous_connections.keys())
    terminated_keys = set(self.previous_connections.keys()) - set(current_connections.keys())

    for key in created_keys:
      self.log_connection("network_connection", current_connections[key])

    for key in terminated_keys:
      self.log_connection("network_termination", self.previous_connections[key])

    if int(time.time()) % 10 == 0:
      self.logger.write_debug_log(f"timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} | "
                      f"hostname: {self.hostname} | source: network | platform: macos | event: progress | "
                      f"message: {self.logger.log_line_count} log lines written | value: {self.logger.log_line_count}")

    self.previous_connections = current_connections.copy()

if __name__ == '__main__':
    network = MacOSNetworkLogger()
    while True:
        network.monitor_events()
        time.sleep(network.interval)
