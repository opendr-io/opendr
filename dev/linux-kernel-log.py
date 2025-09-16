import subprocess
import os
import time
from datetime import datetime
import common.attributes as attr
from common.logger import LoggingModule

class LinuxKernelLogger(attr.LoggerParent):
    def __init__(self):
        super().__init__()
        self.TAINT_FLAGS = {
            0: 'proprietary_module',
            1: 'force_loaded',
            2: 'smp_with_up',
            3: 'user_taint',
            4: 'unsigned_module',
            5: 'oops_taint',
            6: 'hardware_problem',
            7: 'soft_lockup',
            8: 'firmware_bug',
            9: 'out_of_tree_module',
            10: 'unsigned_module_forced',
            11: 'live_patching',
            12: 'auxiliary_locking',
            13: 'unknown_taint_bit13'
            # Add more if necessary based on future kernel definitions
        }
        self.interval: float = attr.get_config_value('Linux', 'KernelInterval', 60.0, 'float')
        self.previous_modules: set = set()
        self.setup_logger()
        self.log_existing()
        print('LinuxKernelLogger Initialization complete')

    def setup_logger(self) -> None:
        log_directory: str = 'tmp-endpoint-info' if attr.get_config_value('General', 'RunDatabaseOperations', False, 'bool') else 'tmp'
        ready_directory: str = 'ready'
        debug_generator_directory: str = 'debuggeneratorlogs'
        os.makedirs(debug_generator_directory, exist_ok=True)
        os.makedirs(log_directory, exist_ok=True)
        os.makedirs(ready_directory, exist_ok=True)
        self.logger: LoggingModule = LoggingModule(log_directory, ready_directory, "KernelMonitor", "kernel")

    def get_kernel_taint_status(self):
        try:
            with open('/proc/sys/kernel/tainted', 'r') as f:
                value = int(f.read().strip())
                flags = [self.TAINT_FLAGS[bit] for bit in self.TAINT_FLAGS if value & (1 << bit)]
                return value, flags
        except Exception:
            return 'unknown', []

    @staticmethod
    def get_module_list():
        with open('/proc/modules', 'r') as f:
            return [line.split()[0] for line in f]

    @staticmethod
    def get_module_info(module: str):
        try:
            result = subprocess.run(['modinfo', module], capture_output=True, text=True, check=True)
            lines = result.stdout.strip().splitlines()
            return {k.strip(): v.strip() for k, v in (line.split(':', 1) for line in lines if ':' in line)}
        except subprocess.CalledProcessError:
            return {}

    def log_existing(self) -> None:
        taint_val, taint_flags = self.get_kernel_taint_status()
        taint_info: str = f"tainted: {taint_val} | " + " | ".join([f"{flag}=True" for flag in taint_flags]) if taint_flags else "tainted: 0 | clean_kernel=True"
    
        for mod in self.get_module_list():
            if mod in self.previous_modules:
                continue
            timestamp: str = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            info = self.get_module_info(mod)
            log_line: str = f"timestamp: {timestamp} | module: {mod} | event: existing kernel | {taint_info}"
            for key, value in info.items():
                log_line += f" | {key.lower().replace(' ', '_')}: {value}"
            
            self.logger.write_log(log_line)
            self.previous_modules.add(mod)

    def monitor_events(self) -> None:
        taint_val, taint_flags = self.get_kernel_taint_status()
        taint_info: str = f"tainted: {taint_val} | " + " | ".join([f"{flag}=True" for flag in taint_flags]) if taint_flags else "tainted: 0 | clean_kernel=True"

        self.logger.check_logging_interval()
        for mod in self.get_module_list():
            if mod in self.previous_modules:
                continue
            timestamp: str = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            info = self.get_module_info(mod)
            log_line: str = f"timestamp: {timestamp} | module: {mod} | event: new kernel | {taint_info}"
            for key, value in info.items():
                log_line += f" | {key.lower().replace(' ', '_')}: {value}"
            self.logger.write_log(log_line)
            self.previous_modules.add(mod)
        self.logger.write_debug_log(f"timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} | "
                        f"hostname: {attr.get_hostname()} | source: kernel | platform: linux | event: progress | "
                        f"message: {self.logger.log_line_count} log lines written | value: {self.logger.log_line_count}")

if __name__ == '__main__':
    kernel = LinuxKernelLogger()
    while True:
        kernel.monitor_events()
        time.sleep(kernel.interval)
