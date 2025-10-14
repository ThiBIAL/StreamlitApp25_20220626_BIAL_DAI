import os
import io
import zipfile
import requests
import pandas as pd
import unicodedata
import difflib

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
DATA_DIR = os.path.join(ROOT, 'data')
os.makedirs(DATA_DIR, exist_ok=True)
CACHE_PATH = os.path.join(DATA_DIR, 'dataset_all_years.parquet')

RESOURCE_URL = 'https://www.data.gouv.fr/api/1/datasets/r/fc84971a-240a-43bd-8d61-64e7fb8a0dc7'

# Try to import country_converter if available
try:
    import country_converter as coco
    _CC = coco.CountryConverter()
except Exception:
    _CC = None


def fetch_and_cache(cache_path: str = CACHE_PATH) -> pd.DataFrame:
    """Download the ZIP from data.gouv.fr, parse CSV files robustly and cache a parquet copy.

    Returns the combined DataFrame.
    """
    resp = requests.get(RESOURCE_URL, timeout=30)
    resp.raise_for_status()

    with zipfile.ZipFile(io.BytesIO(resp.content)) as z:
        csvs = [n for n in z.namelist() if n.lower().endswith('.csv')]
        dfs = []
        for n in csvs:
            b = z.read(n)
            df = None
            # try common encodings and sep=';'
            for enc in ('utf-8', 'latin1', 'cp1252'):
                try:
                    s = b.decode(enc)
                    df = pd.read_csv(io.StringIO(s), sep=';', engine='python', on_bad_lines='warn')
                    break
                except Exception:
                    continue
            if df is None:
                try:
                    df = pd.read_csv(io.BytesIO(b), sep=';', engine='python', encoding='latin1', on_bad_lines='warn')
                except Exception:
                    # give up on this file
                    continue
            dfs.append(df)

    if not dfs:
        raise RuntimeError('No CSV files could be read from the remote ZIP')

    all_df = pd.concat(dfs, ignore_index=True)

    # Basic normalizations: trim strings and try numeric conversions where appropriate
    for col in all_df.columns:
        if all_df[col].dtype == object:
            s = all_df[col].astype(str).str.replace('\xa0', ' ', regex=False).str.strip()
            # try to convert typical number formats (spaces thousands, commas decimals)
            numeric_candidate = s.str.replace(' ', '').str.replace(',', '.', regex=False)
            converted = pd.to_numeric(numeric_candidate, errors='coerce')
            if converted.notna().mean() > 0.5:
                all_df[col] = converted
            else:
                all_df[col] = s

    # Try to cache as parquet, fallback to CSV
    try:
        all_df.to_parquet(cache_path, index=False)
    except Exception:
        all_df.to_csv(cache_path + '.csv', index=False)

    return all_df


def load_data(use_cache: bool = True) -> pd.DataFrame:
    """Load dataset from local cache if present, otherwise download and cache it.

    Returns a pandas DataFrame.
    """
    if use_cache and os.path.exists(CACHE_PATH):
        try:
            return pd.read_parquet(CACHE_PATH)
        except Exception:
            pass

    csv_cache = CACHE_PATH + '.csv'
    if use_cache and os.path.exists(csv_cache):
        try:
            return pd.read_csv(csv_cache)
        except Exception:
            pass

    return fetch_and_cache()


def license_text() -> str:
    """Return a short license citation for the upstream dataset.

    Edit as needed to reflect the dataset license.
    """
    return 'Source: data.gouv.fr - https://www.data.gouv.fr/datasets/trafic-aerien-commercial-mensuel-francais-par-paire-daeroports-par-sens-depuis-1990/'

   