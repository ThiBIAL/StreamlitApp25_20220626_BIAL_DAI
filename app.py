import streamlit as st
import pandas as pd
from utils.io import load_data
from utils.prep import filter_and_make
from utils.viz import heatmap_seasonality

st.set_page_config(page_title="StreamlitApp25 — ASP_CIE Dashboard", layout="wide")

@st.cache_data(show_spinner=False)
def get_raw():
    return load_data()

raw = get_raw()

st.title("ASP_CIE: CIES Air Traffic (2010–2024)")
st.markdown("Thibault BIAL | thibault.bial@efrei.net  ")
st.caption("Source: data.gouv.fr - ASP_CIE dataset (ID: fc84971a-240a-43bd-8d61-64e7fb8a0dc7)")
st.markdown("#EFREIDataStories2025  #EFREIParis #DataVisualization #Streamlit #DataStorytelling #OpenData")

# Sidebar filters
with st.sidebar:
    st.header("Filters")
    # Year options derived from ANMOIS -> year
    if 'ANMOIS' in raw.columns:
        years = sorted(pd.Series(raw['ANMOIS']).dropna().astype(int).unique())
        # convert to year if ANMOIS is yyyymm
        years = sorted(list({y // 100 for y in years}))
    else:
        years = []

    if years:
        year_min, year_max = st.select_slider("Year range", options=years, value=(min(years), max(years)))
    else:
        year_min, year_max = None, None

    countries = []
    if 'CIE_PAYS' in raw.columns:
        countries = st.multiselect("Country (CIE_PAYS)", options=sorted(raw['CIE_PAYS'].dropna().unique()))

    # Nationality filter: 'F' (French), 'E' (Foreign), or All
    nationality = None
    if 'CIE_NAT' in raw.columns:
        nat_choice = st.radio("Carrier nationality (CIE_NAT)", options=['All', 'F', 'E'], index=0)
        nationality = None if nat_choice == 'All' else nat_choice

    # Metric selection: derive from numeric columns + add useful computed metrics
    # Exclude date-like columns (ANMOIS) and helper 'year' from metric options
    numeric_cols = [c for c in raw.columns if pd.api.types.is_numeric_dtype(raw[c]) and c not in ('ANMOIS', 'year')]
    computed_metrics = []
    if 'CIE_PAX' in numeric_cols and 'CIE_VOL' in numeric_cols:
        computed_metrics.append('PAX_PER_VOL')
    if 'CIE_FRP' in numeric_cols and 'CIE_PAX' in numeric_cols:
        computed_metrics.append('FRP_PER_PAX')

    metric_options = numeric_cols + computed_metrics
    if not metric_options:
        metric = None
        st.write('No numeric metrics found in dataset')
    else:
        metric = st.selectbox("Metric", metric_options, index=0)

    # Heatmap controls: aggregation and years limit
    aggfunc = st.selectbox("Heatmap aggregation", options=['sum', 'mean'], index=0)
    years_limit = st.selectbox("Limit heatmap to last N years", options=['All'] + list(range(1, 11)), index=0)
    st.markdown("_Heatmap_: aggregates the selected metric by year (rows) and month (columns). Useful to spot seasonality, low or peak months. Choose `sum` or `mean` and limit to the last N years if needed._")
    show_events = st.checkbox("Show event annotations on trend (COVID, strikes)", value=False)

    # Define a small list of notable events (date in yyyymm format or ISO string)
    events = [
        {"date": 202003, "label": "COVID start", "details": "COVID-19 pandemic travel restrictions begin (Mar 2020)."},
        {"date": 202004, "label": "COVID peak", "details": "Strong drop in traffic (Apr 2020)."},
        {"date": 202109, "label": "Strikes", "details": "Airline strikes causing disruptions (Sep 2021)."}
    ]

# Prepare DataFrame with computed metrics if required
df_with_metrics = raw.copy()
if metric == 'PAX_PER_VOL':
    # avoid division by zero
    df_with_metrics['PAX_PER_VOL'] = df_with_metrics['CIE_PAX'] / df_with_metrics['CIE_VOL'].replace({0: pd.NA})
if metric == 'FRP_PER_PAX':
    df_with_metrics['FRP_PER_PAX'] = df_with_metrics['CIE_FRP'] / df_with_metrics['CIE_PAX'].replace({0: pd.NA})

# Apply filters and prepare tables using selected metric and nationality
df_filtered, tables = filter_and_make(df_with_metrics, year_min, year_max, countries, metric, nationality=nationality)

# KPI row will be shown just before the Overview section (moved further down)

# Seasonality heatmap moved to appear after the intro graph

# Render sections from sections/ modules
from sections.intro import render_intro
from sections.overview import render_overview
from sections.deep_dives import render_deep_dives
from sections.conclusions import render_conclusions

# Render each section (order: intro -> overview -> deep dives -> conclusions)
render_intro(raw=raw, df_filtered=df_filtered)
render_overview(tables=tables, df_filtered=df_filtered, metric=metric, show_events=show_events, events=events)

# Under Overview: list events with expanders for details
if show_events:
    st.markdown("### Notable events (click to expand)")
    for ev in events:
        with st.expander(f"{ev.get('label')} — {ev.get('date')}"):
            st.write(ev.get('details'))
# Heatmap seasonality: shown after the overview graph per user request
if metric is not None:
    st.markdown("### Seasonality (year × month)")
    yl = None if years_limit == 'All' else int(years_limit)
    heatmap_seasonality(df_filtered, metric, aggfunc=aggfunc, years_limit=yl, events=events, show_events=show_events)
    # Explanation paragraph for the heatmap
    st.markdown(
        "The seasonality heatmap aggregates the selected metric by year (rows) and month (columns). "
        "Darker/lighter cells indicate lower or higher values respectively. Use this view to spot recurring monthly patterns, "
        "identify months that consistently underperform (off-peak) or overperform (peak), and to observe whether recent years deviate from historical seasonal norms. "
        "When event annotations are enabled, you can also correlate abrupt deviations with specific external events (e.g., COVID or strikes)."
    )
render_deep_dives(df_filtered=df_filtered, tables=tables, metric=metric)
render_conclusions()

