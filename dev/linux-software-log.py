import subprocess
import shutil
import os
import time
import common.attributes as attr
from common.logger import LoggingModule
from datetime import datetime

class LinuxSoftwareLogger(attr.LoggerParent):
    def __init__(self):
        super().__init__()
        self.interval: float = attr.get_config_value('Linux', 'SoftwareInterval', 60.0, 'float')
        self.previous_software: set = set()
        self.setup_logger()
        self.log_existing()
        print('LinuxSoftwareLogger Initialization complete')

    def setup_logger(self) -> None:
        log_directory: str = 'tmp-software-inventory' if attr.get_config_value('General', 'RunDatabaseOperations', False, 'bool') else 'tmp'
        ready_directory: str = 'ready'
        debug_generator_directory: str = 'debuggeneratorlogs'
        os.makedirs(debug_generator_directory, exist_ok=True)
        os.makedirs(log_directory, exist_ok=True)
        os.makedirs(ready_directory, exist_ok=True)
        self.logger: LoggingModule  = LoggingModule(log_directory, ready_directory, "SoftwareMonitor", "installed_software")

    @staticmethod
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

    @staticmethod
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
    def get_installed_packages(self):
        try:
            if shutil.which("dpkg"):
                return self.get_debian_packages()
            elif shutil.which("rpm"):
                return self.get_rpm_packages()
            else:
                print("Unsupported package manager")
                return []
        except Exception as e:
            print(f"Failed to retrieve packages: {str(e)}")
            return []

    def log_existing(self) -> None:
        packages = self.get_installed_packages()
        for pkg in packages:
            self.logger.write_log((
                    f"timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} | hostname: {self.hostname} | event: existing software | "
                    f"name: {pkg['name']} | version: {pkg['version']} | architecture: {pkg['architecture']} | "
                    f"description: {pkg['description']} | uuid: {self.sid}"
                    ))
            self.previous_software.add((pkg['name'], pkg['version']))

    def monitor_events(self) -> None:
        self.logger.check_logging_interval()
        packages = self.get_installed_packages()
        for pkg in packages:
            if (pkg['name'], pkg['version']) in self.previous_software:
                continue
            self.logger.write_log((
                    f"timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} | hostname: {self.hostname} | event: new software | "
                    f"name: {pkg['name']} | version: {pkg['version']} | architecture: {pkg['architecture']} | "
                    f"description: {pkg['description']} | uuid: {self.sid}"
                    ))
            self.previous_software.add((pkg['name'], pkg['version']))
        self.logger.write_debug_log(f"timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} | "
                        f"hostname: {self.hostname} | source: software | platform: linux | event: progress | "
                        f"message: {self.logger.log_line_count} log lines written | value: {self.logger.log_line_count}")

if __name__ == '__main__':
    software = LinuxSoftwareLogger()
    while True:
        software.monitor_events()
        time.sleep(software.interval)

