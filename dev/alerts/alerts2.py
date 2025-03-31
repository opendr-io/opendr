import re
from datetime import datetime, timedelta
from win10toast import ToastNotifier
from pathlib import Path

network_log = Path("tmp-network")
process_log = Path("tmp-process")

toaster = ToastNotifier()
now = datetime.now()
search_interval = now - timedelta(hours=10)

# Format timestamps for comparison
time_format = "%Y-%m-%d %H:%M:%S"
date_prefix = now.strftime("%Y-%m-%d")  # Ensure we only check today’s logs

# search log files with a time filter
def search_log(directory_path, pattern):
    matches = []

    directory = Path(directory_path)
    if not directory.is_dir():
        print(f"[!] Not a directory: {directory}")
        return matches

    for file_path in directory.glob("*.log"):
        print(f"🔍 Reading file: {file_path}")

        with file_path.open("r", encoding="utf-8") as file:
            for line in file:
                timestamp_match = re.search(r"\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}", line)
                if timestamp_match:
                    log_time = datetime.strptime(timestamp_match.group(0), time_format)
                    if log_time >= search_interval and re.search(pattern, line, re.IGNORECASE):
                        matches.append(line.strip())

    return matches

# alert one: python interpreter making internet connection
network_pattern = r"connection created.*process: python\.exe"
# alert two: python interpreter spawning a command shell
process_pattern = r"name:\s*cmd\.exe.*parent:\s*python\.exe"

# Search both logs
network_matches = search_log(network_log, network_pattern)
process_matches = search_log(process_log, process_pattern)

# create toaster
def send_notification(title, message):
    toaster.show_toast(title, message, duration=5)  # toast for 5 seconds

# process and print alerts
if network_matches:
    alert_title = "🚨 Python Internet Activity"
    alert_message = "python.exe created a connection. Check logs."
    send_notification(alert_title, alert_message)

    print("\n" + "="*50)
    print(f"{alert_title}\n{alert_message}")
    print("Matching log entries:\n")
    for network_match in network_matches:
        print(network_match)
    print("="*50)

if process_matches:
    alert_title = "⚠️ Python Shelled Out"
    alert_message = "python.exe ran cmd.exe. Check logs."
    send_notification(alert_title, alert_message)

    print("\n" + "="*50)
    print(f"{alert_title}\n{alert_message}")
    print("Matching log entries:\n")
    print("\n".join(process_matches))
    for process_match in process_matches:
        print(process_match)
    print("="*50)

if not (network_matches or process_matches):
    print(f"No suspicious activity detected ({search_interval.strftime(time_format)} - {now.strftime(time_format)}).")
