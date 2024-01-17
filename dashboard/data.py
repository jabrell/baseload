import pandas as pd
import requests
import os
import streamlit as st


def download_data(url, fn_out):
    """Download a new data set from url and store it to
    the data directors

    Args:
        url: url of file to download
        fn_out: Output file name
    """
    # get the dropbox file
    url_ = url.strip()
    headers = {"user-agent": "Wget/1.16 (linux-gnu)"}  # <-- the key is here!
    response = requests.get(url_, stream=True, headers=headers)
    response.raise_for_status()

    # delete local file if exist
    try:
        os.remove(fn_out)
    except OSError:
        pass

    # write file to disk
    with open(fn_out, "wb") as f:
        for chunk in response.iter_content(chunk_size=1024):
            if chunk:
                f.write(chunk)
    return True


@st.cache_data
def get_total_results(fn_results: str) -> pd.DataFrame:
    """Get results aggregate over all periods

    Args:
        fn_results: name of file with hourly results
    """
    # settings for aggregation
    cols = [
        "nuclear",
        "renewable",
        "netStorage",
        "demand",
        "energyNotServed",
        "curtailNuclear",
        "curtailRenewable",
    ]
    idx = [
        "share_storage",
        "share_generation",
        "share_renewable",
        "curtailRenewableFirst",
    ]
    # get results, add indicator which technology is dispatched first, and aggregate
    df_annual = (
        pd.read_parquet(fn_results)
        .assign(
            curtailRenewableFirst=lambda df: df["costCurtailRenewable"]
            >= df["costCurtailNuclear"]
        )
        .groupby(idx, as_index=False)[cols]
        .sum()
    )
    return df_annual
