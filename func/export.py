"""
In-memory exports of generated datasets for downloads: one table as CSV or Parquet, or all tables in a ZIP file.
"""
import io
import zipfile

FORMATS = {
    "csv": {"label": "CSV", "mime": "text/csv"},
    "parquet": {"label": "Parquet", "mime": "application/vnd.apache.parquet"},
}

# Semicolon-separated like the command-line generator, with a dot as the decimal separator. The UTF-8 BOM (which the
# command-line files do not have) lets Excel detect the encoding and show Polish letters.
CSV_SEPARATOR = ";"
CSV_ENCODING = "utf-8-sig"


def dataframe_to_bytes(data, file_format):
    """
    Serialize one DataFrame.

    Parameters:
    data (pd.DataFrame): Table to export.
    file_format (str): "csv" or "parquet".

    Returns:
    bytes: File content.
    """
    if file_format == "csv":
        return data.to_csv(sep=CSV_SEPARATOR, index=False).encode(CSV_ENCODING)
    if file_format == "parquet":
        buffer = io.BytesIO()
        data.to_parquet(buffer, index=False)
        return buffer.getvalue()
    raise ValueError(f"Unsupported format: {file_format}. Use one of {sorted(FORMATS)}.")


def file_name(dataset_name, file_format):
    return f"{dataset_name}.{file_format}"


def files_to_zip(files):
    """
    Pack already serialized files into one ZIP file.

    Parameters:
    files (dict): File names mapped to bytes.

    Returns:
    bytes: ZIP file content.
    """
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for name, content in files.items():
            archive.writestr(name, content)
    return buffer.getvalue()


def datasets_to_zip(datasets, file_format):
    """
    Pack several DataFrames into one ZIP file.

    Parameters:
    datasets (dict): Dataset names mapped to DataFrames.
    file_format (str): "csv" or "parquet".

    Returns:
    bytes: ZIP file content.
    """
    return files_to_zip({file_name(name, file_format): dataframe_to_bytes(data, file_format)
                         for name, data in datasets.items()})
