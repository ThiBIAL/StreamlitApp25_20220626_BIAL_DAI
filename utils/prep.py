import pandas as pd
from typing import Dict, Any, Optional, Tuple


def _ensure_year_column(df: pd.DataFrame) -> pd.DataFrame:
    if 'ANMOIS' in df.columns:
        if pd.api.types.is_integer_dtype(df['ANMOIS']):
            df = df.copy()
            df['year'] = (df['ANMOIS'] // 100).astype(int)
            # extract month for future analyses
            try:
                df['month'] = (df['ANMOIS'] % 100).astype(int)
            except Exception:
                df['month'] = pd.NA
        else:
            # try to coerce to int then extract
            try:
                df = df.copy()
                df['ANMOIS'] = df['ANMOIS'].astype(int)
                df['year'] = (df['ANMOIS'] // 100).astype(int)
                # extract month for future analyses
                df['month'] = (df['ANMOIS'] % 100).astype(int)
            except Exception:
                df['year'] = pd.NA
                df['month'] = pd.NA
    else:
        df['year'] = pd.NA
    return df


def make_tables(df: pd.DataFrame, filters: Optional[Dict[str, Any]] = None, metric: Optional[str] = None) -> Dict[str, pd.DataFrame]:
    """Prepare aggregated tables for visualization.

        filters may include:
            - year_min, year_max (int)
            - countries (list of country codes/names matching CIE_PAYS)
            - nationality (str) : expected values 'F' or 'E' to filter CIE_NAT column

    metric may be a column name (e.g. 'CIE_PAX' or 'CIE_VOL') to use for aggregations.

    Returns dict: timeseries, by_region, geo
    """
    df = df.copy()
    df = _ensure_year_column(df)

    # Apply filters
    if filters:
        if 'year_min' in filters and 'year_max' in filters:
            ymin, ymax = filters['year_min'], filters['year_max']
            if pd.notna(ymin) and pd.notna(ymax):
                df = df[(df['year'] >= int(ymin)) & (df['year'] <= int(ymax))]
        if 'countries' in filters and filters['countries']:
            if 'CIE_PAYS' in df.columns:
                df = df[df['CIE_PAYS'].isin(filters['countries'])]
        if 'nationality' in filters and filters['nationality']:
            # filter by CIE_NAT column, expect 'F' or 'E' or similar codes
            if 'CIE_NAT' in df.columns:
                df = df[df['CIE_NAT'] == filters['nationality']]

    tables: Dict[str, pd.DataFrame] = {}

    # determine metric_col: prefer explicit metric parameter if valid
    metric_col = None
    if metric and metric in df.columns and pd.api.types.is_numeric_dtype(df[metric]):
        metric_col = metric
    else:
        numeric_cols = [c for c in df.columns if pd.api.types.is_numeric_dtype(df[c])]
        metric_col = 'CIE_PAX' if 'CIE_PAX' in df.columns else (numeric_cols[0] if numeric_cols else None)

    # timeseries (by year)
    if 'year' in df.columns and df['year'].notna().any() and metric_col:
        timeseries = df.groupby('year')[metric_col].sum().reset_index()
        tables['timeseries'] = timeseries
    else:
        tables['timeseries'] = pd.DataFrame()

    # by_region / nationality: keep aggregated metric and preserve first non-null normalized names/iso3 if present
    if 'CIE_PAYS' in df.columns and metric_col:
        agg_dict = {metric_col: 'sum'}
        if 'CIE_PAYS_EN' in df.columns:
            agg_dict['CIE_PAYS_EN'] = lambda x: x.dropna().astype(str).iloc[0] if x.dropna().size > 0 else None
        if 'CIE_PAYS_ISO3' in df.columns:
            agg_dict['CIE_PAYS_ISO3'] = lambda x: x.dropna().astype(str).iloc[0] if x.dropna().size > 0 else None

        by_region = df.groupby('CIE_PAYS').agg(agg_dict).reset_index().sort_values(metric_col, ascending=False)
        tables['by_region'] = by_region
    else:
        tables['by_region'] = pd.DataFrame()

    if 'lat' in df.columns and 'lon' in df.columns and metric_col:
        tables['geo'] = df[['lat', 'lon', metric_col]].groupby(['lat', 'lon']).sum().reset_index()
    else:
        tables['geo'] = pd.DataFrame()

    return tables


def filter_and_make(df: pd.DataFrame, year_min: Optional[int], year_max: Optional[int], countries: Optional[list], metric: Optional[str], nationality: Optional[str] = None) -> Tuple[pd.DataFrame, Dict[str, pd.DataFrame]]:
    """Convenience wrapper: apply filters and return filtered df + tables.
    """
    # Ensure year column exists before any filtering
    df = _ensure_year_column(df.copy())

    filters = {}
    if year_min is not None and year_max is not None:
        filters['year_min'] = year_min
        filters['year_max'] = year_max
    if countries:
        filters['countries'] = countries
    if nationality:
        filters['nationality'] = nationality

    tables = make_tables(df, filters=filters, metric=metric)

    # Return filtered df for KPI calculations
    df_filtered = df.copy()
    # ensure year col exists on df_filtered
    df_filtered = _ensure_year_column(df_filtered)

    if 'year_min' in filters and 'year_max' in filters:
        df_filtered = df_filtered[(df_filtered['year'] >= filters['year_min']) & (df_filtered['year'] <= filters['year_max'])]
    if 'countries' in filters:
        df_filtered = df_filtered[df_filtered['CIE_PAYS'].isin(filters['countries'])]
    if 'nationality' in filters:
        if 'CIE_NAT' in df_filtered.columns:
            df_filtered = df_filtered[df_filtered['CIE_NAT'] == filters['nationality']]
    return df_filtered, tables
