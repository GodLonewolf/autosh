from datetime import datetime
from colorama import Fore, Style, init

init(autoreset=True)

def log_success(id, message):
    timestamp = datetime.now().strftime("[%H:%M:%S]")
    print(f"{Fore.GREEN}{timestamp} [{id}] SUCCESS: {message}{Style.RESET_ALL}")

def log_error(id, message):
    timestamp = datetime.now().strftime("[%H:%M:%S]")
    print(f"{Fore.RED}{timestamp} [{id}] ERROR: {message}{Style.RESET_ALL}")

def log_info(id, message):
    timestamp = datetime.now().strftime("[%H:%M:%S]")
    print(f"{Fore.CYAN}{timestamp} [{id}] INFO: {message}{Style.RESET_ALL}")
