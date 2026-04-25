import os
import psutil
import time
from datetime import datetime
from typing import NoReturn
import common.attributes as attr
from common.logger import LoggingModule

hostname: str = attr.get_hostname()
uuid = attr.get_system_uuid()

def log_existing_users(logger: LoggingModule) -> set:
    previous_users = set()
    users = psutil.users()
    for user in users:
        login_time = datetime.fromtimestamp(user.started).strftime("%Y-%m-%d %H:%M:%S")
        user_entry = (user.name, user.terminal or "N/A", user.host or "N/A", login_time)
        logger.write_log(
            f"timestamp: {login_time} | "
            f"hostname: {hostname} | "
            f"category: user_existing | username: {user.name} | "
            f"sourceip: {user.host or 'n/a'} | "
            f"uuid: {uuid}"
        )
        previous_users.add(user_entry)
    return previous_users

def monitor_logged_in_users(logger: LoggingModule, interval: float) -> NoReturn:
    """Monitor and log new user logins only."""
    seen_users: set = log_existing_users(logger)
    
    while True:
        logger.check_logging_interval()
        users = psutil.users()
        for user in users:
            login_time: str = datetime.fromtimestamp(user.started).strftime("%Y-%m-%d %H:%M:%S")
            user_entry = (user.name, user.terminal or "N/A", user.host or "N/A", login_time)

            if user_entry not in seen_users:
                logger.write_log(
                    f"timestamp: {login_time} | "
                    f"hostname: {hostname} | "
                    f"category: new_user_detected | username: {user.name} | "
                    f"sourceip: {user.host or 'n/a'} | "
                    f"uuid: {uuid}"
                )
                seen_users.add(user_entry)
        logger.write_debug_log(f"timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} | "
                        f"hostname: {hostname} | source: user | platform: linux | event: progress | "
                        f"message: {logger.log_line_count} log lines written | value: {logger.log_line_count}")  
        time.sleep(interval)

def run() -> NoReturn:
    interval: float = attr.get_config_value('Linux', 'UserInterval', 1.0, 'float')
    log_directory: str = 'tmp-user-info' if attr.get_config_value('General', 'RunDatabaseOperations', False, 'bool') else 'tmp'
    ready_directory: str = 'ready'
    debug_generator_directory: str = 'debuggeneratorlogs'
    os.makedirs(debug_generator_directory, exist_ok=True)
    os.makedirs(log_directory, exist_ok=True)
    os.makedirs(ready_directory, exist_ok=True)
    logger: LoggingModule = LoggingModule(log_directory, ready_directory, "UserMonitor", "user")
    monitor_logged_in_users(logger, interval)

run()
