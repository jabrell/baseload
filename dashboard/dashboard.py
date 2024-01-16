import streamlit as st
from .queries import get_data


def get_data(
    fn,
    share_generation: float,
    share_renewable: float,
    share_storage: float,
):
    """Get data for"""


def dashboard(fn_results: str):
    """Run the dashboard
    Args:
        fn_results: path to file with results
    """
    st.title("Simulations for the Baseload Paper")
