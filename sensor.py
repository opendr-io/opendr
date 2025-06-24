import configparser
import pathlib
import subprocess
import concurrent.futures
import os
import threading

config = configparser.ConfigParser()
config.read(pathlib.Path(__file__).parent.absolute() / "agentconfig.ini")

def execute_scripts_realtime(script):
  print(f"Starting execution of: {script}")
  try:
    process = subprocess.Popen(
      ['python', script],
      stdout=subprocess.PIPE,
      stderr=subprocess.STDOUT,  # Combine stderr with stdout
      text=True,
      bufsize=1,
      universal_newlines=True
    )
      
    output_lines = []
    # Read output line by line in real-time
    for line in iter(process.stdout.readline, ''):
      line = line.rstrip()
      print(f"[{script}] {line}")
      output_lines.append(line)
    
    process.wait()  # Wait for process to complete
    return script, '\n'.join(output_lines), "", process.returncode
  except Exception as e:
    print(f"Error executing {script}: {e}")
    return script, "", str(e), -1

def run():
  os_mode = config.get('General', 'OperatingSystem', fallback='Windows')
  pathsep = '\\' if os_mode == 'Windows' else '/'
  generators = [os_mode + pathsep + script for script in config.get(os_mode, 'Scripts', fallback='').split(', ')]
  if(config.getboolean(os_mode, 'RunDatabaseOperations', fallback=False)):
    generators.append('Database' + pathsep + 'dboperations.py')

  print('Starting Scripts')
  print(f"Will execute: {generators}")
  
  with concurrent.futures.ThreadPoolExecutor(len(generators)) as executor:
    results = executor.map(execute_scripts_realtime, generators)
    for script, stdout, stderr, returncode in results:
      print(f"\nCompleted {script} with return code: {returncode}")
run()