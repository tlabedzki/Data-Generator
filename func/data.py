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