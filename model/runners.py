import os
import time
import pandas as pd
import numpy as np

from model.simulation_min_storage import simulate_min_storage
from model.utils import get_entsoe_data


def run_entsoe_countries(
    countries: list[str] | None = None,
    dates: list[tuple[str]] | None = None,
    shares_renewable: list[float] | None = None,
    gamsopt: dict[str, str] | None = None,
    fn_out: str | None = None,
    label_base: str = "base",
    fn_entsoe: str = "./data/entsoe_data.parquet",
    store_single_country: bool = False,
):
    """Run scenarios based on the entsoe scenarios. Its just a wrapper around
    simulate_min_storage_by_country that sets the default values for the simulations

    Args:
        countries: list of countries
        dates: list of start and end dates
        shares_renewable: list of shares of renewable generation
        gamsopt: dictionary with options for GAMS model
        fn_out: name of output file
        label_base: label for base scenario
        fn_entsoe: name of input file with data
        store_single_country: if True, store results for each country separately
    """
    if countries is None:
        countries = [
            "DE",
            "AT",
            "BE",
            "BG",
            "HR",
            "CZ",
            "DK",
            "EE",
            "ES",
            "FI",
            "FR",
            "LT",
            "LU",
            "HU",
            "NL",
            "IT",
            "GR",
            "PL",
            "PT",
            "RO",
            # countries with no or likelyng solar data
            "NO",
            "SE",
            "LV",
        ]
    if dates is None:
        dates = [
            # ("2017/06/01 00:00", "2018/05/31 23:00"),
            ("2023/01/01 00:00", "2023/12/31 23:00"),
        ]
    if shares_renewable is None:
        shares_renewable = np.arange(0, 1.0001, 0.01)

    df = simulate_min_storage_by_country(
        countries=countries,
        dates=dates,
        shares_renewable=shares_renewable,
        fn_out=fn_out,
        gamsopt=gamsopt,
        label_base=label_base,
        fn_entsoe=fn_entsoe,
        store_single_country=store_single_country,
    )
    return df


def simulate_min_storage_by_country(
    countries: list[str],
    dates: list[tuple[str]],
    shares_renewable: list[float],
    fn_entsoe: str,
    label_base: str,
    fn_out: str | None = None,
    gamsopt: dict[str, str] | None = None,
    store_single_country: bool = False,
) -> pd.DataFrame:
    """Simulate the minimum storage model for different countries and time
    periods. This is based on the original ENTSOE data.

    Args:
        countries: list of countries
        dates: list of start and end dates
        shares_renewable: list of shares of renewable generation
        fn_entsoe: name of input file with data
        label_base: label for base scenario
        fn_out: name of output file
        gamsopt: dictionary with options for GAMS model
        store_single_country: if True, store results for each country separately
    """
    if store_single_country:
        base_path = os.path.dirname(fn_out)
    lst_df = []
    for start, end in dates:
        lst_country = []
        for country in countries:
            print(f"-------- Simulate for {country} from {start} to {end}")
            df_entsoe = get_entsoe_data(country, start=start, end=end, fn=fn_entsoe)
            # todo generalize the mapping
            tech_wind = ["windOnshore", "windOffshore"]
            df_entsoe["wind"] = df_entsoe[tech_wind].sum(1)
            df_entsoe = df_entsoe.drop(tech_wind, axis=1)

            df = simulate_min_storage(
                df_entsoe,
                shares_renewable=shares_renewable,
                renewables=["wind", "solar"],
                label_base=label_base,
                gamsopt=gamsopt,
            )
            lst_country.append(
                df.assign(
                    country=country,
                    start=str(start),
                    end=str(end),
                )
            )
            if store_single_country:
                fn_out_country = os.path.join(
                    base_path,
                    f"{country}_{start.replace('/', '-').replace(':', '-')}.parquet",
                )
                df.assign(
                    country=country,
                    start=str(start),
                    end=str(end),
                ).to_parquet(fn_out_country)
        lst_df.append(pd.concat(lst_country))
    df = pd.concat(lst_df)
    if fn_out is not None:
        df.to_parquet(fn_out)
    return df
