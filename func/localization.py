import pandas as pd

import settings.main_settings as s
import settings.localization as loc


def localize_dataset(data):
    """
    Translate display values in a generated dataset according to settings.main_settings.data_language.

    Parameters:
    data (pd.DataFrame): Generated dataset.

    Returns:
    pd.DataFrame: Localized copy of the dataset.
    """
    language = getattr(s, "data_language", "en")
    if language not in loc.supported_languages:
        raise ValueError(f"Nieobsługiwany data_language: {language}. Dostępne opcje: {sorted(loc.supported_languages)}")

    if language == "en":
        return data.copy()

    localized_data = data.copy()
    language_translations = loc.translations[language]

    for column_name, value_translations in language_translations.items():
        if column_name in localized_data.columns:
            localized_data[column_name] = localized_data[column_name].map(
                lambda value: value_translations.get(value, value)
            )

    localized_data = rebuild_product_name(localized_data)

    return localized_data


def localize_generated_data(generated_data):
    """
    Translate all generated output datasets.

    Parameters:
    generated_data (dict): Dataset names mapped to DataFrames.

    Returns:
    dict: Dataset names mapped to localized DataFrames.
    """
    return {
        dataset_name: localize_dataset(dataset)
        for dataset_name, dataset in generated_data.items()
    }


def rebuild_product_name(data):
    """
    Rebuild product names after product type translation.

    Parameters:
    data (pd.DataFrame): Dataset with product columns.

    Returns:
    pd.DataFrame: Dataset with localized product_name when all required columns exist.
    """
    required_columns = {"product_type", "brand", "product_series", "product_model", "product_name"}
    if not required_columns.issubset(data.columns):
        return data

    data["product_name"] = (
        data["product_type"].astype(str)
        + " "
        + data["brand"].astype(str)
        + " "
        + data["product_series"].astype(str)
        + " "
        + data["product_model"].astype(str)
    )

    return data
