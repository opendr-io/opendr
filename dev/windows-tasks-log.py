import subprocess
import os
import csv
import io
import time
from datetime import datetime
import common.attributes as attr
from common.logger import LoggingModule
from typing import NoReturn

class WindowsTasksLogger():
    def __init__(self):
        self.sid: str = attr.get_computer_sid() or ''
        self.hostname: str = attr.get_hostname()
        self.ec2_instance_id: str = attr.get_ec2_instance_id() or ''
        self.interval: float = attr.get_config_value('Windows', 'TaskInterval', 60.0, 'float')
        self.logger = None
        self.prev_tasks: set = set()
        self.setup_logger()
        self.log_existing()
        print('WindowsTasksLogger Initialization complete')

    def setup_logger(self) -> None:
        log_directory: str = 'tmp-scheduled-tasks' if attr.get_config_value('General', 'RunDatabaseOperations', False, 'bool') else 'tmp'
        ready_directory: str = 'ready'
        debug_generator_directory: str = 'debuggeneratorlogs'
        os.makedirs(debug_generator_directory, exist_ok=True)
        os.makedirs(log_directory, exist_ok=True)
        os.makedirs(ready_directory, exist_ok=True)
        self.logger: LoggingModule = LoggingModule(log_directory, ready_directory, "TaskMonitor", "scheduled_task")

    def fetch_scheduled_tasks(self) -> list[dict]:
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
            task['hostname'] = self.hostname
            task['sid'] = self.sid
            task['ec2_instance_id'] = self.ec2_instance_id
            task['event'] = 'existing scheduled task'

        tasks = [{val: task[key] for key, val in column_names.items()} for task in tasks]
        return tasks

    def log_existing(self) -> None:
        task_data: list[dict] = self.fetch_scheduled_tasks()
        for data in task_data:
            if (data['task_name'], data['task_to_run'], data['start_time']) in self.prev_tasks:
                continue
            self.prev_tasks.add((data['task_name'], data['task_to_run'], data['start_time']))
            self.logger.write_log(" | ".join([f"{key}: {data[key]}" for key in data]))

    def monitor_events(self) -> None:
        self.logger.check_logging_interval()
        task_data: list[dict] = self.fetch_scheduled_tasks()
        for data in task_data:
            if (data['task_name'], data['task_to_run'], data['start_time']) in self.prev_tasks:
                continue
            data["event"] = "new scheduled task found"
            self.logger.write_log(" | ".join([f"{key}: {data[key]}" for key in data]))
            self.prev_tasks.add((data['task_name'], data['task_to_run'], data['start_time']))

        self.logger.write_debug_log(f'timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} | '
                        f'hostname: {self.hostname} | source: tasks | platform: windows | event: progress | '
                        f'message: {self.logger.log_line_count} log lines written | value: {self.logger.log_line_count}')
