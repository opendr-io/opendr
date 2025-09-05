import os
import shutil
from pathlib import Path
import configparser
import pathlib
from storedata import StoreData

config = configparser.ConfigParser()
config.read(pathlib.Path(__file__).parent.absolute() / "../dbconfig.ini")

class DatabaseOperations():
  def __init__(self):
    self.db_interval: int = config.getint('Database', 'DatabaseInterval', fallback=30)
    self.cleanup_interval: int = config.getint('Database', 'CleanupInterval', fallback=30)
    self.dir: str = 'ready'
    self.pat: str = '*.log'
    self.done_dir: str = 'done/ready'
    self.processed_files: set[Path] = set()
    os.makedirs(self.done_dir, exist_ok=True)
    print("DatabaseOperations Initialization complete")

  def directory_cleanup(self) -> None:
    print("Directory Cleanup started")
    with os.scandir(self.done_dir) as files:
      for file in files:
        if(file.is_file()):
          os.unlink(file.path)

  def monitor_directory(self) -> None:
    dataStorage = StoreData()
    path = Path(self.dir)
    try:
      current_files: set[Path] = set(path.glob(self.pat))
      new_files: set[Path] = current_files - self.processed_files
      if not new_files:
        return            
      for new_file in new_files:
        fn = str(new_file)
        if ('process' in fn):
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
        self.processed_files.add(new_file)
        shutil.move(fn, 'done/' + fn)
    except Exception as e:
      print(f"Error: {e}")
