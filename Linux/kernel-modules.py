import subprocess
import os
import logging
from datetime import datetime

# Setup logging
log_dir = 'logs'
os.makedirs(log_dir, exist_ok=True)
log_file = os.path.join(log_dir, 'kernel_modules_detailed.log')
logging.basicConfig(filename=log_file, level=logging.INFO, format='%(message)s')

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

def get_module_info(module):
    try:
        result = subprocess.run(['modinfo', module], capture_output=True, text=True, check=True)
        lines = result.stdout.strip().splitlines()
        return {k.strip(): v.strip() for k, v in (line.split(':', 1) for line in lines if ':' in line)}
    except subprocess.CalledProcessError:
        return {}

def log_modules():
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    taint_val, taint_flags = get_kernel_taint_status()
    taint_info = f"tainted: {taint_val} | " + " | ".join([f"{flag}=True" for flag in taint_flags]) if taint_flags else "tainted: 0 | clean_kernel=True"

    for mod in get_module_list():
        info = get_module_info(mod)
        log_line = f"timestamp: {timestamp} | module: {mod} | {taint_info}"
        for key, value in info.items():
            log_line += f" | {key.lower().replace(' ', '_')}: {value}"
        logging.info(log_line)

log_modules()
