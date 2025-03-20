import time
import logging
import pandas as pd
import tqdm
from scipy.optimize import minimize_scalar
from .utils import get_profiles_shares, get_average_profiles


def calculate_storage_need(
    df_profiles: pd.DataFrame,
    share_renewable: float,
    share_wind: float = 0.5,
    total_demand: float = 100,
) -> pd.DataFrame:
    """Calculate the maximum storage needed for a given share of wind power.

    Args:
        df_profiles (pd.DataFrame): The profiles of the demand, pv, wind, and base load.
        share_renewable (float): The share of renewable energy in total demand
        share_wind (float): The share of wind energy in the renewable energy.
        total_demand (float): The total demand in the system.

    Returns:
        pd.DataFrame: production and storage schedule.
    """
    df = df_profiles.assign(
        demand=lambda df: df["demand"] * total_demand,
        pv=lambda df: df["pv"] * share_renewable * (1 - share_wind) * total_demand,
        wind=lambda df: df["wind"] * share_renewable * share_wind * total_demand,
        base=lambda df: df["base"] * (1 - share_renewable) * total_demand,
        supply=lambda df: df["pv"] + df["wind"] + df["base"],
        netSupply=lambda df: df["supply"] - df["demand"],
        cumSupply=lambda df: df["netSupply"].cumsum(),
        # initial storage level is the minimum of the cumSupply to ensure
        # that net supply is never negative
        initialStorageLevel=lambda df: -df.cumSupply.min(),
        storageLevel=lambda df: df["cumSupply"] + df["initialStorageLevel"],
        MAX_STO=lambda df: df["storageLevel"].max(),
        shareWind=share_wind,
        renewableDemandShare=share_renewable,
    )
    return df.drop(columns=["cumSupply"])


def optimize_storage_need(
    df_profiles: pd.DataFrame, share_renewable: float, total_demand: float = 100
) -> float:
    """Calculate the maximum storage needed for a given share of wind power.

    Args:.
        df_profiles (pd.DataFrame): The profiles of the demand, pv, wind, and base load.
        share_renewable (float): The share of renewable energy in total demand
        total_demand (float): The total demand in the system.

    Returns:
        float: maximum storage need
    """

    def optimize_me(share_wind):
        df = calculate_storage_need(
            df_profiles=df_profiles,
            share_renewable=share_renewable,
            share_wind=share_wind,
            total_demand=total_demand,
        )
        return df["MAX_STO"].iloc[-1]

    # return optimize_me(share_wind=0.5)
    initial_value = 0.5
    bounds = [0, 1]
    result = minimize_scalar(optimize_me, initial_value, args=(), bounds=bounds)
    if not result.success:
        return None
    # compute the final schedule
    df = calculate_storage_need(
        df_profiles=df_profiles,
        share_renewable=share_renewable,
        share_wind=result.x,
        total_demand=total_demand,
    )
    return df


def simulate_storage_need(
    country: str,
    year_re: int,
    year_dem: int,
    share_renewable: float,
    total_demand: float = 100,
    fn_renewable: str = "../data/renewables_ninja.parquet",
    fn_demand: str = "../data/renewables_with_load.parquet",
) -> pd.DataFrame:
    """Simulate storage need for a single country demand and weather year
    optimizing over the share of wind power.

    Args:
        country (str): ISO country code
        year_re (int): year for weather data
        year_dem (int): year for demand data
        share_renewable (float): The share of renewable energy in total demand
        total_demand (float): The total demand in the system.
        fn_renewable (str): path to renewable data
        fn_demand (str): path to demand data

    Returns:
        pd.DataFrame: production and storage schedule.
    """
    # get the profile data
    df_shares = get_profiles_shares(
        country=country,
        year_re=year_re,
        year_dem=year_dem,
        fn_renewable=fn_renewable,
        fn_demand=fn_demand,
    )
    # optimize the storage need
    df_opt = optimize_storage_need(
        df_profiles=df_shares,
        share_renewable=share_renewable,
        total_demand=total_demand,
    )
    if df_opt is None:
        logging.error(
            f"Optimization failed for country {country} and weather year {year_re} and demand year {year_dem}"
        )
        return None
    return df_opt


def simulate_storage_need_by_years(
    countries: list[str],
    shares_renewable: list[float],
    years_re: list[int],
    years_dem: list[int],
    fn_renewable: str = "../data/renewables_ninja.parquet",
    fn_demand: str = "../data/renewables_with_load.parquet",
) -> pd.DataFrame:
    """Simulate storage need for several countries and years optimizing
    over the share of wind power. This version simulates the storage need for
    for each combination of country, share of renewable energy, weather year and
    demand year.

    Args:
        countries (list[str]): list of countries
        shares_renewable (list[float]): list of renewable shares
        years_re (list[int]): years for weather data
        years_dem (list[int]): years for demand data
        fn_renewable (str): path to renewable data
        fn_demand (str): path to demand data

    Returns:
        pd.DataFrame: production and storage schedule.
    """
    tic = time.time()
    all_combis = [
        (c, sr, y1, y2)
        for c in countries
        for sr in shares_renewable
        for y1 in years_re
        for y2 in years_dem
    ]
    lst_df = []
    failed = 0
    for country, share_renewable, year_re, year_dem in tqdm.tqdm(all_combis):
        df_ = simulate_storage_need(
            country=country,
            year_re=year_re,
            year_dem=year_dem,
            share_renewable=share_renewable,
            fn_renewable=fn_renewable,
            fn_demand=fn_demand,
        )
        if df_ is not None:
            lst_df.append(
                df_.assign(
                    country=country,
                    yearWeather=year_re,
                    yearDemand=year_dem,
                    renewableDemandShare=share_renewable,
                )
            )
        else:
            failed += 1
    df_out = pd.concat(lst_df)
    print(f"Solve {len(all_combis)} scenarios in : {time.time() - tic:.2f} seconds.")
    print(f"Failed to solve {failed} of {len(all_combis)} scenarios")
    return df_out


def simulate_storage_need_averaged(
    country: str,
    years: list[int],
    share_renewable: float,
    total_demand: float = 100,
    fn_renewable: str = "../data/renewables_ninja.parquet",
    fn_demand: str = "../data/renewables_with_load.parquet",
) -> pd.DataFrame:
    """Simulate storage need for a country and average weather and demand years optimizing
    over the share of wind power

    Args:
        country (str): ISO country code
        years (list[int]): years for averages
        share_renewable (float): The share of renewable energy in total demand
        total_demand (float): The total demand in the system.
        fn_renewable (str): path to renewable data
        fn_demand (str): path to demand data

    Returns:
        pd.DataFrame: production and storage schedule.
    """
    # get the profile data
    df_shares = get_average_profiles(
        country=country, years=years, fn_renewable=fn_renewable, fn_demand=fn_demand
    )

    # optimize the storage need
    df_opt = optimize_storage_need(
        df_profiles=df_shares,
        share_renewable=share_renewable,
        total_demand=total_demand,
    )
    if df_opt is None:
        logging.error(
            f"Optimization failed for country {country} and average weather and demand year."
        )
        return None
    return df_opt


def simulate_country_averages(
    countries: list[str],
    shares_renewable: list[float],
    years: list[int],
    total_demand: float = 100,
    fn_renewable: str = "../data/renewables_ninja.parquet",
    fn_demand: str = "../data/renewables_with_load.parquet",
) -> pd.DataFrame:
    """Simulate storage need for several countries and years optimizing
    over the share of wind power

    Args:
        countries (list[str]): list of countries
        shares_renewable (list[float]): list of renewable shares
        total_demand (float): The total demand in the system.
        years (list[int]): years for averages
        fn_renewable (str): path to renewable data
        fn_demand (str): path to demand data

    Returns:
        pd.DataFrame: production and storage schedule.
    """
    tic = time.time()
    all_combis = [(c, s) for c in countries for s in shares_renewable]
    failed = 0
    lst_df = []
    for country, share_renewable in tqdm.tqdm(all_combis):
        df_ = simulate_storage_need_averaged(
            country=country,
            years=years,
            share_renewable=share_renewable,
            total_demand=total_demand,
            fn_demand=fn_demand,
            fn_renewable=fn_renewable,
        )
        if df_ is not None:
            df_ = df_.assign(
                country=country,
                yearWeather="average",
                yearDemand="average",
                renewableDemandShare=share_renewable,
            )
            lst_df.append(df_)
        else:
            failed += 1
    df_out = pd.concat(lst_df)
    print(f"Solve {len(all_combis)} scenarios in : {time.time() - tic:.2f} seconds.")
    print(f"Failed to solve {failed} of {len(all_combis)} scenarios")
    return df_out
