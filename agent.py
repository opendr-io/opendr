import subprocess
import concurrent.futures
import configparser
import pathlib

config = configparser.ConfigParser()
config.read(pathlib.Path(__file__).parent.absolute() / "agentconfig.ini")

def execute_scripts(script):
    print(script)
    result = subprocess.run(['python', script], capture_output=True, text=True)
    return script, result.stdout, result.stderr

def run():
  os_mode = config.get('General', 'OperatingSystem', fallback='Windows')
  pathsep = '\\' if os_mode == 'Windows' else '/'
  generators = [os_mode + pathsep + script for script in config.get(os_mode, 'Scripts', fallback='').split(', ')]
  # this section governs local vs database mode - default is local
  if config.getboolean(os_mode, 'RunDatabaseOperations', fallback=False):
    generators.append('Database' + pathsep + 'dboperations.py')

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
