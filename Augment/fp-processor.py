import hashlib
import csv
import ipaddress
from pathlib import Path

def parse_log_line(line: str) -> dict:
    """Parse a pipe-separated log line into a dictionary of fields."""
    fields = {}
    parts = line.split(" | ")
    for part in parts:
        if ": " in part:
            key, value = part.split(": ", 1)
            fields[key.strip()] = value.strip()
    return fields

def compute_driver_hash(fields: dict) -> str:
    """Compute hash for driver fingerprint fields: desc, signer, friendly_name, is_signed."""
    # Extract only the fingerprint fields
    desc = fields.get('desc', '')
    signer = fields.get('signer', '')
    friendly_name = fields.get('friendly_name', '')
    is_signed = fields.get('is_signed', '').upper()  # Normalize to uppercase

    # Create the line in CSV format (matching the CSV structure)
    line = f"new driver found,{desc},{signer},{friendly_name},{is_signed}"

    return hashlib.sha256(line.encode('utf-8')).hexdigest()

def compute_service_hash(fields: dict) -> str:
    """Compute hash for service fingerprint fields: event, servicename, displayname, executable."""
    # Extract only the fingerprint fields and strip quotes
    event = fields.get('event', '')
    servicename = fields.get('servicename', '').strip("'\"")  # Remove quotes
    displayname = fields.get('displayname', '').strip("'\"")  # Remove quotes
    executable = fields.get('executable', '').strip("'\"")  # Remove quotes

    # Create the line in CSV format (matching the CSV structure)
    line = f"{event},{servicename},{displayname},{executable}"

    return hashlib.sha256(line.encode('utf-8')).hexdigest()

def load_fingerprint_hashes(fp_file: Path) -> set:
    """Load all fingerprint hashes from a text file (one hash per line)."""
    hashes = set()

    with open(fp_file, 'r', encoding='utf-8') as f:
        for line in f:
            hash_value = line.strip()
            if hash_value:  # Skip empty lines
                hashes.add(hash_value)

    print(f"Loaded {len(hashes)} fingerprint hashes from {fp_file.name}")
    return hashes

def load_process_fingerprints(fp_file: Path) -> list:
    """Load process fingerprints from text file (each line is a full pattern)."""
    patterns = []

    with open(fp_file, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if line:  # Skip empty lines
                # Parse the line into a dictionary of fields
                fields = parse_log_line(line)
                patterns.append(fields)

    print(f"Loaded {len(patterns)} process fingerprints from {fp_file.name}")
    return patterns

def load_alert_rules(rules_file: Path) -> list:
    """Load alert rules from CSV file."""
    rules = []

    with open(rules_file, 'r', encoding='utf-8', newline='') as f:
        reader = csv.DictReader(f)
        for row in reader:
            rules.append(row)

    print(f"Loaded {len(rules)} alert rules from {rules_file.name}")
    return rules

def load_devtool_subnets(asn_file: Path) -> set:
    """Load subnets from ASN list for devtool network filtering."""
    subnets = set()

    with open(asn_file, 'r', encoding='utf-8', newline='') as f:
        reader = csv.DictReader(f)
        for row in reader:
            subnet = row.get('subnet', '').strip()
            if subnet and subnet != 'Error':
                try:
                    # Validate the subnet
                    ipaddress.ip_network(subnet, strict=False)
                    subnets.add(subnet)
                except ValueError:
                    pass  # Skip invalid subnets

    print(f"Loaded {len(subnets)} subnets from {asn_file.name}")
    return subnets

def ip_in_subnets(ip_str: str, subnets: set) -> bool:
    """Check if an IP address is in any of the given subnets."""
    try:
        ip = ipaddress.ip_address(ip_str)
        for subnet_str in subnets:
            try:
                subnet = ipaddress.ip_network(subnet_str, strict=False)
                if ip in subnet:
                    return True
            except ValueError:
                continue
        return False
    except ValueError:
        return False

def is_network_false_positive(log_line: str, alert_rules: list, devtool_subnets: set) -> bool:
    """Check if a network log line is a false positive (destination in known subnets).
    Returns True if the alert should be filtered out (is a false positive).
    """
    fields = parse_log_line(log_line)
    category = fields.get('category', '')

    # Only process network events
    if 'network' not in category.lower():
        return False

    # Check if this matches any DEVTOOL_NET alert rule
    for rule in alert_rules:
        if not rule['identifier'].endswith('_DEVTOOL_NET'):
            continue

        # Check if this log line matches the rule pattern
        if matches_alert_pattern(fields, rule['pattern']):
            # Check if destination IP is in known devtool subnets
            dest_ip = fields.get('destinationip', '')
            if dest_ip and ip_in_subnets(dest_ip, devtool_subnets):
                # Filter out this alert (known devtool traffic)
                return True
            break  # Only match one rule per event

    return False

def matches_alert_pattern(log_fields: dict, pattern: str) -> bool:
    """Check if log fields match an alert rule pattern."""
    # Parse pattern like "category: network_connection | network_existing, process: python.exe"
    pattern_parts = pattern.split(',')

    for part in pattern_parts:
        part = part.strip()
        if ': ' not in part:
            continue

        key, value = part.split(': ', 1)
        key = key.strip()
        value = value.strip()

        # Check for OR conditions (using |)
        if '|' in value:
            possible_values = [v.strip() for v in value.split('|')]
            log_value = log_fields.get(key, '')
            if not any(log_value == pv for pv in possible_values):
                return False
        else:
            # Exact match required
            if log_fields.get(key, '') != value:
                return False

    return True

def matches_process_fingerprint(log_fields: dict, fingerprint: dict) -> bool:
    """Check if log fields match all fields in the fingerprint."""
    for key, expected_value in fingerprint.items():
        if key not in log_fields:
            return False

        # Case-insensitive comparison
        if log_fields[key].lower() != expected_value.lower():
            return False

    return True

def process_test_results(test_file: Path, driver_hashes: set, service_hashes: set, process_fingerprints: list, alert_rules: list, devtool_subnets: set, debug: bool = False) -> dict:
    """Process test results and count matches against fingerprints."""
    stats = {
        'total_lines': 0,
        'driver_events': 0,
        'driver_matches': 0,
        'new_drivers': 0,
        'service_events': 0,
        'service_matches': 0,
        'new_services': 0,
        'process_events': 0,
        'process_matches': 0,
        'new_processes': 0,
        'network_alerts': 0,
        'network_filtered': 0,
        'driver_new_lines': [],
        'service_new_lines': [],
        'process_new_lines': [],
        'network_alert_lines': []
    }

    with open(test_file, 'r', encoding='utf-8') as f:
        for line in f:
            stats['total_lines'] += 1

            # Only process lines that look like log entries
            if ' | ' not in line:
                continue

            # Parse the log line
            fields = parse_log_line(line.strip())

            # Check if this is a driver event
            if fields.get('event') == 'new driver found':
                stats['driver_events'] += 1

                # Compute hash for this driver event
                driver_hash = compute_driver_hash(fields)

                # Check if it matches a known fingerprint
                if driver_hash in driver_hashes:
                    stats['driver_matches'] += 1
                else:
                    stats['new_drivers'] += 1
                    stats['driver_new_lines'].append({
                        'line': line.strip(),
                        'hash': driver_hash,
                        'fields': fields
                    })

            # Check if this is a service event
            elif fields.get('event') == 'new service':
                stats['service_events'] += 1

                # Compute hash for this service event
                service_hash = compute_service_hash(fields)

                # Check if it matches a known fingerprint
                if service_hash in service_hashes:
                    stats['service_matches'] += 1
                else:
                    stats['new_services'] += 1
                    stats['service_new_lines'].append({
                        'line': line.strip(),
                        'hash': service_hash,
                        'fields': fields
                    })

            # Check if this is a process creation event
            elif 'process_creation' in fields.get('category', '').lower():
                stats['process_events'] += 1

                # Check if it matches any process fingerprint
                matched = False
                for fingerprint in process_fingerprints:
                    if matches_process_fingerprint(fields, fingerprint):
                        stats['process_matches'] += 1
                        matched = True
                        break

                if not matched:
                    stats['new_processes'] += 1
                    stats['process_new_lines'].append({
                        'line': line.strip(),
                        'fields': fields
                    })

            # Check network events against DEVTOOL_NET alert rules
            category = fields.get('category', '')
            if 'network' in category.lower():
                for rule in alert_rules:
                    # Only process DEVTOOL_NET rules
                    if not rule['identifier'].endswith('_DEVTOOL_NET'):
                        continue

                    # Check if this log line matches the rule pattern
                    if matches_alert_pattern(fields, rule['pattern']):
                        # Check if destination IP is in known devtool subnets
                        dest_ip = fields.get('destinationip', '')
                        if dest_ip and ip_in_subnets(dest_ip, devtool_subnets):
                            # Filter out this alert (known devtool traffic)
                            stats['network_filtered'] += 1
                        else:
                            # This is a legitimate alert
                            stats['network_alerts'] += 1
                            stats['network_alert_lines'].append({
                                'line': line.strip(),
                                'fields': fields,
                                'rule': rule
                            })
                        break  # Only match one rule per event

    return stats

def main():
    base_dir = Path(__file__).parent.absolute()
    test_file = base_dir / "test-results-full.txt"
    driver_fp_file = base_dir / "fps" / "driver_hashes.txt"
    service_fp_file = base_dir / "fps" / "services_hashes.txt"
    process_fp_file = base_dir / "fps" / "process.txt"
    alert_rules_file = base_dir / "alertrules.csv"
    asn_list_file = base_dir / "fps" / "asn-list.csv"

    print("="*70)
    print("False Positive Processor")
    print("="*70)
    print(f"Test results file: {test_file}")
    print(f"Driver fingerprints: {driver_fp_file}")
    print(f"Service fingerprints: {service_fp_file}")
    print(f"Process fingerprints: {process_fp_file}")
    print(f"Alert rules: {alert_rules_file}")
    print(f"ASN list: {asn_list_file}")
    print()

    # Load fingerprint hashes
    driver_hashes = load_fingerprint_hashes(driver_fp_file)
    service_hashes = load_fingerprint_hashes(service_fp_file)
    process_fingerprints = load_process_fingerprints(process_fp_file)
    alert_rules = load_alert_rules(alert_rules_file)
    devtool_subnets = load_devtool_subnets(asn_list_file)
    print()

    # Process test results
    print("Processing test results...")
    stats = process_test_results(test_file, driver_hashes, service_hashes, process_fingerprints, alert_rules, devtool_subnets, debug=False)
    print()

    # Display results
    print("="*70)
    print("Results:")
    print("="*70)
    print(f"Total lines in test file: {stats['total_lines']}")
    print()
    print("DRIVER EVENTS:")
    print(f"  Events found: {stats['driver_events']}")
    print(f"  Matches with fingerprints: {stats['driver_matches']}")
    print(f"  New/unknown drivers: {stats['new_drivers']}")
    print()
    print("SERVICE EVENTS:")
    print(f"  Events found: {stats['service_events']}")
    print(f"  Matches with fingerprints: {stats['service_matches']}")
    print(f"  New/unknown services: {stats['new_services']}")
    print()
    print("PROCESS CREATION EVENTS:")
    print(f"  Events found: {stats['process_events']}")
    print(f"  Matches with fingerprints: {stats['process_matches']}")
    print(f"  New/unknown processes: {stats['new_processes']}")
    print()
    print("NETWORK DEVTOOL ALERTS:")
    print(f"  Alerts triggered: {stats['network_alerts']}")
    print(f"  Alerts filtered (known subnets): {stats['network_filtered']}")
    print()

    # Show driver matches
    if stats['driver_matches'] > 0:
        print(f"[+] {stats['driver_matches']} driver events matched known fingerprints (false positives)")

    if stats['new_drivers'] > 0:
        print(f"[!] {stats['new_drivers']} driver events did NOT match fingerprints (potentially suspicious)")
        print("New/Unknown Drivers:")
        for item in stats['driver_new_lines']:
            fields = item['fields']
            print(f"  - {fields.get('desc', 'Unknown')} | {fields.get('signer', 'Unknown')} | {fields.get('friendly_name', 'None')}")

    # Show service matches
    if stats['service_matches'] > 0:
        print(f"[+] {stats['service_matches']} service events matched known fingerprints (false positives)")

    if stats['new_services'] > 0:
        print(f"[!] {stats['new_services']} service events did NOT match fingerprints (potentially suspicious)")
        print("New/Unknown Services:")
        for item in stats['service_new_lines']:
            fields = item['fields']
            print(f"  - {fields.get('servicename', 'Unknown')} | {fields.get('displayname', 'Unknown')}")

    # Show process matches
    if stats['process_matches'] > 0:
        print(f"[+] {stats['process_matches']} process creation events matched known fingerprints (false positives)")

    if stats['new_processes'] > 0:
        print(f"[!] {stats['new_processes']} process creation events did NOT match fingerprints (potentially suspicious)")
        print("New/Unknown Processes:")
        for item in stats['process_new_lines']:
            fields = item['fields']
            print(f"  - {fields.get('process', 'Unknown')} | Parent: {fields.get('parentimage', 'Unknown')} | Cmdline: {fields.get('commandline', 'N/A')[:80]}")

    # Show network alerts
    if stats['network_filtered'] > 0:
        print(f"[+] {stats['network_filtered']} network alerts filtered (destination in known devtool subnets)")

    if stats['network_alerts'] > 0:
        print(f"[!] {stats['network_alerts']} network alerts triggered (destination NOT in known subnets)")
        print("Network Alerts:")
        for item in stats['network_alert_lines']:
            fields = item['fields']
            rule = item['rule']
            print(f"  - {rule['title']}: {fields.get('process', 'Unknown')} -> {fields.get('destinationip', 'Unknown')}:{fields.get('destinationport', 'N/A')}")

    print()
    print("="*70)

if __name__ == "__main__":
    main()
