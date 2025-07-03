import subprocess
import concurrent.futures
import psycopg
import sys
import configparser
import pathlib

config = configparser.ConfigParser()
config.read(pathlib.Path(__file__).parent.absolute() / "agentconfig.ini")
config.read(pathlib.Path(__file__).parent.absolute() / "dbconfig.ini")

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
  os_mode = config.get('General', 'OperatingSystem', fallback='Windows')
  pathsep = '\\' if os_mode == 'Windows' else '/'
  generators = [os_mode + pathsep + script for script in config.get(os_mode, 'Scripts', fallback='').split(', ')]
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
