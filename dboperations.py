import os
import time
import shutil
import schedule
from pathlib import Path
from Database.storedata import StoreData

def directory_cleanup():
  directory = 'done/ready'
  with os.scandir(directory) as files:
    for file in files:
      if(file.is_file()):
        os.unlink(file.path)

def monitor_directory(dir, pat):
  dataStorage = StoreData()
  path = Path(dir)
  processed_files = set()
  schedule.every(30).minutes.do(directory_cleanup)
  while True:
    try:
      current_files = set(path.glob(pat))
      new_files = current_files - processed_files
      if not new_files:
        time.sleep(30)
        continue            
      for new_file in new_files:
        fn = str(new_file)
        file_type = None
        if('process' in fn):
          dataStorage.store_process_events(fn)
        elif('network' in fn):
          dataStorage.store_network_events(fn)
        elif('services' in fn):
          dataStorage.store_installed_services(fn)
        elif('software' in fn):
          dataStorage.store_installed_applications(fn)
        elif('endpoint' in fn):
          dataStorage.store_endpoint_info(fn)
        elif('users' in fn):
          dataStorage.store_user_info(fn)
        processed_files.add(new_file)
        schedule.run_pending()
        shutil.move(fn, 'done/'+fn)
    except Exception as e:
      print(f"Error: {e}")
      time.sleep(1)
      
def run():
  os.makedirs('done/ready', exist_ok=True)
  directory = 'ready'
  pat = '*.log'
  monitor_directory(directory, pat)

run()