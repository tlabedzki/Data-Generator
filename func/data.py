import numpy as np
import unicodedata

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
    probabilities = np.array(list(param_dict.values()), dtype=float)

    if probabilities.sum() <= 0:
        raise ValueError("The sum of probabilities must be greater than 0.")

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



def remove_polish_accents(text):
    """
    Remove Polish accents from the given text.

    Parameters:
    text (str): The input text containing Polish accents.

    Returns:
    str: The text with Polish accents removed.
    """
    # "ł" has no Unicode decomposition, so it is replaced explicitly:
    text = text.replace('ł', 'l').replace('Ł', 'L')

    # Get rid of other Polish accents:
    nfkd_form = unicodedata.normalize('NFKD', text)
    return ''.join([c for c in nfkd_form if not unicodedata.combining(c)])

def report_progress(progress, done, total, steps=50):
    """
    Call a progress callback roughly `steps` times over a loop, without touching the random state.

    Parameters:
    progress (callable or None): Callback taking the completed fraction (0-1).
    done (int): Completed items.
    total (int): All items.
    steps (int): Number of updates over the whole loop.
    """
    if progress is None or total <= 0:
        return
    step = max(total // steps, 1)
    if done % step == 0 or done >= total:
        progress(min(done / total, 1.0))
