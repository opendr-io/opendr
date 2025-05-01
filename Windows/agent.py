import subprocess
import concurrent.futures
import os
import signal
import sys

def run():
  def execute_scripts(script):
    print(script)
    result = subprocess.run(['python', script], capture_output=True, text=True)
    return script, result.stdout, result.stderr
  # this section governs local vs databse mode - default is local
  generators = ['processlog.py', 'softwareinventorylog.py', 'endpointinfolog.py', 'networklog.py', 'windowsserviceslog.py']
  # this generator is for database mode
  # generators = ['dboperations.py', 'softwareinventorylog.py', 'endpointinfolog.py', 'userinfolog.py', 'processlog.py', 'networklog.py', 'windowsserviceslog.py']
  print('Starting Genereators')
  with concurrent.futures.ThreadPoolExecutor(len(generators)) as executor:
    results = executor.map(execute_scripts, generators)
    for script, stdout, stderr in results:
      print(f"Results from {script}:")
      print(stdout)
      if(stderr):
        print(f"Errors from {script}:")
        print(stderr)
run()