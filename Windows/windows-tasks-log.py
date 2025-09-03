import subprocess
import os
import csv
import io
import time
from datetime import datetime
import common.attributes as attr
from common.logger import LoggingModule
from typing import NoReturn

hostname: str = attr.get_hostname()
computer_sid: str = attr.get_computer_sid() or ''
ec2_instance_id: str = attr.get_ec2_instance_id() or ''

def fetch_scheduled_tasks() -> list[dict]:
    # Run schtasks with verbose CSV output
    proc = subprocess.run(
        ['schtasks', '/query', '/fo', 'CSV', '/v'],
        capture_output=True, text=True, check=True
    )
    tasks = list(csv.DictReader(io.StringIO(proc.stdout)))

    if not tasks:
        return

    column_names: dict = {
        'timestamp': 'timestamp',
        'hostname': 'hostname',
        'event': 'event',
        'TaskName': 'task_name',
        'Status': 'status',
        'Last Run Time': 'last_run',
        'Next Run Time': 'next_run',
        'Task To Run': 'task_to_run',
        'Schedule': 'schedule',
        'Author': 'author',
        'Start Time': 'start_time',
        'ec2_instance_id': 'ec2_instance_id',
        'sid': 'sid'
    }
    
    for task in tasks:
        task['timestamp'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        task['hostname'] = hostname
        task['sid'] = computer_sid
        task['ec2_instance_id'] = ec2_instance_id
        task['event'] = 'existing scheduled task'

    tasks = [{val: task[key] for key, val in column_names.items()} for task in tasks]
    return tasks

def log_existing_data(logger: LoggingModule) -> set:
    prev_tasks: set = set()
    task_data: list[dict] = fetch_scheduled_tasks()
    for data in task_data:
        if (data['task_name'], data['task_to_run'], data['start_time']) in prev_tasks:
            continue
        prev_tasks.add((data['task_name'], data['task_to_run'], data['start_time']))
        logger.write_log(" | ".join([f"{key}: {data[key]}" for key in data]))
    return prev_tasks

def log_scheduled_tasks(logger: LoggingModule) -> NoReturn:
    interval = attr.get_config_value('Windows', 'TaskInterval', 60.0, 'float')
    prev_tasks: set = log_existing_data(logger)

    while True:
        logger.check_logging_interval()
        task_data: list[dict] = fetch_scheduled_tasks()
        for data in task_data:
            if (data['task_name'], data['task_to_run'], data['start_time']) in prev_tasks:
                continue
            data["event"] = "new scheduled task found"
            logger.write_log(" | ".join([f"{key}: {data[key]}" for key in data]))
            prev_tasks.add((data['task_name'], data['task_to_run'], data['start_time']))

        logger.write_debug_log(f'timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} | '
                        f'hostname: {hostname} | source: tasks | platform: windows | event: progress | '
                        f'message: {logger.log_line_count} log lines written | value: {logger.log_line_count}')
        time.sleep(interval)

def run() -> NoReturn:
    log_directory = 'tmp-scheduled-tasks' if attr.get_config_value('General', 'RunDatabaseOperations', False, 'bool') else 'tmp'
    ready_directory = 'ready'
    debug_generator_directory = 'debuggeneratorlogs'
    os.makedirs(debug_generator_directory, exist_ok=True)
    os.makedirs(log_directory, exist_ok=True)
    os.makedirs(ready_directory, exist_ok=True)
    print('tasklog running')
    logger: LoggingModule  = LoggingModule(log_directory, ready_directory, "TaskMonitor", "scheduled_task")
    log_scheduled_tasks(logger)

run()
