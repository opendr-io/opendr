import csv
from pathlib import Path
import argparse
import hashlib
import sys
from datetime import datetime

# Parse command line arguments
parser = argparse.ArgumentParser(description='Test alert rules against log entries')
parser.add_argument('--rule', type=str, help='Test only a specific rule by identifier')
parser.add_argument('--type', type=str, help='Test only rules of a specific type (network, process, user, etc.)')
parser.add_argument('--verbose', '-v', action='store_true', help='Show all log lines tested, not just matches')
parser.add_argument('--summary', '-s', action='store_true', help='Show only summary of matches by rule, skip detailed output')
parser.add_argument('--output', '-o', type=str, help='Write output to specified file (default: auto-generated timestamped file)')
parser.add_argument('--no-file', '-c', action='store_true', help='Do not write output to file (console only)')
args = parser.parse_args()

# Set correct directory paths relative to the script location
base_dir = Path(__file__).parent.parent.absolute()
tmp_dir = base_dir / "tmp"
ready_dir = base_dir / "ready"

# Create test results directory
test_results_dir = Path(__file__).parent.absolute() / "test-results"
test_results_dir.mkdir(exist_ok=True)

# Map log types to directories (both tmp and ready)
log_directories = {
    'network': [tmp_dir, ready_dir],
    'process': [tmp_dir, ready_dir],
    'user': [tmp_dir, ready_dir],
    'service': [tmp_dir, ready_dir],
    'endpoint': [tmp_dir, ready_dir],
    'driver': [tmp_dir, ready_dir]
}

class DualOutput:
    """Helper class to write to both console and file simultaneously."""
    def __init__(self, file_path=None):
        self.file = None
        self.file_path = file_path
        if file_path:
            self.file = open(file_path, 'w', encoding='utf-8')

    def print(self, text='', end='\n', flush=False):
        """Print to console and file."""
        # Print to console
        try:
            print(text, end=end, flush=flush)
        except UnicodeEncodeError:
            # Fallback for console
            print(text.encode('ascii', 'replace').decode('ascii'), end=end, flush=flush)

        # Write to file if enabled
        if self.file:
            self.file.write(text + end)
            if flush:
                self.file.flush()

    def close(self):
        """Close the output file."""
        if self.file:
            self.file.close()
            self.file = None

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

def is_false_positive(line: str, driver_hashes: set, service_hashes: set, process_fingerprints: list) -> bool:
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

def test_pattern_on_logs(pattern: str, directory_path: Path, log_type: str, show_progress: bool = True) -> tuple[list[str], int]:
    """Test a pattern against all log files in a directory.
    Returns (matches, total_lines_tested)"""
    matches = []
    total_lines = 0

    if not directory_path.is_dir():
        if show_progress:
            print(f"  [!] Directory not found: {directory_path}")
        return matches, total_lines

    # Parse the pattern into criteria
    criteria = parse_pattern(pattern)

    log_files = list(directory_path.glob("*.log"))
    if log_type:
        log_files = [f for f in log_files if log_type in f.name]

    if not log_files:
        if show_progress:
            print(f"  [!] No log files found in {directory_path}")
        return matches, total_lines

    if show_progress:
        print(f"  Testing against {len(log_files)} log file(s) in {directory_path}")

    for file_path in log_files:
        try:
            with file_path.open("r", encoding="utf-8") as file:
                for line_num, line in enumerate(file, 1):
                    total_lines += 1
                    if args.verbose:
                        print(f"    Line {line_num}: {line.strip()[:100]}...")

                    # Parse log line and check if it matches criteria
                    fields = parse_log_line(line)
                    if matches_criteria(fields, criteria):
                        matches.append(f"{file_path.name}:{line_num} - {line.strip()}")
                        if show_progress and not args.verbose:
                            print(f"    [+] Match in {file_path.name}:{line_num}")
        except Exception as e:
            print(f"  [!] Error reading {file_path.name}: {e}")

    return matches, total_lines

def main():
    # Determine output file path
    output_file = None
    if not args.no_file:
        if args.output:
            output_file = Path(args.output)
        else:
            # Auto-generate timestamped filename
            timestamp = datetime.now().strftime('%Y-%m-%d_%H-%M-%S')
            filter_str = f"_{args.rule}" if args.rule else f"_{args.type}" if args.type else ""
            output_file = test_results_dir / f"test_results{filter_str}_{timestamp}.txt"

    # Initialize dual output
    out = DualOutput(output_file)

    try:
        out.print("=" * 70)
        out.print("Alert Rules Tester")
        out.print("=" * 70)

        if output_file:
            out.print(f"Output will be written to: {output_file}")
            out.print()

        # Load false positive fingerprints
        fps_dir = Path(__file__).parent.absolute() / "fps"
        driver_hashes = load_fingerprint_hashes(fps_dir / "driver_hashes.txt")
        service_hashes = load_fingerprint_hashes(fps_dir / "services_hashes.txt")
        process_fingerprints = load_process_fingerprints(fps_dir / "process.txt")

        out.print(f"[FP Filter] Loaded {len(driver_hashes)} driver fingerprints")
        out.print(f"[FP Filter] Loaded {len(service_hashes)} service fingerprints")
        out.print(f"[FP Filter] Loaded {len(process_fingerprints)} process fingerprints")
        out.print()

        # Load alert rules
        alertrules_path = Path(__file__).parent.absolute() / 'alertrules.csv'
        if not alertrules_path.exists():
            out.print(f"[!] Alert rules file not found: {alertrules_path}")
            return

        total_rules_tested = 0
        total_matches = 0
        total_fp_filtered = 0
        matches_by_rule = {}  # Track matches per rule

        with open(alertrules_path, encoding="utf8") as csvfile:
            reader = csv.DictReader(csvfile)

            for row in reader:
                identifier = row['identifier']
                rule_type = row['type']
                pattern = row['pattern']
                title = row['title']

                # Apply filters
                if args.rule and identifier != args.rule:
                    continue
                if args.type and rule_type != args.type:
                    continue

                # Show rule header only if not in summary mode
                if not args.summary:
                    out.print(f"\n{'=' * 70}")
                    out.print(f"Testing Rule: {identifier}")
                    out.print(f"Type: {rule_type}")
                    out.print(f"Title: {title}")
                    out.print(f"Pattern: {pattern}")
                    out.print(f"{'-' * 70}")

                # Get the appropriate log directories
                log_dirs = log_directories.get(rule_type)
                if not log_dirs:
                    if not args.summary:
                        out.print(f"  [!] Unknown log type: {rule_type}")
                    continue

                # Show progress indicator in summary mode
                if args.summary:
                    out.print(f"Testing {identifier}...", end='', flush=True)

                # Test the pattern across all directories (tmp and ready)
                all_matches = []
                all_lines = 0
                for log_dir in log_dirs:
                    matches, total_lines = test_pattern_on_logs(pattern, log_dir, rule_type, show_progress=not args.summary)
                    all_matches.extend(matches)
                    all_lines += total_lines

                # Filter out false positives
                original_match_count = len(all_matches)
                filtered_matches = []
                for match in all_matches:
                    # Extract the log line from the match string (format: "filename:linenum - log_line")
                    log_line = match.split(' - ', 1)[1] if ' - ' in match else match
                    if not is_false_positive(log_line, driver_hashes, service_hashes, process_fingerprints):
                        filtered_matches.append(match)

                fp_count = original_match_count - len(filtered_matches)
                total_fp_filtered += fp_count

                if fp_count > 0 and not args.summary:
                    out.print(f"  [FP Filter] Filtered {fp_count} false positive(s)")

                all_matches = filtered_matches

                total_rules_tested += 1
                match_count = len(all_matches)
                total_matches += match_count
                matches_by_rule[identifier] = match_count

                # Show result in summary mode
                if args.summary:
                    status = "[+]" if match_count > 0 else "[-]"
                    out.print(f" {status} {match_count} matches")

                # Report results only if not in summary mode
                if not args.summary:
                    out.print(f"\n  Results:")
                    out.print(f"  - Lines tested: {all_lines}")
                    out.print(f"  - Matches found: {match_count}")

                    if all_matches:
                        out.print(f"\n  Matching entries:")
                        for match in all_matches:  # Show ALL matches
                            out.print(f"    {match}")
                    else:
                        out.print(f"  [!] No matches found for this rule")

        # Summary
        out.print(f"\n{'=' * 70}")
        out.print(f"Summary:")
        out.print(f"  Rules tested: {total_rules_tested}")
        out.print(f"  Total matches: {total_matches}")
        out.print(f"  False positives filtered: {total_fp_filtered}")
        out.print(f"\n  Matches by rule:")
        for rule_name, count in matches_by_rule.items():
            status = "[+]" if count > 0 else "[-]"
            out.print(f"    {status} {rule_name}: {count}")
        out.print(f"{'=' * 70}")

        if output_file:
            out.print(f"\nResults written to: {output_file}")

    finally:
        out.close()

if __name__ == "__main__":
    main()
