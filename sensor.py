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

logProfiles = {
  "basic": ['process', 'network', 'software'],
  "advanced": ['process', 'network', 'software', 'user', 'service', 'endpoint'],
  "complete": {
    "Windows": ['process', 'network', 'software', 'hotfix', 'driver', 'user', 'defender', 'autorun', 'service', 'endpoint', 'tasks'],
    "Linux": ['process', 'network', 'software', 'user', 'service', 'endpoint', 'cronjob', 'kernel'],
    "MacOS": ['process', 'network', 'user', 'endpoint']
  },
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
  pathsep = '\\' if os_mode == 'Windows' else '/'
  file_path = os_mode + pathsep + os_mode.lower() + '-'
  logging_mode = config.get('General', 'LogProfile', fallback='basic')
  logging_scripts = logProfiles[logging_mode] if logging_mode != 'complete' else logProfiles[logging_mode][os_mode]
  generators = [file_path + script + '-log.py' for script in logging_scripts]
  # this section governs local vs database mode - default is local
  if config.getboolean(os_mode, 'RunDatabaseOperations', fallback=False):
    generators.append('Database' + pathsep + 'dboperations.py')
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
