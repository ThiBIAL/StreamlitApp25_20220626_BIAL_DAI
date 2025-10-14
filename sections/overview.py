import streamlit as st


def render_overview(tables, df_filtered=None, metric=None, show_events: bool = False, events: list | None = None):
    st.markdown("# Overview")
    st.markdown("**Headline:** Aggregate traffic shows clear annual seasonality; external shocks (e.g. COVID) cause abrupt breaks in the series.")
    st.markdown("The Overview section presents key KPIs and the aggregated annual trend. Check \"Show event annotations\" in the sidebar to display notable event markers.")

    # Totals
    t1, t2, t3 = st.columns(3)
    try:
        total_pax = int(df_filtered['CIE_PAX'].sum()) if df_filtered is not None else 'N/A'
    except Exception:
        total_pax = 'N/A'
    try:
        total_vol = int(df_filtered['CIE_VOL'].sum()) if df_filtered is not None else 'N/A'
    except Exception:
        total_vol = 'N/A'
    t1.metric('Total pax', f"{total_pax:,}" if isinstance(total_pax, int) else total_pax)
    t2.metric('Total flights', f"{total_vol:,}" if isinstance(total_vol, int) else total_vol)

    # % between first and last available points (first -> last)
    yoy_display = 'N/A'
    delta_display = None
    try:
        ts = tables.get('timeseries')
        if ts is not None and not ts.empty and ts.shape[0] >= 2:
            # assume ts has columns [year, metric]
            first_val = float(ts.iloc[0, 1])
            last_val = float(ts.iloc[-1, 1])
            abs_delta = last_val - first_val
            # format absolute delta with thousands separator and sign
            try:
                abs_delta_int = int(round(abs_delta))
                delta_display = f"{abs_delta_int:+,}"
            except Exception:
                delta_display = f"{abs_delta:+.0f}"
            if first_val != 0:
                pct_change = (last_val / first_val - 1.0) * 100.0
                yoy_display = f"{pct_change:.1f}%"
            else:
                # first value zero: percent undefined, show 'inf' and absolute delta
                yoy_display = 'inf'
    except Exception:
        yoy_display = 'N/A'
        delta_display = None

    # Show percentage as main value and absolute delta as the metric delta
    if delta_display is not None:
        t3.metric('Change (first → last) %', yoy_display, delta=delta_display)
    else:
        t3.metric('Change (first → last) %', yoy_display)

    # Secondary KPIs: latest value and top region
    c1, c2 = st.columns(2)
    if tables.get('timeseries') is not None and not tables['timeseries'].empty:
        try:
            latest = tables['timeseries'].iloc[-1]
            c1.metric('Latest', f"{int(latest.iloc[1]):,}")
        except Exception:
            c1.metric('Latest', 'N/A')
    else:
        c1.metric('Latest', 'N/A')

    if tables.get('by_region') is not None and not tables['by_region'].empty:
        c2.metric('Top region', tables['by_region'].iloc[0, 0])
    else:
        c2.metric('Top region', 'N/A')

    st.subheader('Trend')
    from utils.viz import line_chart
    # label units and provide a reference line (median)
    line_chart(tables.get('timeseries'), show_events=show_events, events=events)
