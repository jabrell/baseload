import streamlit as st
from .data import (
    get_storage_scenario_options,
    get_storage_results,
    calculate_cost_storage_scenarios,
)
from .graphs import plot_cost_storage_scenarios, plot_storage_results
import os


def dashboard_minStorage(fn_results: str = None):
    """Run the dashboard
    Args:
        fn_results: path to file with results
    """
    # st.set_page_config(layout="wide")
    st.title("Simulations for Baseload Paper")
    scen_options = get_storage_scenario_options(fn_results)

    with st.sidebar:
        st.subheader("Choose specification for base data")
        # select for country and start date
        country = st.selectbox("Country", scen_options["countries"])
        start = st.selectbox(
            "Start date",
            scen_options["start"],
            help="Start date for the simulation. Simulation includes 8760 hours.",
        )
        st.divider()
        st.subheader("Set cost options")
        cost_res = st.number_input(
            "Cost of installing renewable",
            value=1.0,
            help="The cost of installing capacity that provides the potential to proved 1 MWh over the whole time horizon [CHF/MWh]",
            step=1.0,
            format="%.1f",
        )
        cost_base = st.number_input(
            "Cost of installing baseload",
            value=3.0,
            help="The cost of installing capacity that provides the potential to proved 1 MWh over the whole time horizon [CHF/MWh]",
            step=1.0,
            format="%.1f",
        )
        cost_sto = st.number_input(
            "Cost of installing storage",
            value=10.0,
            help="The cost of installing a facility that allows to store a maximum amount of 1 MWh [CHF/MWh]",
            step=1.0,
            format="%.1f",
        )
        cost = {
            "wind": cost_res,
            "solar": cost_res,
            "base": cost_base,
            "storage": cost_sto,
        }

    # get the storage results and associated cost
    df = get_storage_results(fn_results, country, start)
    df = df.merge(
        calculate_cost_storage_scenarios(df, cost), on=["scenario", "share_renewable"]
    )
    fig = plot_cost_storage_scenarios(df)
    st.plotly_chart(fig, use_container_width=True)
    scenario = st.selectbox(
        "Scenario",
        df["scenario"].unique(),
        help="There are two scenarios. Both minimize storage. The optimalRE scenarios additionally optimizes the share of different renewable technologies",
    )
    fig = plot_storage_results(df)
    st.plotly_chart(fig, use_container_width=True)
