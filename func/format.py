# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - #
    # Functions:

def format_number(number):
    """
    Format a number into the ### ###.## format.

    Parameters:
    number (float or int): The number to format.

    Returns:
    str: The formatted number as a string.
    """
    if not isinstance(number, (int, float)):
        raise ValueError("The input must be a number (int or float).")

    # Format the number with a space as the thousands separator and two decimal places
    formatted_number = f"{number:,.0f}".replace(",", " ").replace(".", ",")
    return formatted_number