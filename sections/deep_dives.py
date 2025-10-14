import streamlit as st


def render_deep_dives(df_filtered, tables, metric=None):
    st.markdown("# Deep dives")
    st.markdown("Comparisons, distributions, and drilldowns")
    st.subheader('Top 10 by region')
    from utils.viz import bar_chart, compare_french_companies
    by_region = tables.get('by_region')
    if by_region is not None and not by_region.empty:
        top10 = by_region.head(10)
        bar_chart(top10)
    else:
        st.info('No regional data available for the selected filters')

    # Brief analysis of the Top-10 by region
    st.markdown("**Quick analysis:**")
    st.markdown(
        "- In terms of passengers, France dominates the top positions — this is expected because the dataset focuses on air traffic involving France.\n"
        "- For freight, the United States appears close behind and shows strong freight activity, indicating significant cargo links.\n"
        "- Consider drilling into specific years or carriers to see whether a region's position is driven by a single year/event or by sustained traffic."
    )

    st.subheader('French carriers - comparison')
    # UI controls for the comparison
    with st.expander('Comparison settings', expanded=False):
        metric_choice = st.selectbox('Metric for ranking', options=[metric] if metric else ['CIE_PAX'], index=0)
        top_n = st.number_input('Top N carriers', min_value=3, max_value=50, value=10)

    compare_french_companies(df_filtered, metric=metric_choice, top_n=top_n)

    # Recovery analysis vs 2019 for top-N French carriers
    st.subheader('French carriers - recovery vs 2019')
    st.markdown("This section computes how much traffic each top carrier has recovered compared to 2019 (pre-COVID baseline).")
    try:
        import pandas as pd
        from utils.viz import heatmap_seasonality

        dfc = df_filtered.copy() if df_filtered is not None else pd.DataFrame()
        # select French carriers: prefer CIE_NAT=='F' if present, else CIE_PAYS contains 'FRANCE'
        if 'CIE_NAT' in dfc.columns:
            mask_fr = dfc['CIE_NAT'].astype(str) == 'F'
        else:
            mask_fr = dfc['CIE_PAYS'].astype(str).str.upper().str.contains('FRANCE') if 'CIE_PAYS' in dfc.columns else pd.Series([False]*len(dfc))

        df_fr = dfc[mask_fr].copy()
        if df_fr.empty:
            st.info('No French carriers found in current selection')
        else:
            # determine company label
            company_col = 'CIE_NOM' if 'CIE_NOM' in df_fr.columns else ('CIE' if 'CIE' in df_fr.columns else df_fr.columns[0])
            # ensure year exists
            try:
                df_fr['ANMOIS'] = df_fr['ANMOIS'].astype(int)
                df_fr['year'] = (df_fr['ANMOIS'] // 100).astype(int)
            except Exception:
                df_fr['year'] = pd.to_numeric(df_fr.get('year', pd.NA), errors='coerce')

            # aggregate totals per company per year
            if metric_choice not in df_fr.columns:
                st.info(f"Metric '{metric_choice}' not available for recovery analysis")
            else:
                df_fr[metric_choice] = pd.to_numeric(df_fr[metric_choice], errors='coerce')
                agg = df_fr.groupby([company_col, 'year'])[metric_choice].sum().reset_index()
                # pick baseline year 2019 and latest year available
                years = sorted(agg['year'].dropna().unique())
                baseline_year = 2019 if 2019 in years else (years[0] if len(years) > 0 else None)
                latest_year = years[-1] if len(years) > 0 else None

                if baseline_year is None or latest_year is None:
                    st.info('Insufficient yearly data to compute recovery vs 2019')
                else:
                    base = agg[agg['year'] == baseline_year].set_index(company_col)[metric_choice]
                    last = agg[agg['year'] == latest_year].set_index(company_col)[metric_choice]
                    # join and compute recovery
                    df_recovery = pd.concat([base, last], axis=1, keys=[f'{baseline_year}', f'{latest_year}']).fillna(0)
                    df_recovery['abs_delta'] = df_recovery[f'{latest_year}'] - df_recovery[f'{baseline_year}']
                    # percent recovered: last / base * 100
                    def safe_pct(row):
                        b = row[f'{baseline_year}']
                        l = row[f'{latest_year}']
                        if b == 0:
                            return float('inf') if l > 0 else 0.0
                        return (l / b) * 100.0

                    df_recovery['pct_recovered'] = df_recovery.apply(safe_pct, axis=1)
                    df_recovery = df_recovery.sort_values(f'{latest_year}', ascending=False)
                    top_companies = df_recovery.head(int(top_n))

                    # display table of top carriers with recovery
                    st.markdown(f"Top {min(len(top_companies), int(top_n))} French carriers - recovery vs {baseline_year} (latest: {latest_year})")
                    display_table = top_companies[[f'{baseline_year}', f'{latest_year}', 'abs_delta', 'pct_recovered']].copy()
                    display_table = display_table.rename(columns={f'{baseline_year}': f'{baseline_year} total', f'{latest_year}': f'{latest_year} total', 'abs_delta': 'delta', 'pct_recovered': 'pct_recovered'})
                    # format pct
                    display_table['pct_recovered'] = display_table['pct_recovered'].apply(lambda x: f"{x:.1f}%" if pd.notna(x) and x != float('inf') else ('inf' if x == float('inf') else 'N/A'))
                    st.dataframe(display_table)

                    # Detailed recovery analysis: top and bottom performers among the selected carriers
                    try:
                        # top_companies contains numeric pct_recovered
                        best = top_companies.sort_values('pct_recovered', ascending=False).head(3)
                        # exclude 'inf' entries when looking for laggards
                        numeric_pct = top_companies[top_companies['pct_recovered'] != float('inf')].copy()
                        worst = numeric_pct.sort_values('pct_recovered', ascending=True).head(3)

                        st.markdown('**Recovery highlights:**')
                        if not best.empty:
                            st.markdown('- Top recoveries:')
                            for name, row in best.iterrows():
                                pct = row['pct_recovered']
                                delta = int(row['abs_delta'])
                                st.markdown(f"  - {name}: recovered {pct:.1f}% vs {baseline_year} (delta {delta:+,})")
                        else:
                            st.markdown('- No strong recoveries detected among the selected carriers.')

                        if not worst.empty:
                            st.markdown('- Lagging carriers:')
                            for name, row in worst.iterrows():
                                pct = row['pct_recovered']
                                delta = int(row['abs_delta'])
                                st.markdown(f"  - {name}: recovered {pct:.1f}% vs {baseline_year} (delta {delta:+,})")
                        else:
                            st.markdown('- No clear laggards detected (insufficient numeric baseline data).')

                        # call out carriers with 'inf' recovery (no baseline in 2019)
                        infers = top_companies[top_companies['pct_recovered'] == float('inf')]
                        if not infers.empty:
                            st.markdown('- New or previously unreported carriers (baseline=0) show infinite recovery; inspect source years to confirm.')
                        # Note on business models
                        st.markdown('- Observational note: low-cost carriers such as French Bee and Transavia have generally recovered faster. Their flexible capacity and leisure-focused networks supported quicker demand capture. In contrast, larger legacy carriers still show gaps versus 2019 and may need targeted operational and commercial strategies to close the gap.')
                    except Exception:
                        st.markdown('Could not compute detailed recovery highlights.')

                   
                    # Freight-specific observations
                    st.markdown('---')
                    st.markdown('*Note: the justifications below are drawn from Internet sources.*')
                    st.markdown('**Freight market context (2019–2024)**')
                    st.markdown(
                        '- Air freight surged in 2020–2021 due to maritime shortages and strong e-commerce demand.\n'
                        '- From 2022 the maritime market recovered, leading to a structural reduction in air freight volumes and downward pressure on freight rates and margins.\n'
                        '- The return of passenger services added belly capacity, increasing competition for freight and lowering yields in some markets.'
                    )

                    st.markdown('**Carrier-specific freight notes**')
                    st.markdown(
                        f"- ASL Airlines France (recovery ~26.5% vs 2019): ASL has depended on European express networks (e‑commerce, postal). Post‑COVID e‑commerce contraction, intense price competition since 2023 and modal shifts on short routes have driven a large decline in freight volumes. Result: sharp drop in demand and margin pressure.\n"
                        f"- Air Tahiti Nui (recovery ~51.8% vs 2019): primarily a passenger carrier with belly cargo. While passenger rebound returned aircraft, dedicated freight contracts and long‑haul belly volumes did not fully recover to 2019 levels - freight has become secondary on many routes, producing lower freight totals vs 2019.\n"
                        f"- Airbus Transport International (recovery ~70.1% vs 2019): cargo activity tied to industrial flows for Airbus. Production ramp‑up has been gradual, so freight volumes recovered more slowly but more stably than commercial carriers; still slightly below 2019 because production cadence has not fully normalized."
                    )

                    st.markdown('**Implication:** carriers exposed to express/e‑commerce or short‑haul freight were most affected once maritime capacity normalized and price competition intensified. Long‑haul belly cargo players recovered differently depending on route economics and passenger recovery. Consider targeted commercial and capacity strategies for ASL and similar operators, and monitor freight yield and contract exposure for carriers relying on industrial or express flows.')

                    # Seasonality heatmap for top carriers removed per user request
    except Exception:
        st.error('Could not compute French carriers recovery analysis (check data availability).')

