import streamlit as st
import plotly.express as px
import pandas as pd
import numpy as np
import calendar


def line_chart(df, show_events: bool = False, events: list | None = None):
    """Render a timeseries line chart. Optionally draw vertical event annotations.

    events: list of dicts with keys: {
      'date': int or str (yyyymm or yyyy-mm),
      'label': short label,
      'details': longer text
    }
    """
    if df is None or df.empty:
        st.info('No timeseries to show')
        return
    x_col, y_col = df.columns[0], df.columns[1]

    # Plot using the original dataframe to preserve original axis/appearance
    fig = px.line(df, x=x_col, y=y_col, markers=True, labels={x_col: x_col, y_col: y_col})
    fig.update_layout(template='plotly_white')

    # Add a median reference line/band to help interpret levels
    try:
        median_val = pd.to_numeric(df[y_col], errors='coerce').median()
        if not np.isnan(median_val):
            fig.add_hline(y=median_val, line_dash='dot', line_color='gray', annotation_text=f'Median: {median_val:.0f}', annotation_position='bottom right')
            # subtle band ±10% around median
            low = median_val * 0.9
            high = median_val * 1.1
            fig.add_shape(type='rect', xref='paper', yref='y', x0=0, x1=1, y0=low, y1=high, fillcolor='LightSalmon', opacity=0.08, layer='below', line_width=0)
    except Exception:
        pass

    # Add event annotations if requested
    if show_events and events:
        import plotly.graph_objects as go

        # operate on the original dataframe for matching x values
        df_x = df.copy()
        df_x[y_col] = pd.to_numeric(df_x[y_col], errors='coerce')

        y_vals = df_x[y_col]
        y_min = float(y_vals.min()) if not y_vals.isna().all() else 0.0
        y_max = float(y_vals.max()) if not y_vals.isna().all() else 1.0

        original_x = df_x[x_col]

        # Pre-detect x format: yearly (YYYY) vs monthly (YYYYMM) vs other
        x_as_str = original_x.astype(str)
        is_yearly = x_as_str.str.match(r'^\d{4}$').all()
        is_yyyymm = x_as_str.str.match(r'^\d{6}$').all()

        for ev in events:
            date_val = ev.get('date')
            x_plot_val = None
            idx = None

            # If the series is yearly and event is yyyymm (int), map to year
            try:
                d_int = int(date_val)
            except Exception:
                d_int = None

            if is_yearly and d_int is not None and d_int >= 1000:
                # convert yyyymm or yyyy to year
                year_val = d_int // 100 if d_int > 9999 else d_int
                matches = original_x.astype(str) == str(year_val)
                if matches.any():
                    idx = matches.idxmax()
                    x_plot_val = original_x.loc[idx]

            # If series stores YYYYMM and event is integer/str YYYYMM, match directly
            if x_plot_val is None and d_int is not None:
                matches = original_x.astype(str) == str(d_int)
                if matches.any():
                    idx = matches.idxmax()
                    x_plot_val = original_x.loc[idx]

            # Try exact string match as fallback
            if x_plot_val is None:
                s_val = str(date_val)
                matches = original_x.astype(str) == s_val
                if matches.any():
                    idx = matches.idxmax()
                    x_plot_val = original_x.loc[idx]

            # Final fallback: nearest by datetime distance if conversion possible
            if x_plot_val is None:
                try:
                    xs_dt = pd.to_datetime(original_x.astype(str), errors='coerce')
                    x_dt = pd.to_datetime(str(date_val), errors='coerce')
                    if not pd.isna(x_dt) and not xs_dt.isna().all():
                        diffs = (xs_dt - x_dt).abs()
                        idx = diffs.idxmin()
                        x_plot_val = original_x.loc[idx]
                except Exception:
                    pass

            if x_plot_val is None or idx is None:
                # can't place this event reliably
                continue

            # y value at the matched index
            y_marker = float(df_x.loc[idx, y_col]) if not pd.isna(df_x.loc[idx, y_col]) else y_max

            # Add a visible vertical line (span entire plot) for the event
            try:
                fig.add_vline(x=x_plot_val, line=dict(color='crimson', width=2, dash='dash'), opacity=0.9, layer='below')
            except Exception:
                # if xref mismatch (categorical vs numeric), add a shape instead
                fig.add_shape(dict(type='line', x0=x_plot_val, x1=x_plot_val, y0=0, y1=1, xref='x', yref='paper', line=dict(color='crimson', width=2, dash='dash')))

            # add marker on the original x scale (bigger + outline)
            fig.add_trace(go.Scatter(x=[x_plot_val], y=[y_marker], mode='markers',
                                     marker=dict(size=12, color='crimson', symbol='diamond', line=dict(width=1, color='black')),
                                     name='Event', hovertemplate=f"{ev.get('label')}: {ev.get('details')}", showlegend=False)
                          )

            # place annotation at the top of the plot area (paper coordinates) to ensure visibility
            fig.add_annotation(x=x_plot_val, y=0.98, xref='x', yref='paper', text=ev.get('label', ''),
                               showarrow=True, arrowhead=2, ax=0, ay=-30,
                               font=dict(color='white', size=10),
                               bgcolor='rgba(220,20,60,0.9)', bordercolor='rgba(0,0,0,0.2)')

    st.plotly_chart(fig, use_container_width=True)


def compare_french_companies(df: pd.DataFrame, metric: str = 'CIE_PAX', top_n: int = 10):
    """Compare French companies: top-N bar chart and yearly trend for those top-N.

    - df: full (or filtered) DataFrame containing at least 'CIE_PAYS', company name/code and metric.
    - metric: column to aggregate (default 'CIE_PAX').
    - top_n: number of top companies to display.
    """
    if df is None or df.empty:
        st.info('No data to compare companies')
        return

    if 'CIE_PAYS' not in df.columns:
        st.info('Dataset missing CIE_PAYS column')
        return

    dfc = df.copy()
    # Select rows for France
    try:
        mask = dfc['CIE_PAYS'].astype(str).str.upper().str.contains('FRANCE')
    except Exception:
        mask = dfc['CIE_PAYS'].astype(str).str.upper() == 'FRANCE'
    df_fr = dfc[mask].copy()

    if df_fr.empty:
        st.info('No French companies found in the current selection')
        return

    # Determine company label column
    company_col = 'CIE_NOM' if 'CIE_NOM' in df_fr.columns else ('CIE' if 'CIE' in df_fr.columns else df_fr.columns[0])

    # Ensure metric exists and is numeric
    if metric not in df_fr.columns:
        st.info(f"Metric '{metric}' not found for comparison")
        return
    df_fr[metric] = pd.to_numeric(df_fr[metric], errors='coerce')

    # Aggregate totals per company
    agg = df_fr.groupby(company_col)[metric].sum().reset_index().sort_values(metric, ascending=False)
    top = agg.head(int(top_n))

    # Bar chart: top N companies with clear axis labels and source
    fig_bar = px.bar(top, x=company_col, y=metric,
                     title=f'Top {len(top)} French companies by {metric}', labels={company_col: 'Company', metric: metric})
    fig_bar.update_layout(template='plotly_white', xaxis_tickangle=-45)
    # Source annotation intentionally omitted for the Top-N companies chart
    st.plotly_chart(fig_bar, use_container_width=True)

    # Yearly trend for top companies (if ANMOIS available)
    if 'ANMOIS' in df_fr.columns:
        try:
            df_fr['year'] = (df_fr['ANMOIS'].astype(int) // 100).astype(int)
            ts = df_fr.groupby(['year', company_col])[metric].sum().reset_index()
            top_names = top[company_col].tolist()
            ts_top = ts[ts[company_col].isin(top_names)]
            if not ts_top.empty:
                # Combined multi-series line chart (one line per company) — preferred for comparison
                fig_line = px.line(ts_top, x='year', y=metric, color=company_col, markers=True,
                                   title=f'Yearly trend for top {len(top_names)} French companies')
                fig_line.update_layout(template='plotly_white')
                st.plotly_chart(fig_line, use_container_width=True)
            else:
                st.info('No yearly data available for the selected top companies')
        except Exception:
            st.info('Could not compute yearly trends for companies')
    else:
        st.info('ANMOIS column missing: cannot show yearly trend')


def bar_chart(df):
    if df is None or df.empty:
        st.info('No bar chart data')
        return
    x_col, y_col = df.columns[0], df.columns[1]
    fig = px.bar(df, x=x_col, y=y_col)
    fig.update_layout(template='plotly_white')
    st.plotly_chart(fig, use_container_width=True)


def heatmap_seasonality(df: pd.DataFrame, metric: str, aggfunc: str = 'sum', years_limit: int | None = None, events: list | None = None, show_events: bool = False):
    """Render a year x month heatmap for the selected metric.

    Parameters
    - df: DataFrame containing an 'ANMOIS' column (yyyymm or int) and the metric column.
    - metric: column name to aggregate and plot.
    - aggfunc: aggregation function name ('sum' or 'mean').
    """
    if df is None or df.empty:
        st.info('No data for heatmap')
        return
    if metric is None or metric not in df.columns:
        st.info('Select a metric to show the seasonality heatmap')
        return
    if 'ANMOIS' not in df.columns:
        st.info('ANMOIS column required for seasonality heatmap')
        return

    # Prepare year and month
    tmp = df.copy()
    try:
        tmp['ANMOIS'] = tmp['ANMOIS'].astype(int)
    except Exception:
        pass
    tmp['year'] = (tmp['ANMOIS'] // 100).astype(int)
    tmp['month'] = (tmp['ANMOIS'] % 100).astype(int)

    # Optionally limit to last N years
    if years_limit and isinstance(years_limit, int) and years_limit > 0:
        max_year = tmp['year'].max()
        min_year = max_year - (years_limit - 1)
        tmp = tmp[tmp['year'].between(min_year, max_year)]

    # Aggregate
    if aggfunc == 'mean':
        agg = tmp.groupby(['year', 'month'])[metric].mean().reset_index()
    else:
        agg = tmp.groupby(['year', 'month'])[metric].sum().reset_index()

    # Pivot to matrix years x months
    pivot = agg.pivot(index='year', columns='month', values=metric)

    # Ensure months 1..12 exist
    months = list(range(1, 13))
    pivot = pivot.reindex(columns=months)

    # Label months
    month_labels = [calendar.month_abbr[m] for m in months]

    if pivot.isna().all(axis=None):
        st.info('No data available for the selected metric / period to draw a heatmap')
        return

    fig = px.imshow(
        pivot.values,
        x=month_labels,
        y=pivot.index.astype(str),
        labels={'x': 'Month', 'y': 'Year', 'color': metric},
        aspect='auto',
        color_continuous_scale='Viridis'
    )
    fig.update_layout(template='plotly_white', yaxis_autorange='reversed')

    # Optionally overlay event points on the heatmap (year x month)
    if show_events and events:
        try:
            import plotly.graph_objects as go

            xs = []
            ys = []
            texts = []
            for ev in events:
                date_val = ev.get('date')
                year = None
                month = None
                # try integer yyyymm or yyyy
                try:
                    d_int = int(date_val)
                    if d_int >= 100000:  # yyyymm (6 digits)
                        year = d_int // 100
                        month = d_int % 100
                    elif d_int >= 1000:  # yyyy (4+) -> default to month 7 (mid-year)
                        year = d_int
                        month = 7
                except Exception:
                    # try parsing as date string
                    try:
                        dt = pd.to_datetime(str(date_val), errors='coerce')
                        if not pd.isna(dt):
                            year = int(dt.year)
                            month = int(dt.month)
                    except Exception:
                        pass

                if year is None or month is None:
                    continue

                # check if this year and month exist in pivot
                if year in pivot.index and 1 <= month <= 12:
                    xs.append(month_labels[month - 1])
                    ys.append(str(year))
                    texts.append(f"{ev.get('label')}: {ev.get('details')}")

            if xs and ys:
                fig.add_trace(go.Scatter(x=xs, y=ys, mode='markers',
                                         marker=dict(size=14, color='crimson', symbol='diamond', line=dict(width=1, color='black')),
                                         hovertext=texts, hoverinfo='text', showlegend=False))
        except Exception:
            # if plotly.graph_objects not available or overlay fails, ignore gracefully
            pass

    st.plotly_chart(fig, use_container_width=True)


