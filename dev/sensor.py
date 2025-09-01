import psycopg
import sys
import configparser
import pathlib
from importlib import import_module
import time
import schedule
import threading

config = configparser.ConfigParser()
config.read(pathlib.Path(__file__).parent.absolute() / "agentconfig.ini")
config.read(pathlib.Path(__file__).parent.absolute() / "dbconfig.ini")

def dynamic_imp(name, class_name):
    try:
        imp_module = import_module(name)
    except Exception as e:
        print(e)
        return None
    try:
        imp_class = getattr(imp_module, class_name)
    except Exception as e:
        print(e)
        return None
    return imp_class()

os_mode: str = config.get('General', 'OperatingSystem', fallback='Windows')
os_log: dict[str, list[str]] = {
    "Windows": ['process', 'network', 'software', 'user', 'service'],
    # "Windows": ['process', 'network', 'software', 'user', 'endpoint', 'service', 'hotfix', 'driver',  'defender', 'autorun', 'tasks'],
    "Linux": ['process', 'network', 'software', 'user', 'endpoint', 'service', 'cronjob', 'kernel'],
    "MacOS": ['process', 'network', 'user', 'endpoint']
}
log_profiles: dict[str, list[str]] = {
    "basic": os_log[os_mode][:3],
    "advanced": os_log[os_mode][:6],
    "complete": os_log[os_mode],
    "custom": config.get(os_mode, 'Scripts', fallback='').split(', ')
}
augment_profiles: list[str] = ["network-aug", "alert-gen"]

def test_connection() -> None:
    try:
        with psycopg.connect(host=config.get('Database', 'HostName'), port=config.get('Database', 'PortNumber', fallback='4000'),
                        dbname=config.get('Database', 'DatabaseName', fallback='opendr'),
                        user=config.get('Database', 'RootDatabaseUserName', fallback='postgres'), password=config.get('Database', 'RootDatabasePassword'),
                        sslmode=config.get('Database', 'SSLMode'), sslrootcert=config.get('Database', 'SSLRootCert')) as connection:
            _ = connection.cursor()
            connection.close()
    except Exception as e:
        print(e)
        sys.exit(1)

def execute_scripts(func):
    t = threading.Thread(target=func)
    t.start()

def run() -> None:
    path_sep = '\\' if os_mode == 'Windows' else '/'
    file_path = os_mode.lower() + '-'
    logging_scripts = log_profiles[config.get('General', 'LogProfile', fallback='basic')]
    generators = [file_path + script + '-log' for script in logging_scripts]
    classes = [os_mode + script.capitalize() + 'Logger' for script in logging_scripts]
    for i in range(len(generators)):
        test = dynamic_imp(generators[i], classes[i])
        schedule.every(int(test.interval)).seconds.do(execute_scripts, test.monitor_events)

    time.sleep(1)
    while True:
        schedule.run_pending()
        time.sleep(1)

run()
