import re
import csv
from datetime import datetime, timedelta
try:
    from win10toast import ToastNotifier
    TOAST_AVAILABLE = True
except ImportError:
    TOAST_AVAILABLE = False
    ToastNotifier = None
from pathlib import Path
import configparser
import time
import argparse
import sys
import hashlib
sys.path.append(str(Path(__file__).parent.absolute()))
from common.logger import setup_logging, check_logging_interval

# Import network filtering from fp-processor
try:
    import importlib.util
    spec = importlib.util.spec_from_file_location("fp_processor", Path(__file__).parent / "fp-processor.py")
    fp_processor = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(fp_processor)

    load_devtool_subnets = fp_processor.load_devtool_subnets
    load_alert_rules = fp_processor.load_alert_rules
    is_network_false_positive = fp_processor.is_network_false_positive

    FP_PROCESSOR_AVAILABLE = True
except Exception as e:
    FP_PROCESSOR_AVAILABLE = False
    print(f"[!] Warning: Could not import fp-processor module. Network filtering will be disabled. Error: {e}")

config = configparser.ConfigParser()
config.read(Path(__file__).parent.absolute() / "../agentconfig.ini")
os_mode = config.get('General', 'OperatingSystem', fallback='Windows')
interval = config.getfloat('Augment', 'AlertGenInterval', fallback=43200.0)
enable_notifications = config.getboolean('Augment', 'EnableNotifications', fallback=False)

# Parse command line arguments
parser = argparse.ArgumentParser(description='Alert generation script for monitoring log files')
parser.add_argument('--once', action='store_true',
                    help='Run once with unlimited lookback instead of running in a loop')
args = parser.parse_args()

# Set correct directory paths relative to the script location
base_dir = Path(__file__).parent.parent.absolute()
network_log = base_dir / "tmp"
process_log = base_dir / "tmp"
service_log = base_dir / "ready"
endpoint_log = base_dir / "ready"
user_log = base_dir / "tmp"
driver_log = base_dir / "ready"
autorun_log = base_dir / "ready"

# Create alerts directories for logging
alerts_tmp_dir = base_dir / "alerts" / "tmp"
alerts_ready_dir = base_dir / "alerts" / "ready"
alerts_tmp_dir.mkdir(parents=True, exist_ok=True)
alerts_ready_dir.mkdir(parents=True, exist_ok=True)

toaster = ToastNotifier() if TOAST_AVAILABLE else None

# Format timestamps for comparison
time_format = "%Y-%m-%d %H:%M:%S"

# Initialize logger variables for loop mode
logger = None
last_interval = None

def parse_log_line(line: str) -> dict:
    """Parse a pipe-separated log line into a dictionary of fields."""
    fields = {}
    parts = line.split(" | ")
    for part in parts:
        if ": " in part:
            key, value = part.split(": ", 1)
            fields[key.strip()] = value.strip()
    return fields

def load_fingerprint_hashes(fp_file: Path) -> set:
    """Load all fingerprint hashes from a text file (one hash per line)."""
    hashes = set()
    if not fp_file.exists():
        return hashes

    with open(fp_file, 'r', encoding='utf-8') as f:
        for line in f:
            hash_value = line.strip()
            if hash_value:  # Skip empty lines
                hashes.add(hash_value)

    return hashes

def load_process_fingerprints(fp_file: Path) -> list:
    """Load process fingerprints from text file (each line is a full pattern)."""
    patterns = []
    if not fp_file.exists():
        return patterns

    with open(fp_file, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if line:  # Skip empty lines
                # Parse the line into a dictionary of fields
                fields = parse_log_line(line)
                patterns.append(fields)

    return patterns

def compute_driver_hash(fields: dict) -> str:
    """Compute hash for driver fingerprint fields: desc, signer, friendly_name, is_signed."""
    desc = fields.get('desc', '')
    signer = fields.get('signer', '')
    friendly_name = fields.get('friendly_name', '')
    is_signed = fields.get('is_signed', '').upper()  # Normalize to uppercase

    line = f"new driver found,{desc},{signer},{friendly_name},{is_signed}"
    return hashlib.sha256(line.encode('utf-8')).hexdigest()

def compute_service_hash(fields: dict) -> str:
    """Compute hash for service fingerprint fields: event, servicename, displayname, executable."""
    event = fields.get('event', '')
    servicename = fields.get('servicename', '').strip("'\"")  # Remove quotes
    displayname = fields.get('displayname', '').strip("'\"")  # Remove quotes
    executable = fields.get('executable', '').strip("'\"")  # Remove quotes

    line = f"{event},{servicename},{displayname},{executable}"
    return hashlib.sha256(line.encode('utf-8')).hexdigest()

def matches_process_fingerprint(log_fields: dict, fingerprint: dict) -> bool:
    """Check if log fields match all fields in the fingerprint."""
    for key, expected_value in fingerprint.items():
        if key not in log_fields:
            return False

        # Case-insensitive comparison
        if log_fields[key].lower() != expected_value.lower():
            return False

    return True

def is_false_positive(line: str, driver_hashes: set, service_hashes: set, process_fingerprints: list,
                      alert_rules: list = None, devtool_subnets: set = None) -> bool:
    """Check if a log line is a false positive."""
    fields = parse_log_line(line)

    # Check driver events
    if fields.get('event') == 'new driver found':
        driver_hash = compute_driver_hash(fields)
        return driver_hash in driver_hashes

    # Check service events
    elif fields.get('event') == 'new service':
        service_hash = compute_service_hash(fields)
        return service_hash in service_hashes

    # Check process creation events
    elif 'process_creation' in fields.get('category', '').lower():
        for fingerprint in process_fingerprints:
            if matches_process_fingerprint(fields, fingerprint):
                return True
        return False

    # Check network events (if fp-processor is available)
    elif 'network' in fields.get('category', '').lower():
        if FP_PROCESSOR_AVAILABLE and alert_rules is not None and devtool_subnets is not None:
            return is_network_false_positive(line, alert_rules, devtool_subnets)

    return False

def matches_criteria(fields: dict, criteria: dict) -> bool:
    """Check if log fields match all criteria (case-insensitive).
    Criteria format: {'field_name': 'value'} or {'field_name': ['value1', 'value2']}
    """
    for key, expected in criteria.items():
        if key not in fields:
            return False

        actual_value = fields[key].lower()

        # Handle list of acceptable values (OR condition)
        if isinstance(expected, list):
            if not any(exp.lower() in actual_value for exp in expected):
                return False
        else:
            # Single value - check if it's contained in the field
            if expected.lower() not in actual_value:
                return False

    return True

def parse_pattern(pattern: str) -> dict:
    """Parse pattern string into criteria dictionary.
    Format: 'field1: value1, field2: value2' or 'field1: value1 | value2, field2: value3'
    """
    criteria = {}
    # Split by comma to get field:value pairs
    pairs = pattern.split(", ")

    for pair in pairs:
        if ": " not in pair:
            continue

        field, value = pair.split(": ", 1)
        field = field.strip()
        value = value.strip()

        # Check if value contains OR condition (pipe)
        if " | " in value:
            criteria[field] = [v.strip() for v in value.split(" | ")]
        else:
            criteria[field] = value

    return criteria

# search log files with a time filter
def search_log(directory_path: Path, pattern: str, type: str ='', search_interval=None) -> list[str]:
    matches = []

    print(f"Searching in directory: {directory_path}")

    if not directory_path.is_dir():
        print(f"[!] Directory not found: {directory_path}")
        return matches

    # Parse the pattern into criteria
    criteria = parse_pattern(pattern)

    for file_path in directory_path.glob("*.log"):
        if type and type not in file_path.name:
            continue
        print(f"Reading file: {file_path.name}")

        try:
            with file_path.open("r", encoding="utf-8") as file:
                for line in file:
                    timestamp_match = re.search(r"\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}", line)
                    if timestamp_match:
                        log_time = datetime.strptime(timestamp_match.group(0), time_format)
                        # If search_interval is None (unlimited lookback), include all entries
                        if search_interval is None or log_time >= search_interval:
                            # Parse log line and check if it matches criteria
                            fields = parse_log_line(line)
                            if matches_criteria(fields, criteria):
                                matches.append(line.strip())
        except Exception as e:
            print(f"[!] Error reading file {file_path.name}: {e}")

    return matches

# create toaster
def send_notification(title, message) -> None:
    if enable_notifications and os_mode == 'Windows' and TOAST_AVAILABLE and toaster:
        toaster.show_toast(title, message, duration=15)  # toast for 15 seconds

def run() -> None:
    global logger, last_interval

    # Load false positive fingerprints at startup
    fps_dir = Path(__file__).parent.absolute() / "fps"
    driver_hashes = load_fingerprint_hashes(fps_dir / "driver_hashes.txt")
    service_hashes = load_fingerprint_hashes(fps_dir / "services_hashes.txt")
    process_fingerprints = load_process_fingerprints(fps_dir / "process.txt")

    print(f"[FP Filter] Loaded {len(driver_hashes)} driver fingerprints")
    print(f"[FP Filter] Loaded {len(service_hashes)} service fingerprints")
    print(f"[FP Filter] Loaded {len(process_fingerprints)} process fingerprints")

    # Load network filtering data
    network_alert_rules = None
    devtool_subnets = None
    if FP_PROCESSOR_AVAILABLE:
        alertrules_path = Path(__file__).parent.absolute() / 'alertrules.csv'
        asn_list_path = fps_dir / 'asn-list.csv'
        if alertrules_path.exists() and asn_list_path.exists():
            network_alert_rules = load_alert_rules(alertrules_path)
            devtool_subnets = load_devtool_subnets(asn_list_path)
            print(f"[FP Filter] Loaded {len(devtool_subnets)} network subnets for filtering")
        else:
            print("[FP Filter] Network filtering disabled (missing alertrules.csv or asn-list.csv)")

    print()

    while True:
        alerts_generated: int = 0
        fp_filtered: int = 0  # Count of false positives filtered
        now = datetime.now()
        once_output = []  # Collect output for --once mode

        # Determine search interval based on mode
        if args.once:
            search_interval = None  # Unlimited lookback
            interval_str = "unlimited lookback"
        else:
            search_interval = now - timedelta(seconds=interval)
            interval_str = f"{search_interval.strftime(time_format)} to {now.strftime(time_format)}"

            # Check if we need to rotate the log file (only in loop mode)
            logger, last_interval = check_logging_interval(
                str(alerts_tmp_dir),
                str(alerts_ready_dir),
                'alert_generator',
                'alerts',
                logger,
                last_interval
            )

        # Print directory paths for debugging
        print(f"Directory paths:")
        print(f"   Network logs: {network_log}")
        print(f"   Process logs: {process_log}")
        print(f"   User logs: {user_log}")
        print(f"   Service logs: {service_log}")
        print(f"   Endpoint logs: {endpoint_log}")
        print(f"   Driver logs: {driver_log}")
        print(f"   Search interval: {interval_str}")
        print()

        with open(Path(__file__).parent.absolute() / 'alertrules.csv', encoding="utf8") as csvfile:
            reader = csv.DictReader(csvfile)
            for row in reader:
                if row['type'] == 'network':
                    matches = search_log(network_log, row['pattern'], row['type'], search_interval)
                elif row['type'] == 'process':
                    matches = search_log(process_log, row['pattern'], row['type'], search_interval)
                elif row['type'] == 'user':
                    matches = search_log(user_log, row['pattern'], row['type'], search_interval)
                elif row['type'] == 'endpoint':
                    matches = search_log(endpoint_log, row['pattern'], row['type'], search_interval)
                elif row['type'] == 'service':
                    matches = search_log(service_log, row['pattern'], row['type'], search_interval)
                elif row['type'] == 'driver':
                    matches = search_log(driver_log, row['pattern'], row['type'], search_interval)
                elif row['type'] == 'autorun':
                    matches = search_log(autorun_log, row['pattern'], 'autoruns', search_interval)
                else:
                    continue

                if not matches:
                    continue

                # Filter out false positives
                original_count = len(matches)
                filtered_matches = [m for m in matches if not is_false_positive(m, driver_hashes, service_hashes, process_fingerprints,
                                                                                network_alert_rules, devtool_subnets)]
                fp_count = original_count - len(filtered_matches)
                fp_filtered += fp_count

                if fp_count > 0:
                    print(f"[FP Filter] Filtered {fp_count} false positive(s) for rule {row['identifier']}")

                # Skip this alert if all matches were filtered out
                if not filtered_matches:
                    continue

                # Send notification only in loop mode
                if not args.once:
                    send_notification(row['title'], row['message'])

                # Format alert output
                alert_output = f"\n{'='*50}\n{row['title']}\n{row['message']}\nMatching log entries:\n\n"
                for match in filtered_matches:
                    alert_output += f"{match}\n"
                alert_output += f"{'='*50}\n"

                # Print to console (handle unicode errors on Windows)
                try:
                    print(alert_output)
                except UnicodeEncodeError:
                    # Fallback to ASCII if Unicode fails
                    print(alert_output.encode('ascii', 'replace').decode('ascii'))

                # Write to logger if in loop mode, or collect for once mode
                if args.once:
                    once_output.append(alert_output)
                elif logger:
                    logger.info(alert_output)

                alerts_generated += len(filtered_matches)

        # Log summary
        summary = ""
        if alerts_generated:
            summary = f"{alerts_generated} alerts were generated during the time period ({interval_str})."
            if fp_filtered > 0:
                summary += f" {fp_filtered} false positive(s) were filtered out."
        else:
            summary = f"No suspicious activity detected ({interval_str})."
            if fp_filtered > 0:
                summary += f" {fp_filtered} false positive(s) were filtered out."

        print(summary)

        # Write summary to logger if in loop mode, or collect for once mode
        if args.once:
            once_output.append(summary)
        elif logger:
            logger.info(summary)

        # If running once, write output to file and exit
        if args.once:
            output_filename = alerts_ready_dir / f"alerts_{now.strftime('%Y-%m-%d_%H-%M-%S')}.log"
            with open(output_filename, 'w', encoding='utf-8') as f:
                f.write('\n'.join(once_output))
            print(f"\nOutput written to: {output_filename}")
            break

        time.sleep(interval)

run()