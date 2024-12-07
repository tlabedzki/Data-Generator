import numpy as np

# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - #
    # Functions:

def get_param_list_and_normalized_probabilities(param_dict):
    """
    Extract the parameter list and normalized probabilities from a dictionary.

    Parameters:
    param_dict (dict): The input dictionary containing parameters and probabilities.

    Returns:
    list: The extracted parameter list.
    list: The normalized probabilities.
    """
    # Extract the parameter list and probabilities:
    param_list = list(param_dict.keys())
    probabilities = list(param_dict.values())

    # Normalize the probabilities:
    probabilities = probabilities / np.sum(probabilities)

    return param_list, probabilities

def round_to_9(price):
    """
    Round the given price to the nearest integer and ensure the last digit is 9.

    Parameters:
    price (float): The input price to be rounded.

    Returns:
    int: The rounded price with the last digit as 9.
    """
    # Round to the nearest integer first:
    rounded_price = round(price)

    # Ensure the last digit is 9:
    if rounded_price % 10 != 9:
        rounded_price = (rounded_price // 10) * 10 + 9

    return rounded_price