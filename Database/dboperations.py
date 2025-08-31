import os
import time
import shutil
import schedule
from pathlib import Path
from typing import NoReturn
import configparser
import pathlib
from storedata import StoreData

config = configparser.ConfigParser()
config.read(pathlib.Path(__file__).parent.absolute() / "../dbconfig.ini")

db_interval: int = config.getint('Database', 'DatabaseInterval', fallback=30)
cleanup_interval: int = config.getint('Database', 'CleanupInterval', fallback=30)

def directory_cleanup() -> None:
  directory: str = 'done/ready'
  with os.scandir(directory) as files:
    for file in files:
      if(file.is_file()):
        os.unlink(file.path)

def monitor_directory(dir, pat) -> NoReturn:
  dataStorage = StoreData()
  path = Path(dir)
  processed_files: set[Path] = set()
  schedule.every(cleanup_interval).minutes.do(directory_cleanup)
  while True:
    try:
      current_files: set[Path] = set(path.glob(pat))
      new_files: set[Path] = current_files - processed_files
      if not new_files:
        time.sleep(db_interval)
        continue            
      for new_file in new_files:
        fn = str(new_file)
        if ('debug' in fn):
          dataStorage.store_debug_events(fn)
        elif ('process' in fn):
          dataStorage.store_process_events(fn)
        elif ('network' in fn):
          dataStorage.store_network_events(fn)
        elif ('services' in fn):
          dataStorage.store_installed_services(fn)
        elif ('software' in fn):
          dataStorage.store_installed_applications(fn)
        elif ('endpoint' in fn):
          dataStorage.store_endpoint_info(fn)
        elif ('user' in fn):
          dataStorage.store_user_info(fn)
        elif ('hotfix' in fn):
          dataStorage.store_hotfix_info(fn)
        elif ('defender' in fn):
          dataStorage.store_defender_info(fn)
        elif ('driver' in fn):
          dataStorage.store_driver_info(fn)
        elif ('autoruns' in fn):
          dataStorage.store_autorun_info(fn)
        elif ('scheduled_task' in fn):
          dataStorage.store_scheduled_task_info(fn)
        processed_files.add(new_file)
        schedule.run_pending()
        shutil.move(fn, 'done/' + fn)
    except Exception as e:
      print(f"Error: {e}")
      time.sleep(db_interval)
      
def run() -> NoReturn:
  os.makedirs('done/ready', exist_ok=True)
  directory: str = 'ready'
  pat: str = '*.log'
  monitor_directory(directory, pat)

run()