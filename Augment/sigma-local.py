from datetime import datetime, timedelta
from pathlib import Path
import configparser
import os
import time
import subprocess
import re
from sigma.collection import SigmaCollection
from sigma.rule import SigmaDetection, SigmaDetectionItem, SigmaRuleBase

config = configparser.ConfigParser()
config.read(Path(__file__).parent.absolute() / "../agentconfig.ini")
os_mode = config.get('General', 'OperatingSystem', fallback='Windows')
interval = config.getfloat('Augment', 'AlertGenInterval', fallback=.864000)  # Default 24 hours for testing

# Log directory - change this to point to your tmp directory
LOG_DIR = Path(__file__).parent.parent.absolute() / "tmp"

# Rules directories - list of directories to search for Sigma rules
# Read from config file - MUST be configured in agentconfig.ini
def get_rules_directories():
    """Get rules directories from config file."""
    # Try to read from config
    config_key = f'{os_mode}RulesDirectories'
    if config.has_option('Augment', config_key):
        dirs_str = config.get('Augment', config_key)
        # Split by comma and strip whitespace
        dirs = [d.strip() for d in dirs_str.split(',') if d.strip()]
        if dirs:
            return dirs

    # No fallback - user must configure rules directories
    print(f"ERROR: No rules directories configured in agentconfig.ini")
    print(f"Please add '{config_key}=<directories>' to the [Augment] section")
    return []

RULES_DIRECTORIES = get_rules_directories()

time_format = "%Y-%m-%d %H:%M:%S"


class LogParser:
    """Parses log files from the tmp directory."""

    def __init__(self, log_dir: str):
        self.log_dir = log_dir
        self.logs = {
            'process': [],
            'network': []
        }

    def parse_line(self, line: str) -> dict:
        """Parse a single log line into a dictionary."""
        if not line.strip():
            return None

        # Split by pipe separator
        parts = line.split('|')
        entry = {}

        for part in parts:
            part = part.strip()
            if ':' in part:
                key, value = part.split(':', 1)
                entry[key.strip()] = value.strip()

        return entry if entry else None

    def load_logs(self):
        """Load process and network log files from the directory."""
        print(f"Loading logs from {self.log_dir}...")

        for filename in os.listdir(self.log_dir):
            if not filename.endswith('.log'):
                continue

            filepath = os.path.join(self.log_dir, filename)

            # Determine log type
            if filename.startswith('process_'):
                log_type = 'process'
            elif filename.startswith('network_'):
                log_type = 'network'
            else:
                continue

            print(f"  Reading {filename}...")
            try:
                with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
                    for line in f:
                        entry = self.parse_line(line)
                        if entry:
                            self.logs[log_type].append(entry)
            except Exception as e:
                print(f"    Warning: Error reading {filename}: {e}")

        print(f"\nLoaded:")
        print(f"  Process logs: {len(self.logs['process'])}")
        print(f"  Network logs: {len(self.logs['network'])}")


def clone_or_update_repo():
    """Clone or update the Sigma rules repository."""
    repo_url = "https://github.com/SigmaHQ/sigma"
    local_path = "./sigma"
    if not os.path.exists(local_path):
        print(f"Cloning repository from {repo_url} to {local_path}")
        subprocess.run(['git', 'clone', repo_url, local_path])
    else:
        print(f"Repository already exists at {local_path}. Fetching latest changes...")
        git_dir = os.path.join(local_path, '.git')
        if not os.path.exists(git_dir):
            print("Error: Existing directory is not a valid Git repository.")
            return
        subprocess.run(['git', 'fetch'], cwd=local_path, capture_output=True)
        subprocess.run(['git', 'pull'], cwd=local_path, capture_output=True)


def create_sigma_collection_from_repo(rules_directories=None) -> SigmaCollection:
    """
    Load Sigma rules for Windows process creation and network connections.

    Args:
        rules_directories: List of directories to search for rules.
                          Defaults to ["./sigma/rules"]
    """
    if rules_directories is None:
        rules_directories = ["./sigma/rules"]

    # Convert to Path objects and validate
    rules_dirs = []
    for dir_path in rules_directories:
        path = Path(dir_path)
        if path.exists() and path.is_dir():
            rules_dirs.append(path)
            print(f"  Found rules directory: {path}")
        else:
            print(f"  Warning: Rules directory not found: {path}")

    if not rules_dirs:
        print("  Error: No valid rules directories found")
        return SigmaCollection()

    # Collect rule files from all directories
    rule_files = []
    for rules_dir in rules_dirs:
        dir_rule_files = [rule_path for rule_path in list(rules_dir.rglob(f"*.yml"))
                    if os_mode.lower() in str(rule_path) and
                    ('process_creation' in str(rule_path) or 'network_connection' in str(rule_path))
                    and ('win_susp_emoji_usage' not in str(rule_path))]
        rule_files.extend(dir_rule_files)
        print(f"  Found {len(dir_rule_files)} rules in {rules_dir}")

    print(f"\nLoading {len(rule_files)} Sigma rules total...")
    return SigmaCollection.load_ruleset(
        inputs=rule_files,
        collect_errors=False,
        recursion_pattern="*/*.yml"
    )


def match_rule_against_logs(rule: SigmaRuleBase, logs: list, search_interval: datetime, now: datetime) -> list:
    """
    Match a Sigma rule against log entries.
    Returns a list of matching log entries.
    """
    matches = []

    # Get detection items from the rule
    detection_items = []
    for key in rule.detection.detections.keys():
        detection = rule.detection.detections[key]
        for item in list(detection.detection_items):
            if isinstance(item, SigmaDetection):
                detection_items.extend(item.detection_items)
            elif isinstance(item, SigmaDetectionItem):
                detection_items.append(item)

    # Iterate through log entries
    for entry in logs:
        # Check timestamp filter
        if 'timestamp' in entry:
            try:
                entry_time = datetime.strptime(entry['timestamp'], time_format)
                if entry_time < search_interval or entry_time >= now:
                    continue
            except ValueError:
                continue

        # Check if log entry matches all detection items
        entry_matches = True
        for det_item in detection_items:
            field = det_item.field.lower()

            # Map Sigma field names to log field names
            field_mapping = {
                'originalfilename': 'process',
                'image': 'image',
                'commandline': 'commandline',
                'parentimage': 'parentimage',
                'processid': 'processid',
                'parentprocessid': 'parentprocessid',
                'user': 'username',
                'destinationip': 'destinationip',
                'destinationport': 'destinationport',
                'sourceip': 'sourceip',
                'sourceport': 'sourceport',
            }

            mapped_field = field_mapping.get(field, field)

            # Skip fields not in our logs
            if mapped_field not in entry:
                entry_matches = False
                break

            # Get the value to match
            log_value = entry[mapped_field].lower() if entry[mapped_field] else ""

            # Check if any of the detection item values match
            item_matches = False
            for value in det_item.value:
                search_value = str(value).lower()

                # Simple substring or regex match
                if '*' in search_value or '?' in search_value:
                    # Wildcard pattern - convert to regex
                    # Escape special regex characters except * and ?
                    pattern = re.escape(search_value)
                    # Then replace escaped wildcards with regex equivalents
                    pattern = pattern.replace(r'\*', '.*').replace(r'\?', '.')
                    try:
                        if re.search(pattern, log_value):
                            item_matches = True
                            break
                    except re.error:
                        # If regex fails, fall back to substring match
                        if search_value.replace('*', '').replace('?', '') in log_value:
                            item_matches = True
                            break
                else:
                    # Exact or substring match
                    if search_value in log_value:
                        item_matches = True
                        break

            if not item_matches:
                entry_matches = False
                break

        if entry_matches:
            matches.append(entry)

    return matches


def write_alerts_to_file(alerts, now, max_matches=None):
    """Write alerts to the output file."""
    with open("sigma_alerts_local.txt", "a", encoding="utf-8") as f:
        f.write(f"\n{'=' * 80}\n")
        f.write(f"ALERT REPORT - {now.strftime(time_format)}\n")
        f.write(f"{'=' * 80}\n\n")

        for alert in alerts:
            rule = alert['rule']
            matches = alert['matches']
            log_type = alert['log_type']

            f.write(f"\n[ALERT] {rule.title}\n")
            f.write(f"Severity: {getattr(rule, 'level', 'unknown')}\n")
            f.write(f"Description: {rule.description}\n")
            f.write(f"Log Type: {log_type}\n")

            # Add false positives if available
            false_positives = getattr(rule, 'falsepositives', None)
            if false_positives:
                f.write(f"False Positives:\n")
                for fp in false_positives:
                    f.write(f"  - {fp}\n")

            f.write(f"Matches: {len(matches)}\n\n")
            f.write("Matching log entries:\n")

            # Determine how many matches to show
            if max_matches is None:
                matches_to_show = matches
            else:
                matches_to_show = matches[:max_matches]

            for match in matches_to_show:
                if log_type == 'process':
                    f.write(f"  {match.get('timestamp', 'N/A')} | "
                           f"PID: {match.get('processid', 'N/A')} | "
                           f"Process: {match.get('process', 'N/A')} | "
                           f"Parent: {match.get('parentimage', 'N/A')} | "
                           f"User: {match.get('username', 'N/A')} | "
                           f"Command: {match.get('commandline', 'N/A')[:500]}\n")
                elif log_type == 'network':
                    f.write(f"  {match.get('timestamp', 'N/A')} | "
                           f"Process: {match.get('process', 'N/A')} | "
                           f"Dest: {match.get('destinationip', 'N/A')}:{match.get('destinationport', 'N/A')}\n")

            # Show truncation message if applicable
            if max_matches is not None and len(matches) > max_matches:
                f.write(f"  ... and {len(matches) - max_matches} more matches\n")

            f.write("-" * 80 + "\n")


def run(max_matches=None, lookback_minutes=None, lookback_unlimited=False) -> None:
    """Main execution loop."""
    clone_or_update_repo()
    rule_collection = create_sigma_collection_from_repo(RULES_DIRECTORIES)

    print(f"\nLoaded {len(rule_collection.rules)} Sigma rules")
    print(f"Log directory: {LOG_DIR}")
    print(f"Rules directories: {', '.join(str(d) for d in RULES_DIRECTORIES)}")
    print(f"Alert check interval: {interval} seconds\n")

    while True:
        now = datetime.now()
        # Calculate search interval based on lookback parameters
        if lookback_unlimited:
            search_interval = datetime.min
        elif lookback_minutes is not None:
            search_interval = now - timedelta(minutes=lookback_minutes)
        else:
            search_interval = now - timedelta(seconds=interval)

        # Load logs from files
        parser = LogParser(LOG_DIR)
        parser.load_logs()

        alerts_generated = 0
        alerts = []

        print(f"\nChecking for suspicious activity ({search_interval.strftime(time_format)} - {now.strftime(time_format)})...")

        for rule in rule_collection.rules:
            # Determine log type
            if 'process_creation' in str(rule.source):
                log_type = 'process'
                logs = parser.logs['process']
            elif 'network_connection' in str(rule.source):
                log_type = 'network'
                logs = parser.logs['network']
            else:
                continue

            # Match rule against logs
            matches = match_rule_against_logs(rule, logs, search_interval, now)

            if matches:
                alerts.append({
                    'rule': rule,
                    'matches': matches,
                    'log_type': log_type
                })
                alerts_generated += len(matches)

        # Write alerts to file
        if alerts:
            write_alerts_to_file(alerts, now, max_matches)
            print(f"\n✓ {alerts_generated} alerts generated!")
            print(f"  Alerts written to: sigma_alerts_local.txt")
        else:
            print(f"\n✓ No suspicious activity detected")

        print(f"\nNext check in {interval} seconds...")
        time.sleep(interval)


if __name__ == "__main__":
    import sys
    sys.stdout.reconfigure(encoding='utf-8')

    # Show help if requested
    if '--help' in sys.argv or '-h' in sys.argv:
        print("""
Sigma Alert Detection for Local Log Files

Usage:
  python sigma-local.py [OPTIONS]

Options:
  --once                    Run a single check and exit (default: continuous monitoring)
  --max-matches N           Show N matches per alert (default: unlimited)
  --max-matches unlimited   Show all matches without limit
  --lookback N              Look back N minutes from current time (default: config value)
  --lookback unlimited      Scan all logs regardless of timestamp
  --help, -h               Show this help message

Examples:
  python sigma-local.py --once
  python sigma-local.py --once --max-matches 50
  python sigma-local.py --once --lookback 60
  python sigma-local.py --once --lookback unlimited
  python sigma-local.py --max-matches unlimited --lookback 120

The script reads logs from the tmp directory and writes alerts to sigma_alerts_local.txt
        """)
        sys.exit(0)

    # Parse command-line arguments
    run_once = '--once' in sys.argv

    # Parse --max-matches argument
    max_matches = None  # default (unlimited)
    for i, arg in enumerate(sys.argv):
        if arg == '--max-matches' and i + 1 < len(sys.argv):
            value = sys.argv[i + 1]
            if value.lower() in ['unlimited', 'all', 'infinite']:
                max_matches = None  # Show all matches
            else:
                try:
                    max_matches = int(value)
                except ValueError:
                    print(f"Warning: Invalid --max-matches value '{value}', using default (unlimited)")
                    max_matches = None
            break

    # Parse --lookback argument
    lookback_minutes = None  # default (use config interval)
    lookback_unlimited = False
    for i, arg in enumerate(sys.argv):
        if arg == '--lookback' and i + 1 < len(sys.argv):
            value = sys.argv[i + 1]
            if value.lower() in ['unlimited', 'all', 'infinite']:
                lookback_unlimited = True
            else:
                try:
                    lookback_minutes = float(value)
                except ValueError:
                    print(f"Warning: Invalid --lookback value '{value}', using default (config interval)")
                    lookback_minutes = None
            break

    if run_once:
        print("Running single alert check...\n")
        try:
            # Run the check logic once
            clone_or_update_repo()
            rule_collection = create_sigma_collection_from_repo(RULES_DIRECTORIES)

            print(f"\nLoaded {len(rule_collection.rules)} Sigma rules")
            print(f"Log directory: {LOG_DIR}")
            print(f"Rules directories: {', '.join(str(d) for d in RULES_DIRECTORIES)}\n")

            now = datetime.now()
            # Calculate search interval based on --lookback argument
            if lookback_unlimited:
                search_interval = datetime.min
            elif lookback_minutes is not None:
                search_interval = now - timedelta(minutes=lookback_minutes)
            else:
                search_interval = now - timedelta(seconds=interval)

            parser = LogParser(LOG_DIR)
            parser.load_logs()

            alerts_generated = 0
            alerts = []

            print(f"\nChecking for suspicious activity ({search_interval.strftime(time_format)} - {now.strftime(time_format)})...")

            for rule in rule_collection.rules:
                if 'process_creation' in str(rule.source):
                    log_type = 'process'
                    logs = parser.logs['process']
                elif 'network_connection' in str(rule.source):
                    log_type = 'network'
                    logs = parser.logs['network']
                else:
                    continue

                matches = match_rule_against_logs(rule, logs, search_interval, now)

                if matches:
                    alerts.append({
                        'rule': rule,
                        'matches': matches,
                        'log_type': log_type
                    })
                    alerts_generated += len(matches)

            if alerts:
                write_alerts_to_file(alerts, now, max_matches)
                print(f"\n✓ {alerts_generated} alerts generated!")
                print(f"  Alerts written to: sigma_alerts_local.txt")
            else:
                print(f"\n✓ No suspicious activity detected")

        except Exception as e:
            print(f"\nError: {e}")
            import traceback
            traceback.print_exc()
    else:
        try:
            run(max_matches, lookback_minutes, lookback_unlimited)
        except KeyboardInterrupt:
            print("\n\nStopping Sigma alert detection...")
        except Exception as e:
            print(f"\nError: {e}")
            import traceback
            traceback.print_exc()
