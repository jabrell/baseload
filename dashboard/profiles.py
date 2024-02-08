import streamlit as st
import pandas as pd
from .data import get_generation, normalize_generation, get_profiles
from .graphs import plot_profile
import os


def profile_dashboard(fn_profiles: str = None):
    """Run the dashboard based on profiles

    Args:
        fn_profiles: path to file with profiles
    """
    all_countries = list(pd.read_parquet(fn_profiles, columns="country").unique())
    country = "DE"
    sh_wind = 0.5
    sh_solar = 0.2
    sh_base = 0.4
    total_demand = 1000000

    with st.sidebar:
        st.subheader("Determine profiles and total demand")
        country = st.selectbox(
            "Choose the country used for profiles",
            all_countries,
            index=all_countries.index("DE"),
        )
        total_demand = st.number_input("Set total annual demand", 1000000)

        # get data
        df_gen = get_generation(fn_profiles, country=country)
        df_norm = normalize_generation(
            df_gen,
            shares={"Wind": sh_wind, "Solar": sh_solar, "Baseload": sh_base},
            total_demand=total_demand,
        )
        profiles = get_profiles(df_norm)

        # create plots
        p = "Hourly: Winter"
        fig = plot_profile(profiles[p], title=p)
        st.plotly_chart(fig)
