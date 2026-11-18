import pandas as pd

import settings.localization as loc
import settings.main_settings as s


def localize_dataset(data: pd.DataFrame) -> pd.DataFrame:
    """
    Translate display values in a generated dataset according to settings.main_settings.data_language.

    Parameters:
    data (pd.DataFrame): Generated dataset.

    Returns:
    pd.DataFrame: Localized copy of the dataset.
    """
    language = getattr(s, "data_language", "en")
    if language not in loc.supported_languages:
        raise ValueError(f"Unsupported data_language: {language}. Use one of {sorted(loc.supported_languages)}.")

    if language == "en":
        return data.copy()

    localized_data = data.copy()
    language_translations = loc.translations[language]

    # Columns that hold the same values as another translated column:
    aliases = {"preferred_category": "category"}
    columns = list(language_translations.items()) + [
        (alias, language_translations[source]) for alias, source in aliases.items() if source in language_translations]
    for column_name, value_translations in columns:
        if column_name in localized_data.columns:
            localized_data[column_name] = localized_data[column_name].map(
                lambda value, translations=value_translations: translations.get(value, value)
            )

    localized_data = rebuild_product_name(localized_data)

    return localized_data


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
