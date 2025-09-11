import os
import psutil
import time
from datetime import datetime
import common.attributes as attr
from common.logger import LoggingModule

class LinuxUserLogger(attr.LoggerParent):
    def __init__(self):
        super().__init__()
        self.interval: float = attr.get_config_value('Linux', 'UserInterval', 1.0, 'float')
        self.seen_users: set = set()
        self.setup_logger()
        self.log_existing()
        print('LinuxUserLogger Initialization complete')

    def setup_logger(self) -> None:
        log_directory: str = 'tmp-user-info' if attr.get_config_value('General', 'RunDatabaseOperations', False, 'bool') else 'tmp'
        ready_directory: str = 'ready'
        debug_generator_directory: str = 'debuggeneratorlogs'
        os.makedirs(debug_generator_directory, exist_ok=True)
        os.makedirs(log_directory, exist_ok=True)
        os.makedirs(ready_directory, exist_ok=True)
        self.logger: LoggingModule = LoggingModule(log_directory, ready_directory, "UserMonitor", "user")

    def log_existing(self) -> None:
        users = psutil.users() 
        for user in users:
            login_time = datetime.fromtimestamp(user.started).strftime("%Y-%m-%d %H:%M:%S")
            user_entry = (user.name, user.terminal or "N/A", user.host or "N/A", login_time)
            self.logger.write_log(
                f"timestamp: {login_time} | "
                f"hostname: {self.hostname} | "
                f"category: user_existing | username: {user.name} | "
                f"sourceip: {user.host or 'n/a'} | "
                f"uuid: {self.sid}"
            )
            self.seen_users.add(user_entry)
            
    def monitor_events(self) -> None:
        """Monitor and log new user logins only."""
        self.logger.check_logging_interval()
        users = psutil.users()
        for user in users:
            login_time = datetime.fromtimestamp(user.started).strftime("%Y-%m-%d %H:%M:%S")
            user_entry = (user.name, user.terminal or "N/A", user.host or "N/A", login_time)
            if user_entry in self.seen_users:
                continue
            self.logger.write_log(
                f"timestamp: {login_time} | "
                f"hostname: {self.hostname} | "
                f"category: new_user_detected | username: {user.name} | "
                f"sourceip: {user.host or 'n/a'} | "
                f"uuid: {self.sid}"
            )
            self.seen_users.add(user_entry)
        self.logger.write_debug_log(f"timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} | "
                                    f"hostname: {self.hostname} | source: user | platform: linux | event: progress | "
                                    f"message: {self.logger.log_line_count} log lines written | value: {self.logger.log_line_count}")

if __name__ == '__main__':
    user = LinuxUserLogger()
    while True:
        user.monitor_events()
        time.sleep(user.interval)