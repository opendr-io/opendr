import subprocess
import concurrent.futures
import psycopg
import sys
from enum import Enum
import configparser
import pathlib

config = configparser.ConfigParser()
config.read(pathlib.Path(__file__).parent.absolute() / "agentconfig.ini")
config.read(pathlib.Path(__file__).parent.absolute() / "dbconfig.ini")
os_mode = config.get('General', 'OperatingSystem', fallback='Windows')

os_log = {
  "Windows": ['process', 'network', 'software', 'user', 'endpoint', 'hotfix', 'driver',  'defender', 'autorun', 'service', 'tasks'],
  "Linux": ['process', 'network', 'software', 'user', 'service', 'endpoint', 'cronjob', 'kernel'],
  "MacOS": ['process', 'network', 'user', 'endpoint']
}

log_profiles = {
  "basic": os_log[os_mode][:3],
  "advanced": os_log[os_mode][:6],
  "complete": os_log[os_mode],
  "custom": config.get(os_mode, 'Scripts', fallback='').split(', ')
}

def test_connection():
  try:
    with psycopg.connect(host=config.get('Database', 'HostName'), port=config.get('Database', 'PortNumber', fallback='4000'),
                        dbname=config.get('Database', 'DatabaseName', fallback='opendr'),
                        user=config.get('Database', 'RootDatabaseUserName', fallback='postgres'), password=config.get('Database', 'RootDatabasePassword'),
                        sslmode='verify-ca', sslrootcert=config.get('Database', 'SSLRootCert')) as connection:
        _ = connection.cursor()
        connection.close()
  except Exception as e:
    print(e)
    sys.exit(1)

def execute_scripts(script):
    print(script)
    result = subprocess.run(['python', script], capture_output=True, text=True)
    return script, result.stdout, result.stderr

def run() -> None:
  path_sep = '\\' if os_mode == 'Windows' else '/'
  file_path = os_mode + path_sep + os_mode.lower() + '-'
  logging_scripts = log_profiles[config.get('General', 'LogProfile', fallback='basic')]
  generators = [file_path + script + '-log.py' for script in logging_scripts]
  # this section governs local vs database mode - default is local
  if config.getboolean('General', 'RunDatabaseOperations', fallback=False):
    generators.append('Database' + path_sep + 'dboperations.py')
    test_connection()

  print('Starting Scripts')
  with concurrent.futures.ThreadPoolExecutor(len(generators)) as executor:
    results = executor.map(execute_scripts, generators)
    for script, stdout, stderr in results:
      print(f"Results from {script}:")
      print(stdout)
      if(stderr):
        print(f"Errors from {script}:")
        print(stderr)

run()
