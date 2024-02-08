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
def get_hourly_results(
    fn_results: str,
    share_generation: float,
    share_storage: float,
    share_renewable: float,
    curtail_res_first=True,
) -> pd.DataFrame:
    """
    Get hourly results

    Args:
        fn_results: name of file with hourly results
        share_generation: total generation as multiple of demand
        curtail_res_first: indicator whether renewable are curtailed fir
    """
    df = pd.read_parquet(
        fn_results,
        filters=[
            (f"share_generation", "==", share_generation),
            (f"share_storage", "==", share_storage),
            (f"share_renewable", "==", share_renewable),
        ],
    ).assign(
        curtailRenewableFirst=lambda df: df["costCurtailRenewable"]
        <= df["costCurtailNuclear"],
    )
    return df[df["curtailRenewableFirst"] == curtail_res_first]


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
            <= df["costCurtailNuclear"],
        )
        .groupby(idx, as_index=False)[cols]
        .sum()
    )
    # to some rounding in the index columns to avoid mismatches due to
    # precision caused by parquet file inputs
    to_round = ["share_storage", "share_generation", "share_renewable"]
    df_annual.loc[:, to_round] = df_annual.loc[:, to_round].round(8)

    # curtailment in percent of total generation
    df_annual = df_annual.assign(
        curtailNuclearPercent=lambda df: df["curtailNuclear"]
        / (df["nuclear"] + df["curtailNuclear"])
        * 100,
        curtailRenewablePercent=lambda df: df["curtailRenewable"]
        / (df["renewable"] + df["curtailRenewable"])
        * 100,
    )
    return df_annual.fillna(0)


def get_profiles(df: pd.DataFrame) -> dict[str, pd.DataFrame]:
    """Get profile by hour and month

    Args:
        df: dataframe with hourly data
    """
    res = {
        "Hourly: Year": df.groupby(lambda x: x.hour)
        .mean()
        .rename_axis(index={"dateTime": "Hour"}),
        "Monthly": df.groupby(lambda x: x.month)
        .mean()
        .rename_axis(index={"dateTime": "Month"}),
        "Hourly: Spring": df[df.index.month.isin([3, 4, 5])]
        .groupby(lambda x: x.hour)
        .mean()
        .rename_axis(index={"dateTime": "Hour"}),
        "Hourly: Summer": df[df.index.month.isin([6, 7, 8])]
        .groupby(lambda x: x.hour)
        .mean()
        .rename_axis(index={"dateTime": "Hour"}),
        "Hourly: Autumn": df[df.index.month.isin([9, 10, 11])]
        .groupby(lambda x: x.hour)
        .mean()
        .rename_axis(index={"dateTime": "Hour"}),
        "Hourly: Winter": df[df.index.month.isin([1, 2, 12])]
        .groupby(lambda x: x.hour)
        .mean()
        .rename_axis(index={"dateTime": "Hour"}),
    }
    return res


def normalize_generation(
    df: pd.DataFrame,
    shares: dict[str, float],
    total_demand: float = 0,
) -> pd.DataFrame:
    """Normalize data to a given value of annual demand. Generation of
       renewable generation is scaled to meet the given demand share on an
       annual basis. In addition, a baseload technology is added with an
       constant annual profile

    Args:
        df: Dataframe with observed demand and generation data
        shares: shares of each technology in annual demand. keys have to match
            with columns. Exception is "Baseload" that is used to create the
            baseload technology with constant profile
        total_demand: Total demand over the whole time horizon to normalize demand
            If zero, no demand scaling
    """
    if total_demand == 0:
        total_demand = df["Demand"].sum()
    # normalize data
    df_ = (df / df.sum()).assign(Baseload=1 / len(df))
    shares.update({"Demand": 1})
    for tech, fac in shares.items():
        df_[tech] = df_[tech] * total_demand * fac
    return df_[list(shares.keys())]


def normalize_generation(
    df: pd.DataFrame,
    shares: dict[str, float],
    total_demand: float = 0,
) -> pd.DataFrame:
    """Normalize data to a given value of annual demand. Generation of
       renewable generation is scaled to meet the given demand share on an
       annual basis. In addition, a baseload technology is added with an
       constant annual profile

    Args:
        df: Dataframe with observed demand and generation data
        shares: shares of each technology in annual demand. keys have to match
            with columns. Exception is "Baseload" that is used to create the
            baseload technology with constant profile
        total_demand: Total demand over the whole time horizon to normalize demand
            If zero, no demand scaling
    """
    if total_demand == 0:
        total_demand = df["Demand"].sum()
    # normalize data
    df_ = (df / df.sum()).assign(Baseload=1 / len(df))
    shares.update({"Demand": 1})
    for tech, fac in shares.items():
        df_[tech] = df_[tech] * total_demand * fac
    return df_[list(shares.keys())]


@st.cache_data
def get_generation(fn: str, country: str, year: int) -> pd.DataFrame:
    """Get renewable generation and demand by country and year

    Args:
        fn: name of parquet file
        country: 2-letter country code
        year: year for data
    """
    df = (
        pd.read_parquet(
            fn,
            filters=[
                ("country", "==", country),
                ("dateTime", ">=", pd.to_datetime(f"{year}/01/01 00:00")),
                ("dateTime", "<=", pd.to_datetime(f"{year}/12/31 23:00")),
            ],
        )
        .set_index("dateTime")
        .drop("country", axis=1)
    )
    df.columns = [c[:1].capitalize() + c[1:] for c in df.columns]
    df["Wind"] = df["WindOffshore"].fillna(0) + df["WindOnshore"].fillna(0)
    return df


def get_storage_stats(df: pd.DataFrame) -> (pd.DataFrame, pd.DataFrame):
    """Get curtailment and energy overshoot given the frame of generation

    Args:
        df: frame with hourly generation and demand data

    Returns:
        hourly dataframe with storage statistics; aggregated statistics
    """
    col_gen = [c for c in df.columns if c != "Demand"]
    df_ = df.assign(
        TotalSupply=lambda df: df[col_gen].sum(1),
        ExcessSupply=lambda df: df["TotalSupply"] - df["Demand"],
        Curtailment=lambda df: (df["ExcessSupply"] > 0).astype("int")
        * df["ExcessSupply"],
        LostLoad=lambda df: (-1)
        * (df["ExcessSupply"] < 0).astype("int")
        * df["ExcessSupply"],
    )
    total = df_.sum()
    stats = {
        var: {
            "Total": total[var],
            "TotalPercentOfDemand": total[var] / total["Demand"] * 100,
            "Max": df_[var].max(),
            # "MaxPercent": df_.loc[df_[var].idxmax(), var]/df_.loc[df_[var].idxmax(), "Demand"]*100,
            "Hours": len(df_[df_[var] > 9]),
        }
        for var in ["Curtailment", "LostLoad"]
    }
    return df_, pd.DataFrame.from_dict(stats).round(1)
