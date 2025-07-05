import os
import psutil
import time
from datetime import datetime
from typing import NoReturn
import common.attributes as attr
from common.logger import check_logging_interval

hostname: str = attr.get_hostname()
uuid = attr.get_system_uuid()

def log_existing_users(logger) -> set:
    previous_users = set()
    users = psutil.users()
    for user in users:
        login_time = datetime.fromtimestamp(user.started).strftime("%Y-%m-%d %H:%M:%S")
        user_entry = (user.name, user.terminal or "N/A", user.host or "N/A", login_time)
        logger.info(
            f"timestamp: {login_time} | "
            f"hostname: {hostname} | "
            f"event: existing user | username: {user.name} | "
            f"sourceip: {user.host or 'n/a'} | "
            f"uuid: {uuid}"
        )
        previous_users.add(user_entry)
    return previous_users

def monitor_logged_in_users(log_directory: str, ready_directory: str, interval: float) -> NoReturn:
    """Monitor and log new user logins only."""
    logger, last_interval = check_logging_interval(log_directory, ready_directory, "UserMonitor", "user", None, None)
    seen_users: set = log_existing_users(logger)
    
    while True:
        logger, last_interval = check_logging_interval(log_directory, ready_directory, "UserMonitor", "user", logger, last_interval)
        users = psutil.users()
        for user in users:
            login_time: str = datetime.fromtimestamp(user.started).strftime("%Y-%m-%d %H:%M:%S")
            user_entry = (user.name, user.terminal or "N/A", user.host or "N/A", login_time)
            
            if user_entry not in seen_users:
                logger.info(
                    f"timestamp: {login_time} | "
                    f"hostname: {hostname} | "
                    f"event: new user detected | username: {user.name} | "
                    f"sourceip: {user.host or 'n/a'} | "
                    f"uuid: {uuid}"
                )
                seen_users.add(user_entry)  
        time.sleep(interval)

def run() -> NoReturn:
    interval: float = attr.get_config_value('Linux', 'UserInterval', 1.0, 'float')
    log_directory: str = 'tmp-user-info' if attr.get_config_value('Linux', 'RunDatabaseOperations', False, 'bool') else 'tmp'
    ready_directory: str = 'ready'
    debug_generator_directory: str = 'debuggeneratorlogs'
    os.makedirs(debug_generator_directory, exist_ok=True)
    os.makedirs(log_directory, exist_ok=True)
    os.makedirs(ready_directory, exist_ok=True)
    monitor_logged_in_users(log_directory, ready_directory, interval)

run()
