import subprocess
import pandas as pd
import os
import csv
import io
import time
from datetime import datetime
import common.attributes as attr
from common.logger import LoggingModule
from typing import NoReturn

timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
hostname: str = attr.get_hostname()
computer_sid: str = attr.get_computer_sid() or ''
ec2_instance_id: str = attr.get_ec2_instance_id() or ''

def format_row_with_keys(row):
    return " | ".join(f"{col}: {row[col]}" for col in row.index if pd.notna(row[col]))

def fetch_scheduled_tasks() -> pd.DataFrame:
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
    dft['timestamp'] = timestamp
    dft['hostname'] = hostname
    dft['sid'] = computer_sid
    dft['ec2_instance_id'] = ec2_instance_id
    dft['event'] = 'existing scheduled task'

    final_order = [
        'timestamp', 'hostname', 'event',
        'task_name', 'status', 'last_run', 'next_run', 'task_to_run',
        'schedule', 'author', 'start_time',  'sid', 'ec2_instance_id'
    ]
    dft = dft[[col for col in final_order if col in dft.columns]]
    return dft

def log_scheduled_tasks(logger: LoggingModule) -> NoReturn:
    interval = attr.get_config_value('Windows', 'TaskInterval', 60.0, 'float')
    prev_df: pd.DataFrame = fetch_scheduled_tasks()
    lines = prev_df.apply(format_row_with_keys, axis=1)
    for line in lines:
        logger.write_log(line)
    while True:
        logger.check_logging_interval()
        cur_df: pd.DataFrame = fetch_scheduled_tasks()
        df_new: pd.DataFrame = pd.concat([cur_df, prev_df, prev_df]).drop_duplicates(keep=False)
        df_new["event"] = "new scheduled task found"
        df_new['timestamp'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        lines = df_new.apply(format_row_with_keys, axis=1)
        for line in lines:
            logger.write_log(line)
        prev_df = cur_df
        logger.write_debug_log(f'timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} | '
                        f'hostname: {hostname} | source: tasks | platform: windows | event: progress | '
                        f'message: {logger.log_line_count} log lines written | value: {logger.log_line_count}')
        time.sleep(interval)

def run():
    log_directory = 'tmp-scheduled-tasks' if attr.get_config_value('General', 'RunDatabaseOperations', False, 'bool') else 'tmp'
    ready_directory = 'ready'
    debug_generator_directory = 'debuggeneratorlogs'
    os.makedirs(debug_generator_directory, exist_ok=True)
    os.makedirs(log_directory, exist_ok=True)
    os.makedirs(ready_directory, exist_ok=True)
    print('tasklog running')
    logger: LoggingModule  = LoggingModule(log_directory, ready_directory, "TaskMonitor", "scheduled_task")
    fetch_scheduled_tasks(logger)

run()
