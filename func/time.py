from datetime import datetime

# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - #
    # Functions:

def get_current_time():
    """
    Returns the current time formatted as a string.
    Returns:
        str: The current time in the format HH:MM:SS.
    """
    current_time = datetime.now().strftime("%H:%M:%S")
    return current_time