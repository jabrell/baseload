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
        st.subheader("Basic data")
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
        st.divider()

        st.subheader("Supply shares")
        col1, col2, col3 = st.columns(3)
        with col1:
            sh_wind = st.number_input("Wind", 0, 120, 60, step=5) / 100
        with col2:
            sh_solar = st.number_input("Solar", 0, 120, 20, step=5) / 100
        with col3:
            sh_base = st.number_input("Baseload", 0, 120, 20, step=5) / 100
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
    df_storage, df_storage_stats = get_storage_stats(df_norm)

    # Tab with daily generation
    with tabDaily:
        st.markdown("""## Daily Generation and Demand""")
        st.markdown("""**Overview Imbalances**""")
        st.dataframe(df_storage_stats.T)
        col1, col2 = st.columns([1, 3])
        with col2:
            percent_daily_demand = st.toggle("Show as percent of daily demand")
        with col1:
            days = st.slider("Numbers of days for aggregation", 1, 10, 1)
        fig = plot_daily_generation(
            df_norm, days=days, percent_daily_demand=percent_daily_demand
        )
        st.plotly_chart(fig, use_container_width=True)

    # tab with average profiles
    with tabProfile:
        if st.toggle("Show hourly profiles"):
            profiles = get_profiles(df_norm)
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
