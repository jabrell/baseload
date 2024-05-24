import logging
import pandas as pd


def get_data_by_years(
    country: str,
    year_re: int,
    year_dem: int,
    fn_renewable: str,
    fn_demand: str,
    base_year: int = 2023,
) -> pd.DataFrame:
    """Get wind and solar generation data together with demand for a given year
    and country. For leap years the leap day is dropped. Missing values are
    forward filled. Data are aligned to a common time index for the given base year.

    Args:
        country (str): ISO country code
        year_re (int): year of renewable data
        year_dem (int): year of demand data
        fn_renewable (str): path to renewable data
        fn_demand (str): path to demand data
        base_year (int): year to which the data is aligned

    Returns:
        dataframe with hourly time index and columns for solar, wind and demand
    """
    df_re = pd.read_parquet(
        fn_renewable,
        filters=[
            ("country", "==", country),
            ("time", ">=", pd.to_datetime(f"{year_re}-01-01")),
            ("time", "<", pd.to_datetime(f"{year_re+1}-01-01")),
        ],
    ).pivot_table(index="time", columns="resource", values="total")
    df_dem = pd.read_parquet(
        fn_demand,
        filters=[
            ("country", "==", country),
            ("dateTime", ">=", pd.to_datetime(f"{year_dem}-01-01")),
            ("dateTime", "<", pd.to_datetime(f"{year_dem+1}-01-01")),
        ],
    ).set_index("dateTime")[["demand"]]

    # ensure that we have a complete time series with all hours
    df_re = df_re.reindex(
        pd.date_range(df_re.index.min(), df_re.index.max(), freq="H")
    ).sort_index()
    if df_re.isna().sum().sum() > 0:
        logging.info(
            f"Missing values in renewable data for {country} in {year_re}. Filled by forward filling: {df_re.isna().sum().to_string()}"
        )
        df_re = df_re.ffill()
    df_dem = df_dem.reindex(
        pd.date_range(df_dem.index.min(), df_dem.index.max(), freq="H")
    ).sort_index()
    if df_dem.isna().sum().sum() > 0:
        logging.info(
            f"Missing values in demand data for {country} in {year_dem}. Filled by forward filling: {df_dem.isna().sum().to_string()}"
        )
        df_dem = df_dem.ffill()

    # drop leap days
    if len(df_re) > 8760:
        df_re = df_re[
            df_re.index.date != pd.to_datetime(f"{year_re}-02-29").date()
        ].copy()
    if len(df_dem) > 8760:
        df_dem = df_dem[
            df_dem.index.date != pd.to_datetime(f"{year_dem}-02-29").date()
        ].copy()

    # create a common time index
    base_year = 2023
    t_index = pd.date_range(f"{base_year}-01-01", freq="H", periods=8760)
    df_re.index = t_index
    df_dem.index = t_index
    df = df_re.join(df_dem, how="outer")
    assert (
        len(df) == 8760
    ), "Something went wrong, we should have 8760 hours in the year"

    return df


def get_profiles_shares(
    country: str,
    year_re: int,
    year_dem: int,
    fn_renewable: str,
    fn_demand: str,
    label_base: str = "base",
    base_year: int = 2023,
) -> pd.DataFrame:
    """Get wind and solar generation data together with demand and convert
    them to shares of annual totals. For the base technology the share is
    set to 1/8760.

    Args:
        country (str): ISO country code
        year_re (int): year of renewable data
        year_dem (int): year of demand data
        fn_renewable (str): path to renewable data
        fn_demand (str): path to demand data
        label_base (str): label for base technology
        base_year (int): year to which the data is aligned

    Returns:
        dataframe with hourly time index and columns for solar, wind and demand
        containing the share of yearly totals for the 8760 hours in the years
    """
    # convert to shares of yearly totals
    df = get_data_by_years(
        country=country,
        year_re=year_re,
        year_dem=year_dem,
        fn_renewable=fn_renewable,
        fn_demand=fn_demand,
        base_year=base_year,
    )
    df = df.div(df.sum()).assign(**{label_base: lambda df: 1 / len(df)})
    return df
