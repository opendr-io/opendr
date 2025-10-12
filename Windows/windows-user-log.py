import os
import psutil
import time
from datetime import datetime
import common.attributes as attr
from common.logger import LoggingModule

hostname = attr.get_hostname()
sid = attr.get_computer_sid()

def log_existing_users(logger: LoggingModule) -> set:
    previous_users = set()
    users = psutil.users() 
    for user in users:
        login_time = datetime.fromtimestamp(user.started).strftime("%Y-%m-%d %H:%M:%S")
        user_entry = (user.name, user.terminal or "N/A", user.host or "N/A", login_time)
        logger.write_log(
            f"timestamp: {login_time} | "
            f"hostname: {hostname} | "
            f"event: existing user | username: {user.name} | "
            f"sourceip: {user.host or 'n/a'} | "
            f"sid: {sid}"
        )
        previous_users.add(user_entry)
    return previous_users

def monitor_logged_in_users(log_directory, ready_directory, interval):
    """Monitor and log new user logins only."""
    logger = LoggingModule(log_directory, ready_directory, "UserMonitor", "user")
    seen_users = log_existing_users(logger)
    
    while True:
        logger.check_logging_interval()
        users = psutil.users()
        for user in users:
            login_time = datetime.fromtimestamp(user.started).strftime("%Y-%m-%d %H:%M:%S")
            user_entry = (user.name, user.terminal or "N/A", user.host or "N/A", login_time)
            
            if user_entry in seen_users:
                continue
            logger.write_log(
                f"timestamp: {login_time} | "
                f"hostname: {hostname} | "
                f"event: new user detected | username: {user.name} | "
                f"sourceip: {user.host or 'n/a'} | "
                f"sid: {sid}"
            )
            seen_users.add(user_entry)
        logger.write_debug_log(f'timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} | '
                        f'hostname: {hostname} | source: user | platform: windows | event: progress | '
                        f'message: {logger.log_line_count} log lines written | value: {logger.log_line_count}')
        time.sleep(interval)

def run():
    interval = attr.get_config_value('Windows', 'UserInterval', 1.0, 'float')
    log_directory = 'tmp-user-info' if attr.get_config_value('General', 'RunDatabaseOperations', False, 'bool') else 'tmp'
    ready_directory = 'ready'
    debug_generator_directory = 'debuggeneratorlogs'
    os.makedirs(debug_generator_directory, exist_ok=True)
    os.makedirs(log_directory, exist_ok=True)
    os.makedirs(ready_directory, exist_ok=True)
    monitor_logged_in_users(log_directory, ready_directory, interval)

run()
