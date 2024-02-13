import streamlit as st
from .data import get_profiles
from .graphs import plot_profile, plot_daily_generation
from .components import sidebar


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


def profile_dashboard(fn_gen: str, fn_cap: str):
    """Run the dashboard based on profiles

    Args:
        fn_gen: path to file with generation data
        fn_cap: path to file with capacity data
    """
    # settings for contents and graphs
    tech_order = ["Baseload", "Wind", "Solar"]
    colors = {"Demand": "Red", "Wind": "Green", "Solar": "Orange", "Baseload": "Black"}

    # layout settings
    st.set_page_config(
        page_title="Baseload Paper",
        layout="wide",
    )

    # sidebar
    df_hourly, df_stats = sidebar(fn_gen=fn_gen, fn_cap=fn_cap)

    # create the different tabs
    tabDaily, tabProfile = st.tabs(["Daily Generation", "Profiles"])

    # Tab with daily generation
    with tabDaily:
        st.markdown("""## Daily Generation and Demand""")
        st.markdown("""**Overview Imbalances**""")
        st.dataframe(df_stats.T)
        col1, col2 = st.columns([1, 3])
        with col2:
            percent_daily_demand = st.toggle("Show as percent of daily demand")
        with col1:
            days = st.slider("Numbers of days for aggregation", 1, 10, 1)
        fig = plot_daily_generation(
            df_hourly,
            days=days,
            percent_daily_demand=percent_daily_demand,
            colors=colors,
            tech_order=tech_order,
        )
        st.plotly_chart(fig, use_container_width=True)

    # tab with average profiles
    with tabProfile:
        if st.toggle("Show hourly profiles"):
            profiles = get_profiles(df_hourly)
            all_profiles = [
                "Hourly: Year",
                "Monthly",
                "Hourly: Winter",
                "Hourly: Spring",
                "Hourly: Summer",
                "Hourly: Autumn",
            ]
            profile_order = (
                tech_order
                if st.toggle(
                    "Stack profiles",
                    value=True,
                    help="If activated graphs shows the sum of hourly mean production over all technologies, i.e., technologies are stacked one on the next one.",
                )
                else None
            )
            if profile_order is not None:
                st.markdown(f"Order of technologies: {'-'.join(profile_order)}")
            cells = [x for xs in make_grid(3, 2) for x in xs]
            for i, profile in enumerate(all_profiles):
                fig = plot_profile(
                    profiles[profile],
                    colors=colors,
                    title=profile,
                    tech_order=profile_order,
                )
                with cells[i]:
                    st.plotly_chart(fig, use_container_width=True)
