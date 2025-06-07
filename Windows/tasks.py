import os
import subprocess
import csv
import io
import time
from datetime import datetime
import common.attributes as attr
import common.logger as logfunc

log_line_count = 0

def get_scheduled_tasks():
    """Retrieve all scheduled tasks using schtasks with CSV output."""
    result = subprocess.run(
        ['schtasks', '/query', '/fo', 'CSV', '/v'],
        capture_output=True, text=True, encoding='utf-8'
    )

    # Parse CSV output
    tasks = []
    try:
        reader = csv.DictReader(io.StringIO(result.stdout))
        for row in reader:
            tasks.append(row)
    except csv.Error as e:
        print("CSV parsing error:", e)
    return tasks

def log_scheduled_tasks(log_directory, ready_directory):
    """Logs scheduled tasks with system metadata."""
    logger = logfunc.setup_logging(log_directory, ready_directory, "TaskMonitor", "scheduled_tasks")
    hostname = attr.get_hostname()
    sid = attr.get_computer_sid()
    instance_id = attr.get_ec2_instance_id()

    global log_line_count
    tasks = get_scheduled_tasks()

    for task in tasks:
        log_entry = (
            f"timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} | "
            f"hostname: {hostname} | "
            f"taskname: {task.get('TaskName')} | "
            f"status: {task.get('Status')} | "
            f"last_run: {task.get('Last Run Time')} | "
            f"next_run: {task.get('Next Run Time')} | "
            f"task_to_run: {task.get('Task To Run')} | "
            f"schedule: {task.get('Schedule')} | "
            f"author: {task.get('Author')} | "
            f"start_time: {task.get('Start Time')} | "
            f"instanceid: {instance_id} | sid: {sid}"
        )
        logger.info(log_entry)
        log_line_count += 1
        if int(time.time()) % 10 == 0:
            logfunc.enter_debug_logs('task-inventory', f"Running total log lines written: {log_line_count}  \n")

    logfunc.clear_handlers(log_directory, ready_directory, logger)

def run():
    interval = attr.get_config_value('Windows', 'TaskInterval', 43200.0, 'float')
    log_directory = 'tmp-scheduled-tasks' if attr.get_config_value('Windows', 'RunDatabaseOperations', False, 'bool') else 'tmp'
    ready_directory = 'ready'
    debug_generator_directory = 'debuggeneratorlogs'
    os.makedirs(debug_generator_directory, exist_ok=True)
    os.makedirs(log_directory, exist_ok=True)
    os.makedirs(ready_directory, exist_ok=True)
    while True:
        log_scheduled_tasks(log_directory, ready_directory)
        time.sleep(interval)  # Twice a day by default, can be increased or decreased

run()
