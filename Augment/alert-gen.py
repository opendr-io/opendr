import re
import csv
from datetime import datetime, timedelta
from win10toast import ToastNotifier
from pathlib import Path
import configparser

config = configparser.ConfigParser()
config.read(Path(__file__).parent.absolute() / "../agentconfig.ini")
os_mode = config.get('General', 'OperatingSystem', fallback='Windows')

network_log = Path("tmp")
process_log = Path("tmp")
service_log = Path("ready")
endpoint_log = Path("ready")
user_log = Path("tmp")
driver_log = Path("ready")

toaster = ToastNotifier()
now = datetime.now()
search_interval = now - timedelta(hours=10)

# Format timestamps for comparison
time_format = "%Y-%m-%d %H:%M:%S"
date_prefix: str = now.strftime("%Y-%m-%d")  # Ensure we only check today’s logs

# search log files with a time filter
def search_log(directory_path: str, pattern: str, type: str ='') -> list[str]:
    matches = []

    directory = Path(directory_path)
    if not directory.is_dir():
        print(f"[!] Not a directory: {directory}. attempting to check default folder")
        if not Path('tmp').is_dir():
            return matches
        directory = Path('tmp')

    for file_path in directory.glob("*.log"):
        if type and type not in file_path.name:
            continue
        print(f"🔍 Reading file: {file_path}")

        with file_path.open("r", encoding="utf-8") as file:
            for line in file:
                timestamp_match = re.search(r"\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}", line)
                if timestamp_match:
                    log_time = datetime.strptime(timestamp_match.group(0), time_format)
                    if log_time >= search_interval and re.search(pattern, line, re.IGNORECASE):
                        matches.append(line.strip())

    return matches

# create toaster
def send_notification(title, message) -> None:
    if os_mode == 'Windows':
        toaster.show_toast(title, message, duration=15)  # toast for 15 seconds

def run() -> None:
    alerts_generated: int = 0
    with open(Path(__file__).parent.absolute() / 'alertrules.csv', encoding="utf8") as csvfile:
        reader = csv.DictReader(csvfile)
        for row in reader:
            match row['type']:
                case 'network':
                    matches = search_log(network_log, row['pattern'], row['type'])
                case 'process':
                    matches = search_log(process_log, row['pattern'], row['type'])
                case 'user':
                    matches = search_log(user_log, row['pattern'], row['type'])
                case 'endpoint':
                    matches = search_log(endpoint_log, row['pattern'], row['type'])
                case 'service':
                    matches = search_log(service_log, row['pattern'], row['type'])
                case 'driver':
                    matches = search_log(driver_log, row['pattern'], row['type'])
                case _:
                    continue

            if not matches:
                continue

            send_notification(row['title'], row['message'])
            print("\n" + "="*50)
            print(f"{row['title']}\n{row['message']}")
            print("Matching log entries:\n")
            for match in matches:
                print(match)
            print("="*50)
            alerts_generated += len(matches)

    if alerts_generated:
        print(f"{alerts_generated} alerts were generated during the time period ({search_interval.strftime(time_format)} - {now.strftime(time_format)}).")
    else:
        print(f"No suspicious activity detected ({search_interval.strftime(time_format)} - {now.strftime(time_format)}).")

run()