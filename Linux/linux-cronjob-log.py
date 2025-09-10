import os
import pwd
import time
import subprocess
from datetime import datetime
import common.attributes as attr
from common.logger import LoggingModule

def get_crontab_jobs(filepath: str) -> list:
    jobs: list = []
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#'):
                    jobs.append(line)
    except Exception as e:
        jobs.append(f"ERROR reading {filepath}: {e}")
    return jobs

def get_user_crontabs() -> list:
    jobs: list = []
    for user in pwd.getpwall():
        username = user.pw_name
        try:
            result = subprocess.run(['crontab', '-l', '-u', username], capture_output=True, text=True)
            if result.returncode == 0:
                for line in result.stdout.strip().splitlines():
                    line = line.strip()
                    if line and not line.startswith('#'):
                        jobs.append(f"user: {username} | job: {line}")
        except Exception:
            continue
    return jobs

def log_cron_jobs(log_directory: str, ready_directory: str) -> None:
    logger = LoggingModule(log_directory, ready_directory, "CronJobMonitor", "cronjob")
    hostname: str = attr.get_hostname()
    timestamp: str = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

    cron_files: list[str] = ['/etc/crontab'] + [
        os.path.join('/etc/cron.d', f)
        for f in os.listdir('/etc/cron.d')
        if os.path.isfile(os.path.join('/etc/cron.d', f))
    ]

    for path in cron_files:
        for job in get_crontab_jobs(path):
            entry: str = f"timestamp: {timestamp} | hostname: {hostname} | file: {path} | job: {job}"
            logger.write_log(entry)

    for job in get_user_crontabs():
        entry: str = f"timestamp: {timestamp} | hostname: {hostname} | source: user_crontab | {job}"
        logger.write_log(entry)

    logger.write_debug_log(f"timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} | "
                        f"hostname: {hostname} | source: cronjob | platform: linux | event: progress | "
                        f"message: {logger.log_line_count} log lines written | value: {logger.log_line_count}")
    logger.clear_handlers()

def run():
    interval: float = attr.get_config_value('Linux', 'CronLogInterval', 43200.0, 'float')
    log_directory: str = 'tmp-cron-job' if attr.get_config_value('General', 'RunDatabaseOperations', False, 'bool') else 'tmp'
    ready_directory: str = 'ready'
    debug_generator_directory: str = 'debuggeneratorlogs'
    os.makedirs(debug_generator_directory, exist_ok=True)
    os.makedirs(log_directory, exist_ok=True)
    os.makedirs(ready_directory, exist_ok=True)
    print("cronlog running")
    while True:
        log_cron_jobs(log_directory, ready_directory)
        time.sleep(interval)

if __name__ == "__main__":
    run()
