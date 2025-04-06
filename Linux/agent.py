import subprocess
import concurrent.futures
from typing import Any

def execute_scripts(script) -> tuple[Any, str, str]:
    print(script)
    result = subprocess.run(['python3', script], capture_output=True, text=True)
    return script, result.stdout, result.stderr

def run() -> None:
  # this section governs local vs databse mode - default is local
  generators: list[str] = ['process-logger.py', 'package-inventory.py', 'linux-endpoint-info.py', 'network-logger.py', 'linux-services.py']
  # this generator is for database mode
  # generators = ['process-logger.py', 'package-inventory.py', 'linux-endpoint-info.py', 'network-logger.py', 'linux-services.py' 'dboperations.py']
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