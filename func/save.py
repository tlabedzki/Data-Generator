import func.log as l
import settings.main_settings as s

# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - #
    # Settings:

dataset_display_names = {
    "customer_data": "dane klientów",
    "product_data": "dane produktów",
    "order_data": "dane zamówień",
    "sales_data": "dane sprzedaży",
}

def save_file_as_chosen_format(data, data_name, saving_path):
    """
    Save the generated data to a file in the chosen format.

    This function performs the following steps:
    1. Logs the start of the file save operation.
    2. Saves the generated data to a file in the chosen format.
    3. Logs the success of the file save operation.
    """
    # Log the start of the file save operation:
    dataset_display_name = dataset_display_names.get(data_name, data_name)
    l.log_info(f'Zapisuję {dataset_display_name} ("{data_name}") do pliku: {saving_path}')

    # Save the generated data to a file in the chosen format:
    if s.saving_format == "csv":
        data.to_csv(saving_path, sep=';', index=False)
    elif s.saving_format == "parquet":
        data.to_parquet(saving_path, index=False)
    else:
        error_message = f"Nieobsługiwany format pliku: {s.saving_format}"
        l.log_error(error_message)
        raise ValueError(error_message)

    # Log the success of the file save operation:
    l.log_success(f'Zapisano {dataset_display_name} ("{data_name}") pomyślnie.')

def save_generated_outputs(generated_data, saving_paths):
    """
    Save all generated datasets using their configured output paths.

    Parameters:
    generated_data (dict): Dataset names mapped to generated DataFrames.
    saving_paths (dict): Dataset names mapped to target file paths.
    """
    for data_name, dataframe in generated_data.items():
        save_file_as_chosen_format(dataframe, data_name, saving_paths[data_name])
