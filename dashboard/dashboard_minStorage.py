import streamlit as st
from .data import (
    get_storage_scenario_options,
    get_storage_results,
    calculate_cost_storage_scenarios,
)
from .graphs import (
    plot_cost_storage_scenarios,
    plot_storage_results,
    plot_storage_level,
    plot_renewable_shares,
)
import os


def dashboard_minStorage(fn_results: str = None):
    """Run the dashboard
    Args:
        fn_results: path to file with results
    """
    st.set_page_config(layout="wide")
    scen_options = get_storage_scenario_options(fn_results)
    with st.sidebar:
        st.subheader("Choose specification for base data")
        # select for country and start date
        country = st.selectbox(
            "Country",
            scen_options["countries"],
            index=scen_options["countries"].index("DE"),
        )
        start = st.selectbox(
            "Start date",
            scen_options["start"],
            help="Start date for the simulation. Simulation includes 8760 hours.",
        )

    st.title("Simulations for Baseload Paper")
    st.markdown(
        """In all scenarios the maximum storage amount is minimized such that demand
        is met. Total available generation equals total demand and comes in two form."""
    )
    st.markdown(
        """1. Baseload: Generation that is available at all times, i.e., has a flat production profile."""
    )

    st.markdown(
        """2. Renewable: Generation that is available at times when the renewable resource is available.
                The renewable profile is derived from the observed data and combines (on- and offshore) wind with
                solar generation."""
    )
    st.markdown(
        """The share of renewable generation in total available generation is exogenously given
                and varies in steps of 1% along the x axis."""
    )
    st.markdown(
        """In the *storageOnly* scenarios, the share of wind and solar power is exogenously 
                set to the share observed in the data. In the *optimalRE* (also RE portfolio) scenario, 
                this share is optimally chosen."""
    )

    if country == "SE":
        st.markdown(
            """**Note**: The solar data for Sweden look somewhat suspicious in the sense that first half of 
                    the year generation is zero but then shows a massive increase."""
        )
    elif country in ["NO", "LV"]:
        st.markdown(
            f"""**Note**: No solar reported for {country}. So the share between wind and solar cannot be optimized."""
        )

    df = get_storage_results(fn_results, country, start)

    with st.expander("**Cost Results**", expanded=True):
        col1, col2, col3 = st.columns(3)
        cost_res = col1.number_input(
            "Cost of installing renewable",
            value=1.0,
            help="The cost of installing capacity that provides the potential to proved 1 MWh over the whole time horizon [CHF/MWh]",
            step=1.0,
            format="%.1f",
        )
        cost_base = col2.number_input(
            "Cost of installing baseload",
            value=3.0,
            help="The cost of installing capacity that provides the potential to proved 1 MWh over the whole time horizon [CHF/MWh]",
            step=1.0,
            format="%.1f",
        )
        cost_sto = col3.number_input(
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
        df_w_cost = df.merge(
            calculate_cost_storage_scenarios(df, cost),
            on=["scenario", "share_renewable"],
        )
        st.plotly_chart(
            plot_cost_storage_scenarios(df_w_cost), use_container_width=True
        )

    with st.expander("**Storage Usage**", expanded=False):
        scenario = st.selectbox(
            "Scenario",
            df["scenario"].unique(),
            help="There are two scenarios. Both minimize storage. The optimalRE scenarios additionally optimizes the share of different renewable technologies",
        )

        fig = plot_storage_results(df, scenario=scenario)
        st.plotly_chart(fig, use_container_width=True)

        col1, col2 = st.columns(2)
        re_level = round(
            col1.slider(
                "Share of renewable generation",
                min_value=0,
                max_value=100,
                value=30,
                step=1,
            )
            / 100,
            2,
        )
        time_dimension = col2.selectbox(
            "Time steps",
            options=[
                "day",
                "week",
                "month",
            ],
            index=1,
        )

        fig2 = plot_storage_level(
            df, scenario=scenario, re_level=re_level, by=time_dimension
        )
        st.plotly_chart(fig2, use_container_width=True)

    with st.expander("**Renewable Shares**", expanded=False):
        show_observed = st.checkbox("Show observed shares", value=True)

        st.plotly_chart(
            plot_renewable_shares(df, add_observed=show_observed),
            use_container_width=True,
        )
