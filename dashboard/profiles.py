import streamlit as st
import pandas as pd
from .data import get_generation, normalize_generation, get_profiles, get_storage_stats
from .graphs import plot_profile, plot_daily_generation


def make_grid(cols: int, rows: int):
    """Make grid of streamlit cells
    see: https://towardsdatascience.com/how-to-create-a-grid-layout-in-streamlit-7aff16b94508

    Args:
        cols: number of columns
        rows: number of rows
    """
    grid = [0] * cols
    for i in range(cols):
        with st.container():
            grid[i] = st.columns(rows)
    return grid


def profile_dashboard(fn_profiles: str = None):
    """Run the dashboard based on profiles

    Args:
        fn_profiles: path to file with profiles
    """
    all_countries = list(
        pd.read_parquet(fn_profiles, columns=["country"])["country"]
        .sort_values()
        .unique()
    )

    # layout settings
    st.set_page_config(
        page_title="Baseload Paper",
        layout="wide",
    )
    tabDaily, tabProfile = st.tabs(["Daily Generation", "Profiles"])

    # side bar
    with st.sidebar:
        show_hourly_profiles = st.toggle("Enable hourly profile tab")
        st.subheader("Basic data")
        st.markdown("Country and year for profiles")
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

        st.subheader("Supply configuration")
        sh_wind = st.slider("Share wind in total demand", 0, 120, 30) / 100
        sh_solar = st.slider("Share solar in total demand", 0, 120, 30) / 100
        sh_base = st.slider("Share baseload in total demand", 0, 120, 30) / 100
        st.markdown(
            f"**Share of total supply in demand: {round((sh_base + sh_solar + sh_wind)*100,0)}%**"
        )
    # get data
    df_gen = get_generation(fn_profiles, country=country, year=year)
    df_norm = normalize_generation(
        df_gen,
        shares={"Wind": sh_wind, "Solar": sh_solar, "Baseload": sh_base},
        total_demand=total_demand,
    )
    profiles = get_profiles(df_norm)
    df_storage, df_storage_stats = get_storage_stats(df_norm)

    # Tab with daily generation
    with tabDaily:
        st.markdown("""## Daily Generation and Demand""")
        col1, col2 = st.columns([1, 3])
        with col2:
            percent_daily_demand = st.toggle("Show as percent of daily demand")
        with col1:
            days = st.slider("Numbers of days for aggregation", 1, 10, 1)
        fig = plot_daily_generation(
            df_norm, days=days, percent_daily_demand=percent_daily_demand
        )
        st.plotly_chart(fig, use_container_width=True)
        st.markdown("""**Overview Imbalances**""")
        st.dataframe(df_storage_stats.T)

    # tab with average profiles
    with tabProfile:
        if show_hourly_profiles:
            st.text("test")
        else:
            st.text("test")
        all_profiles = [
            "Hourly: Year",
            "Monthly",
            "Hourly: Winter",
            "Hourly: Spring",
            "Hourly: Summer",
            "Hourly: Autumn",
        ]
        cells = [x for xs in make_grid(3, 2) for x in xs]
        for i, profile in enumerate(all_profiles):
            fig = plot_profile(profiles[profile], title=profile)
            with cells[i]:
                st.plotly_chart(fig, use_container_width=True)
