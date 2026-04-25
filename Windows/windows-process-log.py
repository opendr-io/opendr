import os
import psutil
import time
from datetime import datetime
import common.attributes as attr
from common.logger import LoggingModule
from typing import NoReturn

# Retrieve system details once
sid: str = attr.get_computer_sid()
hostname: str = attr.get_hostname()

def _format_cmdline(cmdline: list[str]|None) -> str:
  return " ".join(cmdline) if cmdline else 'N/A'

def _get_process_snapshot() -> dict[int, dict]:
  """Return process details keyed by PID using the fastest available process listing."""
  snapshot: dict[int, dict] = {}
  for pid in psutil.pids():
    snapshot[pid] = {'pid': pid}
  return snapshot

def _enrich_process_info(proc_info: dict, pid_name_cache: dict[int, str]|None=None) -> dict:
  """Best-effort enrichment for a process observed in the fast snapshot."""
  try:
    proc = psutil.Process(proc_info['pid'])

    with proc.oneshot():
      parent_pid = proc.ppid()
      parent_name = 'Unknown'
      if parent_pid:
        if pid_name_cache and parent_pid in pid_name_cache:
          parent_name = pid_name_cache[parent_pid]
        else:
          parent_name = attr.get_process_name(parent_pid)

      proc_info = proc_info.copy()
      proc_info['name'] = proc.name()
      proc_info['username'] = proc.username()
      proc_info['cmdline'] = _format_cmdline(proc.cmdline())
      proc_info['exe'] = proc.exe()
      proc_info['create_time'] = proc.create_time()
      proc_info['parent_pid'] = parent_pid
      proc_info['parent_name'] = parent_name
      return proc_info
  except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
    proc_info = proc_info.copy()
    proc_info.setdefault('name', 'Unknown')
    proc_info.setdefault('username', 'N/A')
    proc_info.setdefault('cmdline', 'N/A')
    proc_info.setdefault('exe', 'N/A')
    proc_info.setdefault('create_time', 0)
    proc_info.setdefault('parent_pid', 'N/A')
    proc_info.setdefault('parent_name', 'N/A')
    return proc_info

def _write_process_log(logger: LoggingModule, category: str, proc_info: dict) -> None:
  create_time = datetime.fromtimestamp(proc_info['create_time']).strftime('%Y-%m-%d %H:%M:%S.%f')
  logger.write_log(f"timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} | "
    f"hostname: {hostname} | username: {proc_info['username']} | category: {category} | "
    f"processid: {proc_info['pid']} | process: {proc_info['name']} | "
    f"creationtime: {create_time} | parentprocessid: {proc_info['parent_pid']} | "
    f"parentimage: {proc_info['parent_name']} | image: {proc_info['exe']} | "
    f"commandline: {proc_info['cmdline']} | sid: {sid}")

def log_existing_processes(logger: LoggingModule) -> None:
  """Logs all currently running processes at script startup."""
  #log_message(logger, f"Logging all existing processes at startup on {hostname} with SID: {sid}")
  for proc_info in _get_process_snapshot().values():
    _write_process_log(logger, 'process_existing', _enrich_process_info(proc_info))

def monitor_process_events(logger: LoggingModule, interval: float) -> NoReturn:
  """Monitors process creation and termination events while tracking log lines written."""
  previous_processes: dict[int, dict] = _get_process_snapshot()

  # Log all running processes at startup
  for pid, proc_info in previous_processes.items():
    previous_processes[pid] = _enrich_process_info(proc_info)
    _write_process_log(logger, 'process_existing', previous_processes[pid])

  while True:
    # # Check if the minute has changed to rotate the log file
    logger.check_logging_interval()

    current_processes: dict[int, dict] = _get_process_snapshot()
    created_processes = current_processes.keys() - previous_processes.keys()
    terminated_processes = previous_processes.keys() - current_processes.keys()

    # Log created processes
    created_details: dict[int, dict] = {}
    created_names: dict[int, str] = {}
    for pid in created_processes:
      proc_info = _enrich_process_info(current_processes[pid])
      created_details[pid] = proc_info
      created_names[pid] = proc_info['name']

    for pid in created_processes:
      proc_info = created_details[pid]
      parent_pid = proc_info.get('parent_pid')
      if parent_pid in created_names:
        proc_info = proc_info.copy()
        proc_info['parent_name'] = created_names[parent_pid]
      current_processes[pid] = proc_info
      _write_process_log(logger, 'process_creation', current_processes[pid])

    # Log terminated processes
    for pid in terminated_processes:
      _write_process_log(logger, 'process_termination', previous_processes[pid])

    for pid in current_processes.keys() - created_processes:
      current_processes[pid] = previous_processes.get(pid, current_processes[pid])

    # Print the current running total of log lines every 10 seconds
    if int(time.time()) % 10 == 0:
      logger.write_debug_log(f"timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} | "
                            f"hostname: {hostname} | source: process | platform: windows | event: progress | "
                            f"message: {logger.log_line_count} log lines written | value: {logger.log_line_count}")

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
  interval = attr.get_config_value('Windows', 'ProcessInterval', 0.1, 'float')
  logger: LoggingModule  = LoggingModule(log_directory, ready_directory, "ProcessMonitor", "process")
  monitor_process_events(logger, interval)

run()
