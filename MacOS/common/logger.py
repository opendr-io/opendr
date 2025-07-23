import os
from datetime import datetime
import logging
import random
from pathlib import Path
from typing import Optional
from common.attributes import get_config_value

class LoggingModule:
    def __init__(self, log_directory: str, ready_directory: str, logger_name: str, file_name: str):
        self.log_directory: str = log_directory
        self.ready_directory: str = ready_directory
        self.debug_generator_directory: str = "debuggeneratorlogs"
        self.logger_name: str = logger_name
        self.file_name: str = file_name
        self.log_line_count: int = 0
        self.debug_mode: bool = get_config_value('General', 'Debugging', False, 'bool')
        self.logger: logging.Logger
        self.debug_logger: Optional[logging.Logger] = None
        self.last_interval: Optional[int] = self.fetch_interval()
        self.setup_logging()
        if self.debug_mode:
            self.setup_logging(debug=True)

    def setup_logging(self, debug: bool=False) -> None:
        """Configures logging to write to a new file every minute."""
        current_time: str = datetime.now().strftime('%Y-%m-%d_%H-%M')
        random_int = random.randint(1, 1000)
        if not debug:
            log_filename: str = os.path.join(self.log_directory, f'{self.file_name}_{random_int}_{current_time}.log')
            self.logger: logging.Logger = logging.getLogger(self.logger_name)
            self.logger.setLevel(logging.INFO)
            # Close and remove existing handlers to prevent file handle leaks
            self.clear_logging_handlers()

            # Create new handler for the new log file
            handler: logging.FileHandler = logging.FileHandler(log_filename, mode='a')
            handler.setFormatter(logging.Formatter('%(message)s'))
            self.logger.addHandler(handler)
        else:
            log_filename: str = os.path.join(self.debug_generator_directory, f'debug_{self.file_name}_{random_int}_{current_time}.log')
            self.debug_logger: logging.Logger = logging.getLogger('Debug' + self.logger_name)
            self.debug_logger.setLevel(logging.INFO)
            # Close and remove existing handlers to prevent file handle leaks
            self.clear_debug_handlers()

            # Create new handler for the new log file
            handler: logging.FileHandler = logging.FileHandler(log_filename, mode='a')
            handler.setFormatter(logging.Formatter('%(message)s'))
            self.debug_logger.addHandler(handler)

    def clear_handlers(self) -> None:
        self.clear_logging_handlers()
        if self.debug_mode:
            self.clear_debug_handlers()

    def clear_logging_handlers(self) -> None:
        while self.logger.hasHandlers():
            try:
                if len(self.logger.handlers) == 0:
                    break
                handler: logging.Handler = self.logger.handlers[0]
                file_path: str = handler.baseFilename
                handler.close()
                self.logger.removeHandler(handler)
                if('nt' in os.name):
                    file = str(file_path).rsplit('\\')[-1]
                else:
                    file = str(file_path).rsplit('/')[-1]
                log_path: str = os.path.join(self.log_directory, file)
                ready_path: str = os.path.join(self.ready_directory, file)
                Path(log_path).rename(ready_path)
            except Exception as e:
                print(e)
                continue

    def clear_debug_handlers(self) -> None:
        while self.debug_logger.hasHandlers():
            try:
                if len(self.debug_logger.handlers) == 0:
                    break
                handler: logging.Handler = self.debug_logger.handlers[0]
                file_path: str = handler.baseFilename
                handler.close()
                self.debug_logger.removeHandler(handler)
                if('nt' in os.name):
                    file = str(file_path).rsplit('\\')[-1]
                else:
                    file = str(file_path).rsplit('/')[-1]
                debug_path: str = os.path.join(self.debug_generator_directory, file)
                ready_path: str = os.path.join(self.ready_directory, file)
                Path(debug_path).rename(ready_path)
            except Exception as e:
                print(e)
                continue

    @staticmethod
    def fetch_interval() -> int:
        interval = get_config_value('General', 'LoggingInterval', 'minute')
        match interval:
            case 'minute':
                return datetime.now().minute
            case 'hour':
                return datetime.now().hour
            case 'day':
                return datetime.now().day
            case _:
                return datetime.now().minute

    def check_logging_interval(self) -> None:
        current_interval: int = self.fetch_interval() # Defaults to daily logs for running locally; change to minute for database shipping
        if current_interval != self.last_interval:  # Rotate log file at the start of a new minute
            self.setup_logging()
            if self.debug_mode:
                self.setup_logging(debug=True)
            self.last_interval = current_interval

    def write_log(self, data: str) -> None:
        self.logger.info(data)
        self.log_line_count += 1

    def write_debug_log(self, data: str) -> None:
        if self.debug_mode:
            self.debug_logger.info(data)
