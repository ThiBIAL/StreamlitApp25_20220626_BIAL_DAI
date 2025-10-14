import streamlit as st
from utils.io import license_text


def render_intro(raw=None, df_filtered=None):
    """Render project intro: context, objectives, data caveats.
    Accepts `raw` (full dataset) and optional `df_filtered` to show a small filtered sample below the raw rows count.
    """
    st.markdown("# Introduction")
    # Headline insight
    st.markdown(
       "### ✈️ Air Traffic Disruptions in France (2010–2024)\n"
       "\nOver the past decade, the air transport sector has faced unprecedented shocks - from the COVID-19 pandemic to strikes and operational disruptions - shaking the entire industry. These disruptions didn’t just reduce passenger volumes; they reshaped how airlines operate and how quickly they can bounce back.\n"
       "\n"
       )
    st.info(
        "🧭 Main question: How did these events impact air traffic over time, and which French carriers showed the strongest vs weakest recovery?"
        )
    st.markdown(
        "### 🧾 About the ASP_CIE Dataset\n"
        "This project is based on the ASP_CIE dataset (2010–2024), which tracks key monthly indicators by airline:\n"
        "\n"
        "**Columns:**\n"
        "- **ANMOIS**: Period (format YYYYMM, e.g., 201601 for January 2016)\n"
        "- **CIE**: Carrier (ICAO code)\n"
        "- **CIE_NOM**: Carrier commercial name\n"
        "- **CIE_NAT**: Carrier nationality [F=French, E=Foreign]\n"
        "- **CIE_PAYS**: Carrier country\n"
        "- **CIE_PAX**: Number of passengers carried\n"
        "- **CIE_FRP**: Freight and mail carried (in tons)\n"
        "- **CIE_PEQ**: Equivalent passengers carried [1Peq = 1 pax or 0.1 ton of freight/mail]\n"
        "- **CIE_PKT**: Passenger kilometers transported (in billions)\n"
        "- **CIE_TKT**: Ton kilometers transported (in billions)\n"
        "- **CIE_PEQKT**: Equivalent passenger kilometers transported (in billions) [1Peq = 1 pax or 0.1 ton of freight/mail]\n"
        "- **CIE_VOL**: Number of commercial flights\n"
        "\n"
    )
    st.info(
        "📊 We use aggregated time series to analyze long-term trends, seasonality, and the impact of major events."
    )
    st.markdown("### Data source & license")
    st.write(license_text())

    
    if raw is not None:
        st.markdown(f"**Rows in raw dataset:** {len(raw)}")

    # If a filtered sample is provided, show a short explanation and the first 20 rows
    if df_filtered is not None:
        st.subheader('Filtered sample')
        st.markdown("**What is filtered:**")
        st.markdown("- Year range selected in the sidebar (year_min to year_max).\n- Countries selected in the sidebar (if any).\n- The dataset is filtered to only include rows matching these selections.")
        st.markdown("**Derived / added columns for analysis:**")
        st.markdown("- `year`: extracted from `ANMOIS` (yyyymm → yyyy).\n- `month`: extracted from `ANMOIS` (yyyymm → mm).\n- `PAX_PER_VOL`: passengers per flight (if selected/computed).\n- `FRP_PER_PAX`: freight per passenger (if selected/computed).")
        st.caption("This table shows the first 20 rows of the filtered sample.")
        st.dataframe(df_filtered.head(20))
        st.markdown(
            "This sample is intended to give a quick, concrete overview of how the dataset is structured: the key columns, typical values, and any derived fields added for analysis.\n\nIt helps validate assumptions about column types and missing values before diving into aggregated charts and comparisons."
        )

    # Data quality & limitations: keep this under the filtered sample to show raw vs filtered counts
    if raw is not None:
        st.markdown("### Data Quality & Limitations")
        with st.expander("Data quality checks"):
            st.write(license_text())
            st.write(f"Total rows (raw): {len(raw)}")
            st.write(f"Total rows (filtered): {len(df_filtered) if df_filtered is not None else 'N/A'}")

            st.write("Missing per column:")
            try:
                st.dataframe(raw.isna().sum().to_frame('missing_count'))
            except Exception:
                # if raw is not a DataFrame or something unexpected, skip
                st.write("Could not compute missing counts for raw dataset.")

            # Duplicate checks
            try:
                dup_raw_any = int(raw.duplicated(keep=False).sum())
                dup_filtered_any = int(df_filtered.duplicated(keep=False).sum()) if df_filtered is not None else None
            except Exception:
                dup_raw_any = None
                dup_filtered_any = None

            st.write("---")
            st.write("Duplicate rows (any columns):")
            if dup_raw_any is not None:
                st.write(f"Raw duplicate rows (counting all rows that are part of a duplicate group): {dup_raw_any}")
                st.write(f"Filtered duplicate rows: {dup_filtered_any}")
            else:
                st.write("Could not compute duplicate counts for the dataset.")

            # Key-based duplicate checks (if sensible key columns exist)
            key_cols = None
            if 'ANMOIS' in raw.columns and 'CIE' in raw.columns:
                key_cols = ['ANMOIS', 'CIE']
            elif 'ANMOIS' in raw.columns and 'CIE_PAYS' in raw.columns:
                key_cols = ['ANMOIS', 'CIE_PAYS']

            if key_cols:
                try:
                    dup_raw_key = int(raw.duplicated(subset=key_cols, keep=False).sum())
                    dup_filtered_key = int(df_filtered.duplicated(subset=key_cols, keep=False).sum()) if df_filtered is not None else None
                except Exception:
                    dup_raw_key = None
                    dup_filtered_key = None

                st.write(f"---\nDuplicate rows by key {key_cols}:")
                if dup_raw_key is not None:
                    st.write(f"Raw: {dup_raw_key} rows part of duplicate groups by key")
                    st.write(f"Filtered: {dup_filtered_key}")

                    # Show examples (first 10 duplicates)
                    try:
                        dup_examples = raw[raw.duplicated(subset=key_cols, keep=False)].sort_values(key_cols).head(10)
                        if not dup_examples.empty:
                            st.markdown("Example duplicate rows by key (raw):")
                            st.dataframe(dup_examples)
                    except Exception:
                        pass
                else:
                    st.write("Could not compute key-based duplicates.")
            else:
                st.write("No sensible key columns (ANMOIS/CIE) found for key-based duplicate checks.")

            # Show a small sample of any duplicate rows (all columns)
            if dup_raw_any and dup_raw_any > 0:
                st.markdown("Sample duplicate rows (raw, first 10):")
                st.dataframe(raw[raw.duplicated(keep=False)].head(10))
            if dup_filtered_any and dup_filtered_any > 0:
                st.markdown("Sample duplicate rows (filtered, first 10):")
                st.dataframe(df_filtered[df_filtered.duplicated(keep=False)].head(10))
