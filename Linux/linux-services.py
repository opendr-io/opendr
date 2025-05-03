import subprocess
import os
import time
import common.attributes as attr
import common.logger as logfunc
from datetime import datetime

hostname = attr.get_hostname()
uuid = attr.get_system_uuid()

# List all services and their statuses on a linux machine
def get_all_service_statuses():
    try:
        output = subprocess.check_output(
            ['systemctl', 'list-units', '--type=service', '--no-pager', '--no-legend'],
            stderr=subprocess.DEVNULL
        ).decode('utf-8')

        services = []
        for line in output.strip().split('\n'):
            if line:
                parts = line.split(None, 4)
                service_name = parts[0]
                load_state = parts[1]
                active_state = parts[2]
                sub_state = parts[3]
                description = parts[4] if len(parts) > 4 else ''
                services.append({
                    'name': service_name,
                    'load_state': load_state,
                    'active_state': active_state,
                    'sub_state': sub_state,
                    'description': description
                })

        return services

    except subprocess.CalledProcessError:
        return []

log_line_count = 0

def log_data(log_directory, ready_directory):
    interval = attr.get_config_value('Linux', 'ServiceInterval', 43200.0, 'float')
    while True:
        logger = logfunc.setup_logging(log_directory, ready_directory, "ServiceMonitor", "services")
        global log_line_count
        services = get_all_service_statuses()
        for service in services:
            logger.info((
                f"timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} | hostname: {hostname} | "
                f"name: {service['name']} | active: {service['active_state']} | sub: ({service['sub_state']}) | "
                f"description: {service['description']} | uuid: {uuid}"
                ))
            log_line_count += 1

        logfunc.enter_debug_logs('linux-services', f"Running total log lines written: {log_line_count}  \n")
        logfunc.clear_handlers(log_directory, ready_directory, logger)
        time.sleep(interval)  # Log every 60 minutes - or choose an interval

def run():
    log_directory = 'tmp-linux-services'
    ready_directory = 'ready'
    debug_generator_directory = 'debuggeneratorlogs'
    os.makedirs(debug_generator_directory, exist_ok=True)
    os.makedirs(log_directory, exist_ok=True)
    os.makedirs(ready_directory, exist_ok=True)
    logfunc.move_existing_temp_files(log_directory, ready_directory)
    log_data(log_directory, ready_directory)

run()