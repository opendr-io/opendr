import subprocess
import pandas as pd
import os
import csv
import io
import time
from datetime import datetime
import common.attributes as attr
from common.logger import LoggingModule

def format_row_with_keys(row):
    return " | ".join(f"{col}: {row[col]}" for col in row.index if pd.notna(row[col]))

def fetch_scheduled_tasks(logger: LoggingModule) -> None:
    logger.check_logging_interval()

    # Run schtasks with verbose CSV output
    proc = subprocess.run(
        ['schtasks', '/query', '/fo', 'CSV', '/v'],
        capture_output=True, text=True, check=True
    )
    tasks = list(csv.DictReader(io.StringIO(proc.stdout)))

    if not tasks:
        return

    # Load into DataFrame
    dft = pd.DataFrame(tasks)

    # Trim and normalize fields
    dft = dft.rename(columns={
        'TaskName': 'task_name',
        'Status': 'status',
        'Last Run Time': 'last_run',
        'Next Run Time': 'next_run',
        'Task To Run': 'task_to_run',
        'Schedule': 'schedule',
        'Author': 'author',
        'Start Time': 'start_time'
    })

    keep = [
        'task_name', 'status', 'last_run', 'next_run',
        'task_to_run', 'schedule', 'author', 'start_time'
    ]
    dft = dft[[col for col in keep if col in dft.columns]]

    # Add system metadata
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    dft['timestamp'] = timestamp
    dft['hostname'] = attr.get_hostname()
    dft['sid'] = attr.get_computer_sid() or ''
    dft['ec2_instance_id'] = attr.get_ec2_instance_id() or ''
    dft['event'] = 'scheduled_task'

    # Final output column order
    final_order = [
        'timestamp', 'hostname', 'event',
        'task_name', 'status', 'last_run', 'next_run', 'task_to_run',
        'schedule', 'author', 'start_time',  'sid', 'ec2_instance_id'
    ]
    dft = dft[[col for col in final_order if col in dft.columns]]

    # Format and write each row
    for line in dft.apply(format_row_with_keys, axis=1):
        logger.write_log(line)

    logger.write_debug_log(f"timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} | "
                        f"hostname: {attr.get_hostname()} | source: tasks | platform: windows | event: progress | "
                        f"message: {logger.log_line_count} log lines written | value: {logger.log_line_count}")
    logger.clear_handlers()

def run():
    interval = attr.get_config_value('Windows', 'TaskInterval', 43200.0, 'float')
    log_directory = 'tmp-scheduled-tasks' if attr.get_config_value('General', 'RunDatabaseOperations', False, 'bool') else 'tmp'
    ready_directory = 'ready'
    debug_generator_directory = 'debuggeneratorlogs'
    os.makedirs(debug_generator_directory, exist_ok=True)
    os.makedirs(log_directory, exist_ok=True)
    os.makedirs(ready_directory, exist_ok=True)
    print('tasklog running')
    logger: LoggingModule  = LoggingModule(log_directory, ready_directory, "TaskMonitor", "scheduled_task")
    while True:
        fetch_scheduled_tasks(logger)
        time.sleep(interval)

run()
