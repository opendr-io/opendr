import subprocess
import concurrent.futures
import configparser
import pathlib

config = configparser.ConfigParser()
config.read(pathlib.Path(__file__).parent.absolute() / "../agentconfig.ini")

def execute_scripts(script):
    print(script)
    result = subprocess.run(['python', script], capture_output=True, text=True)
    return script, result.stdout, result.stderr

def run():
  # this section governs local vs database mode - default is local
  generators = config.get('Windows', 'Scripts', fallback='').split(', ')
  if config.getboolean('Windows', 'RunDatabaseOperations', fallback=False):
    generators.append('dboperations.py')
  print('Starting Generators')
  with concurrent.futures.ThreadPoolExecutor(len(generators)) as executor:
    results = executor.map(execute_scripts, generators)
    for script, stdout, stderr in results:
      print(f"Results from {script}:")
      print(stdout)
      if(stderr):
        print(f"Errors from {script}:")
        print(stderr)
run()