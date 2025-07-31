import subprocess
import concurrent.futures
import psycopg
import sys
import configparser
import pathlib

config = configparser.ConfigParser()
config.read(pathlib.Path(__file__).parent.absolute() / "agentconfig.ini")
config.read(pathlib.Path(__file__).parent.absolute() / "dbconfig.ini")

os_mode: str = config.get('General', 'OperatingSystem', fallback='Windows')
os_log: dict[str, list[str]] = {
  "Windows": ['process', 'network', 'software', 'user', 'endpoint', 'service', 'hotfix', 'driver',  'defender', 'autorun', 'tasks'],
  "Linux": ['process', 'network', 'software', 'user', 'endpoint', 'service', 'cronjob', 'kernel', 'ssh'],
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

  if config.getboolean('General', 'RunAugmentOperations', fallback=False):
    generators.extend(['Augment' + path_sep + aug + '.py' for aug in augment_profiles])
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
