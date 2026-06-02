import os
import psycopg
import subprocess
import json
import configparser
import pathlib
import time
from datetime import datetime, timedelta
import common.attributes as attr

config = configparser.ConfigParser()
config.read(pathlib.Path(__file__).parent.absolute() / "../dbconfig.ini")

if os.name != 'nt':
    sys.exit("platform not supported (Windows only)")

def get_signature_info(filepath):
    try:
        ps_script = f"""
        $sig = Get-AuthenticodeSignature -FilePath '{filepath}';
        $output = [PSCustomObject]@{{
            Status = $sig.Status.ToString()
            Signer = if ($sig.SignerCertificate) {{ $sig.SignerCertificate.Subject }} else {{ "None" }}
        }}
        $output | ConvertTo-Json -Compress
        """
        result = subprocess.run(["powershell", "-Command", ps_script], capture_output=True, text=True)
        result_json = result.stdout.strip()
        if result_json:
            data = json.loads(result_json)
            return data["Status"], data["Signer"]
        else:
            return "Unknown", "Unknown"
    except Exception as e:
        return "Error", str(e)

def fetch_unique_process(interval):
    with psycopg.connect(host=config.get('Database', 'HostName'), port=config.get('Database', 'PortNumber', fallback='4000'), dbname=config.get('Database', 'DatabaseName', fallback='opendr'),
                        user=config.get('Database', 'RootDatabaseUserName', fallback='postgres'), password=config.get('Database', 'RootDatabasePassword'), autocommit=True) as connection:
        with connection.cursor() as cursor:
            exes = cursor.execute(f"SELECT DISTINCT(exe, pid) FROM systemevents WHERE timestmp > '{(datetime.now() - timedelta(seconds=interval)).strftime('%Y-%m-%d %H:%M:%S')}'").fetchall()
        connection.close()
    return [exe[0] for exe in exes]

def enrich_process(exe, status, signer, interval):
    with psycopg.connect(host=config.get('Database', 'HostName'), port=config.get('Database', 'PortNumber', fallback='4000'), dbname=config.get('Database', 'DatabaseName', fallback='opendr'),
                        user=config.get('Database', 'RootDatabaseUserName', fallback='postgres'), password=config.get('Database', 'RootDatabasePassword'), autocommit=True) as connection:
        with connection.cursor() as cursor:
            cursor.execute(f"UPDATE systemevents SET status = '{status}', signer = '{signer}' WHERE exe = '{exe[0]}' AND pid = '{exe[1]}' AND timestmp > '{(datetime.now() - timedelta(seconds=interval)).strftime('%Y-%m-%d %H:%M:%S')}'")
        connection.commit()

def run():
    interval = attr.get_config_value('Augment', 'WinSignAugInterval', 43200.0, 'float')
    print('windows process signer enrichment running')
    while True:
        exes = fetch_unique_process(interval)
        for exe in exes:
            if not exe or not exe[0].lower().endswith(".exe"):
                continue
            status, signer = get_signature_info(exe[0])
            enrich_process(exe, status, signer, interval)
        time.sleep(interval)

run()
