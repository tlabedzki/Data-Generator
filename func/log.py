import logging
from colorama import init
from colorama import Fore, Style
init()

import func.time as fti

# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - #
    # Functions:

LOG_LEVEL_WIDTH = 7


def log_time_print():
    """
    Returns the current time formatted with light black color and reset style.
    Returns:
        str: The formatted current time string.
    """
    return f'  {Fore.LIGHTBLACK_EX}{fti.get_current_time()}  {Style.RESET_ALL}'

def log_level_print(level, color):
    """
    Returns the formatted log level.
    Args:
        level (str): The log level name.
        color (str): Colorama foreground color.
    Returns:
        str: Formatted log level string.
    """
    return f'{color}{level:<{LOG_LEVEL_WIDTH}}{Style.RESET_ALL}'

def print_log_line(level, message, color=Style.RESET_ALL, indent=0):
    """
    Prints a single formatted log line.
    Args:
        level (str): The log level name.
        message (str): The message to print.
        color (str): Colorama foreground color.
        indent (int): Number of spaces before the message.
    """
    indentation = " " * indent
    print(f'{log_time_print()}{log_level_print(level, color)}  {indentation}{message}')

def log_info(i):
    """
    Logs an informational message and prints it with a timestamp.
    Args:
        i (str): The informational message to log and print.
    """
    logging.info(i)
    print_log_line('INFO', i, Fore.WHITE)

def log_error(e):
    """
    Logs an error message and prints it with a timestamp in red color.
    Args:
        e (str): The error message to log and print.
    """
    logging.error(e)
    print_log_line('BŁĄD', e, Fore.LIGHTRED_EX)

def log_warning(w):
    """
    Logs a warning message and prints it with a timestamp and log level.
    Args:
        w (str): The warning message to log and print.
    """
    logging.warning(w)
    print_log_line('OSTRZ', w, Fore.YELLOW)

def log_success(i):
    """
    Logs a success message and prints it with a timestamp in green color.
    Args:
        i (str): The success message to log and print.
    """
    logging.info(i)
    print_log_line('SUKCES', i, Fore.GREEN)

def log_section(title):
    """
    Logs a visible section title.
    Args:
        title (str): The section title.
    """
    logging.info(title)
    print_log_line('INFO', title, Fore.CYAN)

def log_metric(label, value, field_width=42):
    """
    Logs a formatted metric line.
    Args:
        label (str): The metric label.
        value (str): The metric value.
        field_width (int): Width used to align labels.
    """
    logging.info(f'{label}: {value}')
    print_log_line('INFO', f'{label + ":":<{field_width}} {value}', Fore.WHITE, indent=2)
