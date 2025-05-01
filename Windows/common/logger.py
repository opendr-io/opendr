import os
from datetime import datetime
import logging
import random
from pathlib import Path
from typing import Optional

def setup_logging(log_directory: str, ready_directory: str, logger_name: str, file_name: str) -> logging.Logger:
    """Configures logging to write to a new file every minute."""
    current_time: str = datetime.now().strftime('%Y-%m-%d_%H-%M')
    random_int = random.randint(1, 1000)
    log_filename: str = os.path.join(log_directory, f'{file_name}_{random_int}_{current_time}.log')
    logger: logging.Logger = logging.getLogger(logger_name)
    logger.setLevel(logging.INFO)
    # Close and remove existing handlers to prevent file handle leaks
    clear_handlers(log_directory, ready_directory, logger)

    # Create new handler for the new log file
    handler: logging.FileHandler = logging.FileHandler(log_filename, mode='a')
    handler.setFormatter(logging.Formatter('%(message)s'))
    logger.addHandler(handler)
    return logger

def clear_handlers(log_directory: str, ready_directory: str, logger: logging.Logger) -> None:
    while logger.hasHandlers():
        try:
            if len(logger.handlers) == 0:
                break
            handler: logging.Handler = logger.handlers[0]
            file_path: str = handler.baseFilename
            handler.close()
            logger.removeHandler(handler)
            if('nt' in os.name):
                file = str(file_path).rsplit('\\')[-1]
            else:
                file = str(file_path).rsplit('/')[-1]
            log_path: str = os.path.join(log_directory, file)
            ready_path: str = os.path.join(ready_directory, file)
            Path(log_path).rename(ready_path)
        except Exception as e:
            print(e)
            continue

def check_logging_interval(*args) -> tuple[logging.Logger, int]:
    log_directory: str
    ready_directory: str
    logger_name: str
    file_name: str
    logger: Optional[logging.Logger]
    last_interval: Optional[int]
    log_directory, ready_directory, logger_name, file_name, logger, last_interval = args
    current_interval: int = datetime.now().day # Defaults to daily logs for running locally; change to minute for database shippping
    if current_interval != last_interval:  # Rotate log file at the start of a new minute
        logger = setup_logging(log_directory, ready_directory, logger_name, file_name)
        last_interval= current_interval
    return logger, last_interval

def move_existing_temp_files(log_directory, ready_directory):
    try:
        for entry in os.listdir(log_directory):
            full_path = os.path.join(log_directory, entry)
            if('nt' in os.name):
                file = str(full_path).rsplit('\\')[-1]
            else:
                file = str(full_path).rsplit('/')[-1]
            log_path: str = os.path.join(log_directory, file)
            ready_path: str = os.path.join(ready_directory, file)
            Path(log_path).rename(ready_path)
    except FileNotFoundError:
        print(f"Error: The directory '{dir}' was not found.")
    except PermissionError:
        print(f"Error: Permission denied to access '{dir}'.")
    except Exception as e:
        print(f"An error occurred: {e}")

def enter_debug_logs(file_name: str, debug_string: str) -> None:
    with open(f'debuggeneratorlogs/{file_name}-debug.log', 'a') as file:
        file.write(debug_string)
