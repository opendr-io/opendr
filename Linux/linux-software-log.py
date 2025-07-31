import subprocess
import shutil
import os
import time
import common.attributes as attr
from common.logger import LoggingModule
from datetime import datetime
from typing import NoReturn

hostname: str = attr.get_hostname()
uuid = attr.get_system_uuid()

def get_rpm_packages() -> list[dict]:
    try:
        output = subprocess.check_output(
            ['rpm', '-qa', '--qf', '%{NAME}\t%{VERSION}-%{RELEASE}\t%{ARCH}\t%{SUMMARY}\n'],
            stderr=subprocess.DEVNULL
        ).decode('utf-8')

        packages = []
        for line in output.strip().split('\n'):
            parts = line.split('\t', 3)
            if len(parts) == 4:
                pkg = {
                    'name': parts[0],
                    'version': parts[1],
                    'architecture': parts[2],
                    'description': parts[3]
                }
                packages.append(pkg)
        return packages
    except subprocess.CalledProcessError:
        return []
        
def get_debian_packages() -> list[dict]:
    try:
        output = subprocess.check_output(
            ['dpkg-query', '-W', '-f=${Package}\t${Version}\t${Architecture}\t${Description}\n'],
            stderr=subprocess.DEVNULL
        ).decode('utf-8')

        packages = []
        for line in output.strip().split('\n'):
            parts = line.split('\t', 3)
            if len(parts) == 4:
                pkg = {
                    'name': parts[0],
                    'version': parts[1],
                    'architecture': parts[2],
                    'description': parts[3]
                }
                packages.append(pkg)
        return packages
    except subprocess.CalledProcessError:
        return []

# run one of the above functions after checking if we have deb or rpm packages
def get_installed_packages():
    try:
        if shutil.which("dpkg"):
            return get_debian_packages()
        elif shutil.which("rpm"):
            return get_rpm_packages()
        else:
            print("Unsupported package manager")
            return []
    except Exception as e:
        print(f"Failed to retrieve packages: {str(e)}")
        return []

def log_data(log_directory: str, ready_directory: str) -> NoReturn:
    interval: float = attr.get_config_value('Linux', 'SoftwareInterval', 43200.0, 'float')
    logger: LoggingModule = LoggingModule(log_directory, ready_directory, "SoftwareMonitor", "installed_software")
    while True:
        logger.check_logging_interval()
        packages = get_installed_packages()
        for pkg in packages:
            logger.write_log((
                    f"timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} | hostname: {hostname} | "
                    f"name: {pkg['name']} | version: {pkg['version']} | architecture: {pkg['architecture']} | "
                    f"description: {pkg['description']} | uuid: {uuid}"
                    ))
        logger.write_debug_log(f'timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} | '
                        f'hostname: {hostname} | source: software | platform: linux | event: progress | '
                        f'message: {logger.log_line_count} log lines written | value: {logger.log_line_count}')
        logger.clear_handlers()
        time.sleep(interval)

def run() -> NoReturn:
    log_directory: str = 'tmp-software-inventory' if attr.get_config_value('General', 'RunDatabaseOperations', False, 'bool') else 'tmp'
    ready_directory: str = 'ready'
    debug_generator_directory: str = 'debuggeneratorlogs'
    os.makedirs(debug_generator_directory, exist_ok=True)
    os.makedirs(log_directory, exist_ok=True)
    os.makedirs(ready_directory, exist_ok=True)
    log_data(log_directory, ready_directory)

run()