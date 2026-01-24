"""
Load logs from /tmp folder into a pandas DataFrame
"""

import pandas as pd
from pathlib import Path
import re
import configparser

def parse_log_line(line: str) -> dict:
    """Parse a pipe-separated log line into a dictionary of fields.

    Expected format: timestamp: ... | hostname: ... | username: ... | category: ... | ...

    The challenge is that commandline fields can contain pipes (|) as part of bash commands.
    We solve this by only recognizing fields that match known log field names.
    """
    fields = {}

    # Known field names in the log format
    KNOWN_FIELDS = {
        'timestamp', 'hostname', 'username', 'category', 'processid', 'process',
        'parentprocessid', 'parentimage', 'image', 'commandline', 'sid',
        'sourceip', 'sourceport', 'destinationip', 'destinationport', 'protocol',
        'event', 'servicename', 'displayname', 'executable', 'desc', 'signer',
        'friendly_name', 'is_signed', 'message'
    }

    # Split by pipe, but validate each part
    parts = line.split(" | ")

    # Track the current field being built (for handling multi-pipe values)
    current_key = None
    current_value = []

    for part in parts:
        if ": " in part:
            # Check if this looks like a new field
            potential_key = part.split(": ", 1)[0].strip()

            if potential_key in KNOWN_FIELDS:
                # Save previous field if exists
                if current_key:
                    fields[current_key] = " | ".join(current_value)

                # Start new field
                current_key = potential_key
                current_value = [part.split(": ", 1)[1].strip()]
            else:
                # This is part of the previous field's value (e.g., part of commandline)
                if current_key:
                    current_value.append(part)
        else:
            # No colon, so this is a continuation of the current field
            if current_key:
                current_value.append(part)

    # Save the last field
    if current_key:
        fields[current_key] = " | ".join(current_value)

    return fields

def load_logs_to_dataframe(log_dir: Path, log_type: str = None) -> pd.DataFrame:
    """
    Load all log files from a directory into a pandas DataFrame.

    Args:
        log_dir: Path to the directory containing log files
        log_type: Optional filter for specific log type (e.g., 'network', 'process', 'driver')

    Returns:
        DataFrame with all log entries
    """
    all_records = []

    # Get all .log files
    log_files = list(log_dir.glob("*.log"))

    # Filter by type if specified
    if log_type:
        log_files = [f for f in log_files if log_type in f.name]

    print(f"Loading {len(log_files)} log files from {log_dir}")

    for log_file in log_files:
        print(f"  Reading: {log_file.name}")

        try:
            with open(log_file, 'r', encoding='utf-8') as f:
                for line_num, line in enumerate(f, 1):
                    line = line.strip()
                    if not line or ' | ' not in line:
                        continue

                    # Parse the log line
                    fields = parse_log_line(line)

                    # Add metadata
                    fields['source_file'] = log_file.name
                    fields['line_number'] = line_num
                    fields['raw_line'] = line

                    all_records.append(fields)

        except Exception as e:
            print(f"  Error reading {log_file.name}: {e}")

    # Create DataFrame
    df = pd.DataFrame(all_records)

    print(f"\nLoaded {len(df)} log entries")
    if len(df) > 0:
        print(f"Columns: {', '.join(df.columns)}")
        print(f"\nLog types (category): {df['category'].value_counts().head(10).to_dict() if 'category' in df.columns else 'N/A'}")

    return df

if __name__ == "__main__":
    # Load configuration
    config_file = Path(__file__).parent / "log_loader_config.ini"
    config = configparser.ConfigParser()
    config.read(config_file)

    # Parse configuration
    log_dirs_str = config.get('Paths', 'log_directories', fallback='../tmp')
    log_dirs = [Path(__file__).parent / d.strip() for d in log_dirs_str.split(',') if d.strip()]
    output_dir = Path(__file__).parent / config.get('Paths', 'output_directory', fallback='.')

    log_types_str = config.get('LogTypes', 'log_types', fallback='process, network')
    log_types = [lt.strip() for lt in log_types_str.split(',') if lt.strip() and lt.strip().lower() != 'all']
    if not log_types or log_types_str.strip().lower() == 'all':
        log_types = ['process', 'network', 'service', 'driver', 'user', 'endpoint']

    export_csv = config.getboolean('OutputFormats', 'export_csv', fallback=True)
    export_tsv = config.getboolean('OutputFormats', 'export_tsv', fallback=True)
    export_parquet = config.getboolean('OutputFormats', 'export_parquet', fallback=True)
    csv_quoting = config.getint('OutputFormats', 'csv_quoting', fallback=1)
    parquet_compression = config.get('OutputFormats', 'parquet_compression', fallback='snappy')

    field_order_str = config.get('FieldOrdering', 'field_order', fallback='')
    desired_order = [f.strip() for f in field_order_str.split(',') if f.strip()]

    deduplicate = config.getboolean('Processing', 'deduplicate', fallback=True)
    sort_order = config.get('Processing', 'sort_by_timestamp', fallback='descending').lower()
    show_statistics = config.getboolean('Processing', 'show_statistics', fallback=True)

    # Create output directory if needed
    output_dir.mkdir(parents=True, exist_ok=True)

    print("="*70)
    print(f"Loading logs from {len(log_dirs)} director{'y' if len(log_dirs) == 1 else 'ies'}:")
    for log_dir in log_dirs:
        print(f"  - {log_dir}")
    print(f"Log types: {', '.join(log_types)}")
    print("="*70)

    # Load logs by type from all directories
    dataframes = []
    for log_dir in log_dirs:
        if not log_dir.exists():
            print(f"\nWarning: Directory not found: {log_dir}")
            continue

        for log_type in log_types:
            print(f"\nLoading {log_type} logs from {log_dir}...")
            df = load_logs_to_dataframe(log_dir, log_type=log_type)
            if len(df) > 0:
                dataframes.append(df)

    if not dataframes:
        print("\nNo logs found!")
        exit(0)

    # Combine all dataframes
    print("\nCombining dataframes...")
    df_all = pd.concat(dataframes, ignore_index=True)
    print(f"Total combined records: {len(df_all)}")

    # Deduplicate if enabled
    if deduplicate:
        print("\nDeduplicating records...")
        before_dedup = len(df_all)
        df_all = df_all.drop_duplicates(subset=df_all.columns.tolist(), keep='first')
        after_dedup = len(df_all)
        duplicates_removed = before_dedup - after_dedup
        print(f"Removed {duplicates_removed} duplicate records ({before_dedup} -> {after_dedup})")

    # Convert data types
    print("\nConverting data types...")

    # Convert timestamp to datetime
    df_all['timestamp'] = pd.to_datetime(df_all['timestamp'], errors='coerce')

    # Convert integer fields
    int_fields = ['processid', 'parentprocessid', 'sourceport', 'destinationport']
    for field in int_fields:
        if field in df_all.columns:
            df_all[field] = pd.to_numeric(df_all[field], errors='coerce').astype('Int64')

    print("Data types converted")

    # Sort by timestamp if enabled
    if sort_order in ['ascending', 'descending']:
        print(f"\nSorting by timestamp ({sort_order})...")
        df_all = df_all.sort_values('timestamp', ascending=(sort_order == 'ascending')).reset_index(drop=True)
        print(f"Sorted {len(df_all)} records by timestamp")

    # Reorder columns if specified
    if desired_order:
        print("\nReordering columns...")
        # Only include columns that exist in the dataframe
        column_order = [col for col in desired_order if col in df_all.columns]
        df_all = df_all[column_order]
        print(f"Reordered to: {', '.join(column_order)}")

    # Show DataFrame info if statistics enabled
    if show_statistics:
        print("\n" + "="*70)
        print("DataFrame Info:")
        print("="*70)
        print(df_all.info())

        print("\n" + "="*70)
        print("Sample records:")
        print("="*70)
        print(df_all.head())

    # Export to configured formats
    print("\n" + "="*70)
    print("Exporting data:")
    print("="*70)

    if export_csv:
        output_file = output_dir / "logs_dataframe.csv"
        df_all.to_csv(output_file, index=False, encoding='utf-8', quoting=csv_quoting)
        print(f"CSV saved to: {output_file}")

    if export_tsv:
        output_tsv = output_dir / "logs_dataframe.tsv"
        df_all.to_csv(output_tsv, index=False, encoding='utf-8', sep='\t')
        print(f"TSV saved to: {output_tsv}")

    if export_parquet:
        output_parquet = output_dir / "logs_dataframe.parquet"
        df_all.to_parquet(output_parquet, index=False, engine='pyarrow', compression=parquet_compression)
        print(f"Parquet saved to: {output_parquet}")

    # Show statistics if enabled
    if show_statistics:
        # Show breakdown by log type
        if 'category' in df_all.columns:
            print("\n" + "="*70)
            print("Breakdown by category:")
            print("="*70)
            print(df_all['category'].value_counts())

        # Show breakdown by process for network connections
        network_dfs = [df for df in dataframes if 'sourceip' in df.columns]
        if network_dfs:
            df_network = pd.concat(network_dfs, ignore_index=True)
            if 'process' in df_network.columns:
                print("\n" + "="*70)
                print("Network connections by process:")
                print("="*70)
                print(df_network['process'].value_counts().head(10))

        # Show process creation statistics
        process_dfs = [df for df in dataframes if 'commandline' in df.columns]
        if process_dfs:
            df_process = pd.concat(process_dfs, ignore_index=True)
            if 'process' in df_process.columns:
                print("\n" + "="*70)
                print("Process creation by process:")
                print("="*70)
                print(df_process['process'].value_counts().head(10))
