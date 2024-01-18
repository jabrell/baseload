import streamlit as st
from .data import get_total_results, download_data
from .graphs import get_plot_variable, plot_heatmap
import os


def dashboard(fn_results: str = None):
    """Run the dashboard
    Args:
        fn_results: path to file with results
    """
    st.title("Simulations for the Baseload Paper")
    with st.sidebar:
        st.subheader("Set cost inputs")
        curtail_res_first = st.toggle(
            "Curtail renewable first",
            value=True,
            help="If activated, renewable generation is curtailed before nuclear resource",
        )
        cost_res = st.number_input(
            "Cost of installing renewable",
            value=2.0,
            help="The cost of installing capacity that provides the potential to proved 1 MWh over the whole time horizon [CHF/MWh]",
            step=1.0,
            format="%.1f",
        )
        cost_nuc = st.number_input(
            "Cost of installing nuclear",
            value=1.0,
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
        cost_ens = st.number_input(
            "Cost of energy-not-served",
            value=10.0,
            help="The cost of 1 MWh of energy-not-served [CHF/MWh]",
            step=1.0,
            format="%.1f",
        )
        st.divider()
        st.subheader("Update the local input file")
        url = st.text_input("URL of input file")
        if st.button("Update input file"):
            success = False
            if url != "" and url is not None:
                success = download_data(url, fn_out=fn_results)
                if success:
                    st.write("Updated input file")

    if os.path.isfile(fn_results):
        df_annual = get_total_results(fn_results)
        share_generation = st.select_slider(
            "Generation as multiple of demand",
            df_annual["share_generation"].round(3).unique(),
            help="Multiplier used to determine the amount of potential generation as multiple of demand. A value of 1 means that total potential generation equals total demand over the whole time horizon.",
        )
        variable = st.selectbox(
            "Variable to plot",
            ("cost", "energyNotServed", "curtailRenewable", "curtailNuclear"),
        )
        df_cost = get_plot_variable(
            df_annual=df_annual,
            cost_res=cost_res,
            cost_nuc=cost_nuc,
            cost_sto=cost_sto,
            cost_ens=cost_ens,
            share_generation=share_generation,
            curtail_res_first=curtail_res_first
        )
        fig = plot_heatmap(df_plot=df_cost, variable=variable)
        st.plotly_chart(fig, use_container_width=True)
        st.dataframe(df_cost.set_index(["share_renewable", "share_storage"]))
    else:
        st.write("No input data found. Upload new data.")
