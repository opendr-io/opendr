import configparser
import pathlib
import subprocess
import concurrent.futures
import os
import threading
import queue

config = configparser.ConfigParser()
config.read(pathlib.Path(__file__).parent.absolute() / "agentconfig.ini")

def stream_output(pipe, output_queue, script_name, stream_type):
  """Stream output from subprocess in real-time"""
  try:
    for line in iter(pipe.readline, ''):
      if line:
        output_queue.put((script_name, stream_type, line.rstrip()))
    pipe.close()
  except Exception as e:
    output_queue.put((script_name, 'ERROR', f"Stream error: {e}"))

def execute_scripts(script):
  print(f"Starting execution of: {script}")
  output_queue = queue.Queue()
    
  try:
    process = subprocess.Popen(
      ['python', script],
      stdout=subprocess.PIPE,
      stderr=subprocess.PIPE,
      text=True,
      bufsize=1,
      universal_newlines=True
    )
    
    # Start threads to capture stdout and stderr
    stdout_thread = threading.Thread(
      target=stream_output, 
      args=(process.stdout, output_queue, script, 'STDOUT')
    )
    stderr_thread = threading.Thread(
      target=stream_output, 
      args=(process.stderr, output_queue, script, 'STDERR')
    )
    
    stdout_thread.start()
    stderr_thread.start()
    
    # Collect all output
    all_stdout = []
    all_stderr = []
    
    # Process output as it comes in
    while process.poll() is None or not output_queue.empty():
      try:
        script_name, stream_type, line = output_queue.get(timeout=0.1)
        print(f"[{script_name}] {stream_type}: {line}")
        
        if stream_type == 'STDOUT':
          all_stdout.append(line)
        elif stream_type == 'STDERR':
          all_stderr.append(line)
              
      except queue.Empty:
        continue
    
    # Wait for threads to complete
    stdout_thread.join()
    stderr_thread.join()
    
    # Wait for process to complete
    process.wait()
    
    return script, '\n'.join(all_stdout), '\n'.join(all_stderr), process.returncode
      
  except Exception as e:
    print(f"Error executing {script}: {e}")
    return script, "", str(e), -1

def run():
  os_mode = config.get('General', 'OperatingSystem', fallback='Windows')
  pathsep = '\\' if os_mode == 'Windows' else '/'
  generators = [os_mode + pathsep + script for script in config.get(os_mode, 'Scripts', fallback='').split(', ')]
  
  if config.getboolean(os_mode, 'RunDatabaseOperations', fallback=False):
    generators.append('Database' + pathsep + 'dboperations.py')

  print('Starting Scripts')
  
  with concurrent.futures.ThreadPoolExecutor(len(generators)) as executor:
    results = executor.map(execute_scripts, generators)
    for script, stdout, stderr, returncode in results:
      print(f"\n{'='*60}")
      print(f"Final results from {script} (Return code: {returncode}):")
      print(f"{'='*60}")
run()