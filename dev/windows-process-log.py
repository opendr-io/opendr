import os
import psutil
import time
from datetime import datetime
import common.attributes as attr
from common.logger import LoggingModule

class WindowsProcessLogger():
  def __init__(self):
    self.sid: str = attr.get_computer_sid()
    self.hostname: str = attr.get_hostname()
    self.interval: float = attr.get_config_value('Windows', 'ProcessInterval', 1.0, 'float')
    self.logger = None
    self.previous_processes: set[int] = set()
    self.setup_logger()
    self.log_existing()
    print('WindowsProcessLogger Initialization complete')

  def setup_logger(self) -> None:
    log_directory: str = 'tmp-process' if attr.get_config_value('General', 'RunDatabaseOperations', False, 'bool') else 'tmp'
    ready_directory: str = 'ready'
    debug_generator_directory: str = 'debuggeneratorlogs'
    os.makedirs(debug_generator_directory, exist_ok=True)
    os.makedirs(log_directory, exist_ok=True)
    os.makedirs(ready_directory, exist_ok=True)
    self.logger: LoggingModule  = LoggingModule(log_directory, ready_directory, "ProcessMonitor", "process")

  def log_existing(self) -> None:
    """Logs all currently running processes at script startup."""
    self.previous_processes = set(psutil.pids())

    for proc in psutil.process_iter(attrs=['pid', 'name', 'exe', 'username', 'cmdline']):
      try:
        proc_info = proc.as_dict(attrs=['pid', 'name', 'username', 'cmdline', 'exe'])
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

        self.logger.write_log(f"timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} | "
            f"hostname: {self.hostname} | username: {user} | event: existing process | "
            f"pid: {pid} | name: {proc_name} | ppid: {parent_pid} | parent: {parent_name} | "
            f"exe: {exe} | cmdline: {cmdline} | sid: {self.sid}")
      except (psutil.NoSuchProcess, psutil.AccessDenied):
        continue

  def monitor_events(self) -> None:
    """Monitors process creation and termination events while tracking log lines written."""
    # # Check if the minute has changed to rotate the log file
    self.logger.check_logging_interval()

    current_processes: set[int] = set(psutil.pids()) 
    created_processes = current_processes - self.previous_processes
    terminated_processes = self.previous_processes - current_processes

    # Log created processes
    for pid in created_processes:
      try:
        proc: psutil.Process = psutil.Process(pid)
        proc_info = proc.as_dict(attrs=['pid', 'name', 'username', 'cmdline', 'exe'])
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

        self.logger.write_log(f"timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} | "
          f"hostname: {self.hostname} | username: {user} | event: process created | "
          f"pid: {pid} | name: {proc_name} | ppid: {parent_pid} | parent: {parent_name} | "
          f"exe: {exe} | cmdline: {cmdline} | sid: {self.sid}")
      except (psutil.NoSuchProcess, psutil.AccessDenied):
        continue

    # Log terminated processes
    for pid in terminated_processes:
      try:
        proc: psutil.Process = psutil.Process(pid)
        proc_info = proc.as_dict(attrs=['pid', 'name', 'username', 'cmdline', 'exe'])
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

        self.logger.write_log(f"timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} | "
          f"hostname: {self.hostname} | username: {user} | event: process terminated | "
          f"pid: {pid} | name: {proc_name} | ppid: {parent_pid} | parent: {parent_name} | "
          f"exe: {exe} | cmdline: {cmdline} | sid: {self.sid}")
      except (psutil.NoSuchProcess, psutil.AccessDenied):
        continue

    # Print the current running total of log lines every 10 seconds
    if int(time.time()) % 10 == 0:
      self.logger.write_debug_log(f'timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} | '
                            f'hostname: {self.hostname} | source: process | platform: windows | event: progress | '
                            f'message: {self.logger.log_line_count} log lines written | value: {self.logger.log_line_count}')

    # Update the previous process set
    self.previous_processes = current_processes
