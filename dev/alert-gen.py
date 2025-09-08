import re
import csv
from datetime import datetime, timedelta
from win10toast import ToastNotifier
from pathlib import Path
import configparser

config = configparser.ConfigParser()
config.read(Path(__file__).parent.absolute() / "../agentconfig.ini")

class AlertGen():
    def __init__(self):
        self.toaster = ToastNotifier()
        self.time_format = "%Y-%m-%d %H:%M:%S"
        self.os_mode = config.get('General', 'OperatingSystem', fallback='Windows')
        self.interval = config.getfloat('Augment', 'AlertGenInterval', fallback=43200.0)
        self.rules: list = []
        self.search_interval = datetime.now() - timedelta(seconds=self.interval)
        self.paths: dict = {
            "endpoint": "tmp-endpoint-info",
            "network": "tmp-network",
            "process": "tmp-process",
            "tasks": "tmp-scheduled-tasks",
            "software": "tmp-software-inventory",
            "user": "tmp-user-info",
            "autorun": "tmp-windows-autoruns",
            "defender": "tmp-windows-defender",
            "driver": "tmp-windows-drivers",
            "service": "tmp-windows-service",
            "hotfix": "tmp-windows-autoruns"
        }
        self.populate_rules()
        print("AlertGen Initialization complete")
        
    def populate_rules(self):
        with open(Path(__file__).parent.absolute() / 'alertrules.csv', encoding="utf8") as csvfile:
            reader = csv.DictReader(csvfile)
            for row in reader:
                self.rules.append(row)

    # search log files with a time filter
    def search_log(self, directory_path: str, pattern: str, type: str ='') -> list[str]:
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
                        log_time = datetime.strptime(timestamp_match.group(0), self.time_format)
                        if log_time >= self.search_interval and re.search(pattern, line, re.IGNORECASE):
                            matches.append(line.strip())
        return matches

    def send_notification(self, title, message) -> None:
        if self.os_mode == 'Windows':
            self.toaster.show_toast(title, message, duration=15)  # toast for 15 seconds

    def augment_events(self) -> None:
        print("Running Augment alert")
        alerts_generated: int = 0
        for rule in self.rules:
            matches = self.search_log(self.paths[rule['type']], rule['pattern'], rule['type'])
            if not matches:
                continue

            self.send_notification(rule['title'], rule['message'])
            print("\n" + "="*50)
            print(f"{rule['title']}\n{rule['message']}")
            print("Matching log entries:\n")
            for match in matches:
                print(match)
            print("="*50)
            alerts_generated += len(matches)

        if alerts_generated:
            print(f"{alerts_generated} alerts were generated during the time period ({self.search_interval.strftime(self.time_format)} - {datetime.now().strftime(self.time_format)}).")
        else:
            print(f"No suspicious activity detected ({self.search_interval.strftime(self.time_format)} - {datetime.now().strftime(self.time_format)}).")
