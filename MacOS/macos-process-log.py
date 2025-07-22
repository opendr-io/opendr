import os
import psutil
import time
from datetime import datetime
from typing import NoReturn
import common.attributes as attr
from common.logger import LoggingModule

# Global counter for log lines written
log_line_count: int = 0

# Retrieve system details once
uuid = attr.get_mac_computer_uuid()
hostname: str = attr.get_hostname()

def log_existing_processes(logger: LoggingModule):
  """Logs all currently running processes at script startup."""
  #log_message(logger, f"Logging all existing processes at startup on {hostname} with uuid: {uuid}")
  global log_line_count
  for proc in psutil.process_iter(attrs=['pid', 'name', 'exe', 'username', 'cmdline']):
    try:
      proc_info = proc.as_dict(attrs=['pid', 'name', 'username', 'exe', 'cmdline'])
      pid = proc_info.get('pid', 'N/A')
      proc_name: str = proc_info.get('name', 'Unknown')
      user: str = proc_info.get('username', 'N/A')
      cmdline = proc_info.get('cmdline', [])
      cmdline: str = " ".join(cmdline) if cmdline else 'N/A'
      exe: str = proc_info.get('exe', 'N/A')

      # Handle cases where the parent process is None
      parent_pid, parent_name = "N/A", "N/A"
      parent: psutil.Process|None = proc.parent()
      if parent:  # Check if parent is not None
          parent_pid = parent.pid
          parent_name = parent.name()

      logger.write_log(f"timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} | "
          f"hostname: {hostname} | username: {user} | event: existing process | "
          f"pid: {pid} | name: {proc_name} | ppid: {parent_pid} | parent: {parent_name} | "
          f"exe: {exe} | cmdline: {cmdline} | uuid: {uuid}"
        )
      log_line_count += 1
    except (psutil.NoSuchProcess, psutil.AccessDenied):
      continue  # Ignore processes that vanish before logging

def monitor_process_events(logger: LoggingModule, debug_logger: LoggingModule, interval: float) -> NoReturn:
  """Monitors process creation and termination events while tracking log lines written."""
  global log_line_count
  previous_processes = set(psutil.pids())

  # Log all running processes at startup
  log_existing_processes(logger)

  while True:
    # # Check if the minute has changed to rotate the log file
    logger.check_logging_interval()

    current_processes = set(psutil.pids()) 
    created_processes = current_processes - previous_processes
    terminated_processes = previous_processes - current_processes

    # Log created processes
    for pid in created_processes:
      try:
        proc = psutil.Process(pid)
        proc_info = proc.as_dict(attrs=['pid', 'name', 'username', 'exe', 'cmdline'])
        proc_name: str = proc_info.get('name', 'Unknown')
        user: str = proc_info.get('username', 'N/A')
        cmdline = proc_info.get('cmdline', [])
        cmdline: str = " ".join(cmdline) if cmdline else 'N/A'
        exe: str = proc_info.get('exe', 'N/A')

        # Handle cases where the parent process is None
        parent_pid, parent_name = "N/A", "N/A"
        parent: psutil.Process|None = proc.parent()
        if parent:  # Check if parent is not None
            parent_pid: int = parent.pid
            parent_name: str = parent.name()

        logger.write_log(f"timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} | "
          f"hostname: {hostname} | username: {user} | event: process created | "
          f"pid: {pid} | name: {proc_name} | ppid: {parent_pid} | parent: {parent_name} | "
          f"exe: {exe} | cmdline: {cmdline} | uuid: {uuid}"
        )
        log_line_count += 1
      except (psutil.NoSuchProcess, psutil.AccessDenied):
        continue

    # Log terminated processes
    for pid in terminated_processes:
      try:
        proc = psutil.Process(pid)
        proc_info = proc.as_dict(attrs=['pid', 'name', 'username', 'exe', 'cmdline'])
        pid = proc_info.get('pid', 'N/A')
        proc_name: str = proc_info.get('name', 'Unknown')
        user: str = proc_info.get('username', 'N/A')
        cmdline = proc_info.get('cmdline', [])
        cmdline: str = " ".join(cmdline) if cmdline else 'N/A'
        exe: str = proc_info.get('exe', 'N/A')
      
        # Handle cases where the parent process is None
        parent_pid, parent_name = "N/A", "N/A"
        parent: psutil.Process|None = proc.parent()
        if parent:  # Check if parent is not None
            parent_pid: int = parent.pid
            parent_name: str = parent.name()

        logger.write_log(f"timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} | "
          f"hostname: {hostname} | username: {user} | event: process terminated | "
          f"pid: {pid} | name: {proc_name} | ppid: {parent_pid} | parent: {parent_name} | "
          f"exe: {exe} | cmdline: {cmdline} | uuid: {uuid}"
        )
        log_line_count += 1
      except (psutil.NoSuchProcess, psutil.AccessDenied):
        continue

    # Print the current running total of log lines every 10 seconds
    if int(time.time()) % 10 == 0:
      debug_logger.check_logging_interval()
      debug_logger.write_log(f'timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} | '
                      f'hostname: {hostname} | source: process | platform: macos | event: progress | '
                      f'message: Running {log_line_count} log lines written | value: {log_line_count}')

    # Update the previous process set
    previous_processes = current_processes
    time.sleep(interval)

def run() -> NoReturn:
  log_directory: str = 'tmp-process' if attr.get_config_value('General', 'RunDatabaseOperations', False, 'bool') else 'tmp'
  ready_directory: str = 'ready'
  debug_generator_directory: str = 'debuggeneratorlogs'
  os.makedirs(debug_generator_directory, exist_ok=True)
  os.makedirs(log_directory, exist_ok=True)
  os.makedirs(ready_directory, exist_ok=True)
  # Run the monitor with a 0.1-second interval
  interval: float = attr.get_config_value('MacOS', 'ProcessInterval', 0.1, 'float')
  logger: LoggingModule  = LoggingModule(log_directory, ready_directory, "ProcessMonitor", "process")
  debug_logger: LoggingModule = LoggingModule(debug_generator_directory, ready_directory, "DebugMonitor", "debug")
  monitor_process_events(logger, debug_logger, interval)

run()