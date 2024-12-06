import logging
from colorama import init
from colorama import Fore, Back, Style
init()

import func.time as fti

# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - #
    # Functions:

def log_time_print():
    """
    Returns the current time formatted with light black color and reset style.
    Returns:
        str: The formatted current time string.
    """
    return f'  {Fore.LIGHTBLACK_EX}{fti.get_current_time()}  {Style.RESET_ALL}'

def log_info(i):
    """
    Logs an informational message and prints it with a timestamp.
    Args:
        i (str): The informational message to log and print.
    """
    logging.info(i)
    print(f'{log_time_print()}{i}')

def log_error(e):
    """
    Logs an error message and prints it with a timestamp in red color.
    Args:
        e (str): The error message to log and print.
    """
    logging.error(e)
    print(f'{log_time_print()}{Fore.LIGHTRED_EX}{e}{Style.RESET_ALL}')

def log_success(i):
    """
    Logs a success message and prints it with a timestamp in green color.
    Args:
        i (str): The success message to log and print.
    """
    logging.info(i)
    print(f'{log_time_print()}{Fore.GREEN}{i}{Style.RESET_ALL}')
