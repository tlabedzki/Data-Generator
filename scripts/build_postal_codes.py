"""
Build source/pl_postal_code.csv from the ZnajdzKod.pl postal code database.

Source: ZnajdzKod.pl na podstawie PRG (GUGiK) i TERYT (GUS), stan 16.09.2026
https://znajdzkod.pl/baza-kodow-pocztowych/

Usage (from the repository root):
    python scripts/build_postal_codes.py                       # downloads kody-pocztowe.csv
    python scripts/build_postal_codes.py --input kody-pocztowe.csv

The output keeps the columns the generator reads (id, postal_code, city) and adds address_count,
which the generator uses as the weight when it assigns postal codes to customers.
"""
import argparse
import io
import sys
import urllib.request
from pathlib import Path

import pandas as pd

SOURCE_URL = "https://znajdzkod.pl/pobierz/kody-pocztowe.csv"
OUTPUT_PATH = Path(__file__).resolve().parents[1] / "source" / "pl_postal_code.csv"

SOURCE_COLUMNS = {
    "kod_pocztowy": "postal_code",
    "miejscowosc_glowna": "city",
    "liczba_adresow": "address_count",
}


def read_source(input_path=None):
    """Read the ZnajdzKod.pl CSV from a local file or download it."""
    if input_path is None:
        request = urllib.request.Request(SOURCE_URL, headers={"User-Agent": "data-generator-build-script"})
        with urllib.request.urlopen(request, timeout=60) as response:
            input_path = io.BytesIO(response.read())

    return pd.read_csv(input_path, sep=";", encoding="utf-8-sig", dtype={"kod_pocztowy": str})


def convert(source):
    """Convert the source table to the generator format: id, postal_code, city, address_count."""
    missing = set(SOURCE_COLUMNS) - set(source.columns)
    if missing:
        raise ValueError(f"Missing columns in the source file: {sorted(missing)}")

    data = source[list(SOURCE_COLUMNS)].rename(columns=SOURCE_COLUMNS)
    data = data[data["postal_code"].str.fullmatch(r"\d{2}-\d{3}") & (data["address_count"] > 0)]
    data = data.drop_duplicates("postal_code").sort_values("postal_code").reset_index(drop=True)
    data["address_count"] = data["address_count"].astype(int)
    data.insert(0, "id", range(len(data)))

    return data


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--input", type=Path, help="local copy of kody-pocztowe.csv (default: download)")
    args = parser.parse_args(argv)

    data = convert(read_source(args.input))
    data.to_csv(OUTPUT_PATH, sep=";", index=False, encoding="utf-8", lineterminator="\n")
    print(f"Saved {len(data):,} postal codes ({data['city'].nunique():,} localities) to {OUTPUT_PATH}")


if __name__ == "__main__":
    sys.exit(main())
