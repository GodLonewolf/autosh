from datetime import datetime
from colorama import Fore, Style, init

init(autoreset=True)

def log_success(id, message, cc, end=''):
    timestamp = datetime.now().strftime("[%H:%M:%S]")
    print(f"\r{Style.DIM}{timestamp} » {Style.RESET_ALL}[{Style.BRIGHT}{Fore.GREEN}{cc[0]}|{cc[1]}|{cc[2]}|{cc[3]}{Style.RESET_ALL}] | [{Style.BRIGHT}{Fore.GREEN}SUCCESS - {id}{Style.RESET_ALL}] {Style.DIM}➔{Style.RESET_ALL}  [{Style.BRIGHT}{Fore.GREEN}{message}{Style.RESET_ALL}] {' '*10}", end=end)

def log_info(id, message, cc, end=''):
    timestamp = datetime.now().strftime("[%H:%M:%S]")
    print(f"\r{Style.DIM}{timestamp} » {Style.RESET_ALL}[{Style.BRIGHT}{Fore.CYAN}{cc[0]}|{cc[1]}|{cc[2]}|{cc[3]}{Style.RESET_ALL}] | [{Style.BRIGHT}{Fore.CYAN}PROCESSING - {id}{Style.RESET_ALL}] {Style.DIM}➔{Style.RESET_ALL}  [{Style.BRIGHT}{Fore.CYAN}{message}{Style.RESET_ALL}] {' '*10}", end=end)

def log_error(id, message, cc, end='\n'):
    timestamp = datetime.now().strftime("[%H:%M:%S]")
    print(f"\r{Style.DIM}{timestamp} » {Style.RESET_ALL}[{Style.BRIGHT}{Fore.RED}{cc[0]}|{cc[1]}|{cc[2]}|{cc[3]}{Style.RESET_ALL}] | [{Style.BRIGHT}{Fore.RED}ERROR - {id}{Style.RESET_ALL}] {Style.DIM}➔{Style.RESET_ALL}  [{Style.BRIGHT}{Fore.RED}{message}{Style.RESET_ALL}] {' '*10}", end=end)
