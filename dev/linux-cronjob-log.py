import os
import pwd
import time
import subprocess
from datetime import datetime
import common.attributes as attr
from common.logger import LoggingModule

class LinuxCronjobLogger(attr.LoggerParent):
    def __init__(self):
        super().__init__()
        self.interval: float = attr.get_config_value('Linux', 'CronLogInterval', 43200.0, 'float')
        self.previous_jobs: set = set()
        self.cron_files: list[str] = ['/etc/crontab'] + [
            os.path.join('/etc/cron.d', f)
            for f in os.listdir('/etc/cron.d')
            if os.path.isfile(os.path.join('/etc/cron.d', f))
        ]
        self.setup_logger()
        self.log_existing()
        print('LinuxCronjobLogger Initialization complete')

    def setup_logger(self) -> None:
        log_directory: str = 'tmp-cron-job' if attr.get_config_value('General', 'RunDatabaseOperations', False, 'bool') else 'tmp'
        ready_directory: str = 'ready'
        debug_generator_directory: str = 'debuggeneratorlogs'
        os.makedirs(debug_generator_directory, exist_ok=True)
        os.makedirs(log_directory, exist_ok=True)
        os.makedirs(ready_directory, exist_ok=True)
        self.logger: LoggingModule = LoggingModule(log_directory, ready_directory, "CronJobMonitor", "cronjob")

    @staticmethod
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

    @staticmethod
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

    def log_existing(self) -> None:
        timestamp: str = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        for path in self.cron_files:
            for job in self.get_crontab_jobs(path):
                if (path, job) in self.previous_jobs:
                    continue
                entry: str = f"timestamp: {timestamp} | hostname: {self.hostname} | event: existing cronjob | file: {path} | job: {job}"
                self.logger.write_log(entry)
                self.previous_jobs.add((path, job))

        for job in self.get_user_crontabs():
            if ('user_crontab', job) in self.previous_jobs:
                continue
            entry: str = f"timestamp: {timestamp} | hostname: {self.hostname} | event: existing cronjob | source: user_crontab | {job}"
            self.logger.write_log(entry)
            self.previous_jobs.add(('user_crontab', job))

    def monitor_events(self) -> None:
        timestamp: str = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        for path in self.cron_files:
            for job in self.get_crontab_jobs(path):
                if (path, job) in self.previous_jobs:
                    continue
                entry: str = f"timestamp: {timestamp} | hostname: {self.hostname} | event: new cronjob detected | file: {path} | job: {job}"
                self.logger.write_log(entry)
                self.previous_jobs.add((path, job))

        for job in self.get_user_crontabs():
            if ('user_crontab', job) in self.previous_jobs:
                continue
            entry: str = f"timestamp: {timestamp} | hostname: {self.hostname} | event: new cronjob detected | source: user_crontab | {job}"
            self.logger.write_log(entry)
            self.previous_jobs.add(('user_crontab', job))

        self.logger.write_debug_log(f"timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} | "
                            f"hostname: {self.hostname} | source: cronjob | platform: linux | event: progress | "
                            f"message: {self.logger.log_line_count} log lines written | value: {self.logger.log_line_count}")

if __name__ == '__main__':
    cronjob = LinuxCronjobLogger()
    while True:
        cronjob.monitor_events()
        time.sleep(cronjob.interval)
