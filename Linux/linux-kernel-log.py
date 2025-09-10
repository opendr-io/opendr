import subprocess
import os
import time
from datetime import datetime
from typing import NoReturn
import common.attributes as attr
from common.logger import LoggingModule

# Kernel taint bits and their meaning
TAINT_FLAGS = {
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

def get_kernel_taint_status():
    try:
        with open('/proc/sys/kernel/tainted', 'r') as f:
            value = int(f.read().strip())
            flags = [TAINT_FLAGS[bit] for bit in TAINT_FLAGS if value & (1 << bit)]
            return value, flags
    except Exception:
        return 'unknown', []

def get_module_list():
    with open('/proc/modules', 'r') as f:
        return [line.split()[0] for line in f]

def get_module_info(module: str):
    try:
        result = subprocess.run(['modinfo', module], capture_output=True, text=True, check=True)
        lines = result.stdout.strip().splitlines()
        return {k.strip(): v.strip() for k, v in (line.split(':', 1) for line in lines if ':' in line)}
    except subprocess.CalledProcessError:
        return {}

def log_existing_modules(taint_info: str, logger: LoggingModule) -> list:
    seen_modules: list = []
    for mod in get_module_list():
        timestamp: str = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        info = get_module_info(mod)
        log_line: str = f"timestamp: {timestamp} | module: {mod} | event: existing kernel | {taint_info}"
        for key, value in info.items():
            log_line += f" | {key.lower().replace(' ', '_')}: {value}"
        
        logger.write_log(log_line)
        seen_modules.append(mod)
    return seen_modules

def log_modules(log_directory: str, ready_directory: str) -> NoReturn:
    interval: float = attr.get_config_value('Linux', 'KernelInterval', 60.0, 'float')
    logger = LoggingModule(log_directory, ready_directory, "KernelMonitor", "kernel")

    taint_val, taint_flags = get_kernel_taint_status()
    taint_info: str = f"tainted: {taint_val} | " + " | ".join([f"{flag}=True" for flag in taint_flags]) if taint_flags else "tainted: 0 | clean_kernel=True"
    
    prev_modules: list = log_existing_modules(taint_info, logger)
    while True:
        logger.check_logging_interval()
        for mod in get_module_list():
            if mod in prev_modules:
                continue
            timestamp: str = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            info = get_module_info(mod)
            log_line: str = f"timestamp: {timestamp} | module: {mod} | event: new kernel | {taint_info}"
            for key, value in info.items():
                log_line += f" | {key.lower().replace(' ', '_')}: {value}"
            logger.write_log(log_line)
            prev_modules.append(mod)
        logger.write_debug_log(f"timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} | "
                        f"hostname: {attr.get_hostname()} | source: kernel | platform: linux | event: progress | "
                        f"message: {logger.log_line_count} log lines written | value: {logger.log_line_count}")
        time.sleep(interval)

def run() -> NoReturn:
    log_directory: str = 'tmp-kernel' if attr.get_config_value('General', 'RunDatabaseOperations', False, 'bool') else 'tmp'
    ready_directory: str = 'ready'
    debug_generator_directory: str = 'debuggeneratorlogs'
    os.makedirs(debug_generator_directory, exist_ok=True)
    os.makedirs(log_directory, exist_ok=True)
    os.makedirs(ready_directory, exist_ok=True)
    print("kernel logging running")
    log_modules(log_directory, ready_directory)

if __name__ == "__main__":
    run()