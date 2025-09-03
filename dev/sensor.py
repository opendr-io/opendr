import psycopg
import sys
import configparser
import pathlib
from importlib import import_module
import time
import schedule
import threading
from typing import NoReturn

config = configparser.ConfigParser()
config.read(pathlib.Path(__file__).parent.absolute() / "../agentconfig.ini")
config.read(pathlib.Path(__file__).parent.absolute() / "../dbconfig.ini")

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
    # "Windows": ['process', 'network', 'software', 'user', 'endpoint', 'service', 'hotfix', 'driver', 'defender', 'autorun', 'tasks'],
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
stop_event = threading.Event()

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

def execute_inf_script(class_obj) -> NoReturn:
    while not stop_event.is_set():
        t = threading.Thread(target=class_obj.monitor_events)
        t.start()
        t.join()
        time.sleep(class_obj.interval)

def execute_script(func, i) -> NoReturn:
    if i:
        t = threading.Thread(target=func, args=(i,))
    else:
        t = threading.Thread(target=func)
    t.start()

def run() -> None:
    # path_sep = '\\' if os_mode == 'Windows' else '/'
    file_path = os_mode.lower() + '-'
    logging_scripts = log_profiles[config.get('General', 'LogProfile', fallback='basic')]
    generators = [file_path + script + '-log' for script in logging_scripts]
    classes = [os_mode + script.capitalize() + 'Logger' for script in logging_scripts]
    for i in range(len(generators)):
        class_obj = dynamic_imp(generators[i], classes[i])
        if int(class_obj.interval) < 1:
            execute_script(execute_inf_script, class_obj)
        else:
            schedule.every(int(class_obj.interval)).seconds.do(execute_script, class_obj.monitor_events, None)

    time.sleep(1)
    try:
        while True:
            schedule.run_pending()
            time.sleep(1)
    except KeyboardInterrupt:
        stop_event.set()
        schedule.clear()

run()
