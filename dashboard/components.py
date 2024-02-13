from typing import Any
import streamlit as st
import pandas as pd
import numpy as np
from .data import get_generation, normalize_generation, get_storage_stats


def sidebar(
    fn_gen: str, fn_cap: str, years: list[int] = range(2015, 2024)
) -> dict[str, Any]:
    """Create streamlit sidebar

    Args:
        fn_gen: name of file with generation data
        fn_cap: name of file with capacity data
        years: year to include in select field

    Returns:
        dictionary with the following key:
            country, year, total_demand, sh_wind, sh_solar, sh_base
    """
    all_countries = list(
        pd.read_parquet(fn_cap, columns=["country"])["country"].sort_values().unique()
    )
    with st.sidebar:
        col1, col2 = st.columns(2)
        with col1:
            country = st.selectbox(
                "Country",
                options=all_countries,
                index=all_countries.index("DE"),
            )
        with col2:
            years = list(range(2015, 2024))
            year = st.selectbox("Year", list(range(2015, 2024)), index=(len(years) - 1))
        total_demand = st.number_input("Scale annual demand to (0 for no scaling)", 0)

        # get the data and add the annual overview
        st.markdown("**Observed**")
        df_gen, df_annual = get_generation(
            fn_gen=fn_gen, fn_cap=fn_cap, country=country, year=year
        )

        st.table(
            df_annual.assign(
                **{
                    "Capacity [GW]": lambda df: (df["Capacity"] / 1000).round(0),
                    "Annual Gen. [TMh]": lambda df: (
                        df["AnnualGeneration"] / 1000000
                    ).round(0),
                    "Fullload Hours [#]": lambda df: (df["Fullload Hours"]).round(0),
                    "Demand Share [%]": lambda df: (df["DemandShare"]).round(0),
                }
            )
            .loc[
                ["Wind", "Solar"],
                [
                    "Capacity [GW]",
                    "Annual Gen. [TMh]",
                    "Fullload Hours [#]",
                    "Demand Share [%]",
                ],
            ]
            .T.style.format("{:.0f}")
        )

        st.markdown("**Set demand shares**")
        df_w = (
            int(df_annual.at["Wind", "DemandShare"])
            if ~np.isnan(df_annual.at["Wind", "DemandShare"])
            else 0
        )
        df_s = (
            int(df_annual.at["Solar", "DemandShare"])
            if ~np.isnan(df_annual.at["Solar", "DemandShare"])
            else 0
        )
        df_b = max(100 - df_w - df_s, 0)
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            sh_wind = st.number_input("Wind", 0, 120, df_w, step=5) / 100
        with col2:
            sh_solar = st.number_input("Solar", 0, 120, df_s, step=5) / 100
        with col3:
            sh_base = st.number_input("Baseload", 0, 120, df_b, step=5) / 100
        with col4:
            total = int((sh_base + sh_solar + sh_wind) * 100)
            st.number_input("Total", total, total, total)
        df_norm = normalize_generation(
            df_gen,
            shares={
                "Wind": sh_wind,
                "Solar": sh_solar,
                "Baseload": sh_base,
            },
            total_demand=total_demand,
        )
        df_storage, df_storage_stats = get_storage_stats(df_norm)
        df_cap_ = (df_norm.sum() / (df_annual["Fullload Hours"] + 0.0000001))[
            ["Wind", "Solar"]
        ] / 1000
        st.markdown(
            f"""Implied capacity [GW]:          
- Wind {round(df_cap_["Wind"],2)}
- Solar {round(df_cap_["Solar"],2)}
            """
        )
        return df_storage, df_storage_stats
