from datetime import datetime, timedelta
from win10toast import ToastNotifier
from pathlib import Path
import configparser
import os
import time
import subprocess
import psycopg
from sigma.collection import SigmaCollection
from sigma.rule import SigmaDetection, SigmaDetectionItem, SigmaRuleBase
from sigma.backends.sqlite import sqlite
from sigma.processing.resolver import ProcessingPipelineResolver

config = configparser.ConfigParser()
config.read(Path(__file__).parent.absolute() / "../agentconfig.ini")
config.read(Path(__file__).parent.absolute() / "../dbconfig.ini")
os_mode = config.get('General', 'OperatingSystem', fallback='Windows')
interval = config.getfloat('Augment', 'AlertGenInterval', fallback=43200.0)

toaster = ToastNotifier()
now = datetime.now()
search_interval = now - timedelta(seconds=interval)

# Format timestamps for comparison
time_format = "%Y-%m-%d %H:%M:%S"
date_prefix: str = now.strftime("%Y-%m-%d")  # Ensure we only check today’s logs

def clone_or_update_repo():
    repo_url = "https://github.com/SigmaHQ/sigma"
    local_path = "./sigma"
    if not os.path.exists(local_path):
        print(f"Cloning repository from {repo_url} to {local_path}")
        subprocess.run(['git', 'clone', repo_url, local_path])
    else:
        print(f"Repository already exists at {local_path}. Fetching latest changes...")
        # Check if it's a valid git repo
        git_dir = os.path.join(local_path, '.git')
        if not os.path.exists(git_dir):
            print("Error: Existing directory is not a valid Git repository.")
            return
        # Fetch and pull the latest changes
        subprocess.run(['git', 'fetch'], cwd=local_path)
        subprocess.run(['git', 'pull'], cwd=local_path)

def create_sigma_collection_from_repo() -> SigmaCollection:
    repo_path = Path("./sigma")
    rules_dir = repo_path / "rules"
    if not rules_dir.exists() or not rules_dir.is_dir():
        return []

    rule_files = [rule_path for rule_path in list(rules_dir.rglob(f"*.yml")) 
                if os_mode.lower() in str(rule_path) and ('process_creation' in str(rule_path) or 'network_connection'in str(rule_path)) 
                and ('win_susp_emoji_usage' not in str(rule_path))]
    return SigmaCollection.load_ruleset(
        inputs=rule_files,
        collect_errors=False,
        recursion_pattern="*/*.yml"
    )

def translate_sigma_to_sql(sigma_rule: SigmaRuleBase, type: str, initial_query: str):
    # Parse the Sigma rule and translate to SQL
    detections = []
    for key in sigma_rule.detection.detections.keys():
        detections.append(sigma_rule.detection.detections[key])

    detection_items = []
    for detection in detections:
        for item in list(detection.detection_items):
            if isinstance(item, SigmaDetection):
                detection_items.append(item.detection_items[0])
            elif isinstance(item, SigmaDetectionItem):
                detection_items.append(item)

    table_name = 'systemevents'
    res_query = initial_query.replace("<TABLE_NAME>", table_name).replace(" ESCAPE '\\'", "").replace('REGEXP', '~')
    options = [
        'timestamp', 'category', 'processid', 'process', 'hostname', 
        'parentprocessid', 'parentimage', 'username', 'dnsname', 'dnsdate', 
        'sourceip', 'sourceport', 'destinationip', 'destinationport', 
        'asname', 'status', 'image', 'commandline', 'sid'
    ]

    for item in detection_items:
        field = item.field.lower()
        if field == 'initiated':
            res_query = res_query.replace(item.field, field)
            ind = res_query.index('initiated')
            res_query = res_query.replace("initiated='true'", "").replace("initiated=true", "").replace("initiated='false'", "").replace("initiated=false", "")
            if 'AND' in res_query[ind-5:ind+5]:
                res_query = res_query[:ind-5] + res_query[ind-5:ind+5].replace(" AND ", "", 1) + res_query[ind+5:]
            continue
        elif field in ['sourcehostname', 'sourceisipv6', 'description', 'provider_name', 'company']:
            return ''
        elif field == 'originalfilename':
            field = 'process'
        elif field not in options:
            return ''
        res_query = res_query.replace(item.field, field)
    
    ind = res_query.index('WHERE')
    res_query = res_query[:ind+5] + f" timestamp >= '{search_interval}' AND timestamp < '{now}' AND" + res_query[ind+5:]
    return res_query

def send_notification(title, message) -> None:
    if os_mode == 'Windows':
        toaster.show_toast(title, message, duration=15, threaded=True)  # toast for 15 seconds

def run() -> None:
    clone_or_update_repo()
    rule_collection = create_sigma_collection_from_repo()
    piperesolver = ProcessingPipelineResolver()
    combined_pipeline = piperesolver.resolve(piperesolver.pipelines)
    sqlite_backend = sqlite.sqliteBackend(combined_pipeline)
    converted_collection = sqlite_backend.convert(rule_collection)
    while True:
        alerts_generated: int = 0
        for idx, rule in enumerate(rule_collection.rules):
            if 'process_creation' in str(rule.source):
                type = 'process'
            elif 'network_connection' in str(rule.source):
                type = 'network'

            query = translate_sigma_to_sql(rule, type, converted_collection[idx])
            if not query:
                continue

            matches = []

            try:
                with psycopg.connect(host=config.get('Database', 'HostName'), port=config.get('Database', 'PortNumber', fallback='4000'), dbname=config.get('Database', 'DatabaseName', fallback='opendr'),
                            user=config.get('Database', 'RootDatabaseUserName', fallback='postgres'), password=config.get('Database', 'RootDatabasePassword'), autocommit=True) as connection:
                    with connection.cursor() as cursor:
                        matches = cursor.execute(query).fetchall()
                    connection.close()
            except Exception as e:
                print(e)
                continue

            if not matches:
                continue

            send_notification(rule.title, rule.description)
            print("\n" + "="*50)
            print(f"{rule.title}\n{rule.description}")
            print("Matching log entries:\n")
            for match in matches:
                print(match)
            print("="*50)
            alerts_generated += len(matches)

        if alerts_generated:
            print(f"{alerts_generated} alerts were generated during the time period ({search_interval.strftime(time_format)} - {now.strftime(time_format)}).")
        else:
            print(f"No suspicious activity detected ({search_interval.strftime(time_format)} - {now.strftime(time_format)}).")

        time.sleep(interval)

run()
