import os
import pwd
import time
import socket
import subprocess
import logging
from datetime import datetime

log_directory = 'logs'
os.makedirs(log_directory, exist_ok=True)
log_file = os.path.join(log_directory, 'cron-jobs.log')

logging.basicConfig(
    filename=log_file,
    level=logging.INFO,
    format='%(message)s'
)

def get_hostname():
    return socket.gethostname()

def get_crontab_jobs(filepath):
    jobs = []
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#'):
                    jobs.append(line)
    except Exception as e:
        jobs.append(f"ERROR reading {filepath}: {e}")
    return jobs

def get_user_crontabs():
    jobs = []
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

def log_cron_jobs():
    hostname = get_hostname()
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    
    cron_files = ['/etc/crontab'] + [
        os.path.join('/etc/cron.d', f)
        for f in os.listdir('/etc/cron.d')
        if os.path.isfile(os.path.join('/etc/cron.d', f))
    ]

    for path in cron_files:
        for job in get_crontab_jobs(path):
            entry = f"timestamp: {timestamp} | hostname: {hostname} | file: {path} | job: {job}"
            logging.info(entry)

    for job in get_user_crontabs():
        entry = f"timestamp: {timestamp} | hostname: {hostname} | source: user_crontab | {job}"
        logging.info(entry)

def run():
    interval = 43200  # 12 hours
    print("cronlog running")
    while True:
        log_cron_jobs()
        time.sleep(interval)

if __name__ == "__main__":
    run()
