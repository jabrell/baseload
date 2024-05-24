# This is the model version that we used to create the model runs after the
# Mannheim workshop.
import sys
import logging
from typing import Any
import time
import tqdm
import pandas as pd
import numpy as np
from model_no_gams.model import (
    get_profiles_shares,
    solve_model,
    get_data_by_years,
)


def simulate_demand_and_weather_years(
    countries: list[str],
    shares_renewable: list[float],
    years_re: list[int],
    years_dem: list[int],
    fn_renewable: str = "./data/renewables_ninja.parquet",
    fn_demand: str = "./data/renewables_with_load.parquet",
    gamsopt: dict[str, str] = {},
    output_stream: Any = sys.stdout,
) -> pd.DataFrame:
    """Simulate all combinations of countries, renewable years and demand years.

    Args:
        countries (list[str]): list of countries
        shares_renewable (list[float]): list of shares of renewable generation
            in total demand
        years_re (list[int]): list of years for renewable data
        years_dem (list[int]): list of years for demand data
        fn_renewable (str): file name with renewable data
        fn_demand (str): file name with demand data
        gamsopt (dict[str, str]): options for GAMS model
        output_stream (Any): output stream for GAMS model

    Returns:
        pd.DataFrame: results of all simulations
    """
    lst_df = []
    all_combis = [
        (c, sr, y1, y2)
        for c in countries
        for sr in shares_renewable
        for y1 in years_re
        for y2 in years_dem
    ]
    for country, share_renewable, year_re, year_dem in tqdm.tqdm(all_combis):
        logging.info(
            f"Simulate for country {country}, weather year {year_re} and demand year {year_dem}"
        )
        df = get_profiles_shares(country, year_re, year_dem, fn_renewable, fn_demand)
        try:
            df_sol = solve_model(
                df,
                share_renewable=share_renewable,
                optimize_res_share=True,
                output_stream=output_stream,
                gamsopt=gamsopt,
            )
        except ValueError:
            logging.warning(
                f"Model did not solve for {country} with renewable year {year_re} and demand year {year_dem}"
            )
        if df_sol is not None:
            df_sol = df_sol.assign(
                country=country,
                yearWeather=year_re,
                yearDemand=year_dem,
                renewableDemandShare=share_renewable,
            )
            lst_df.append(df_sol)
    return pd.concat(lst_df)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)

    fn_demand = "./data/renewables_with_load.parquet"
    fn_renewable = "./data/renewables_ninja.parquet"

    # we have weather years form 1980 to 2019
    # and demand years from 2015 to 2020
    years_re = range(1980, 2020)
    years_dem = range(2015, 2024)
    countries = ["DE", "FR", "GR"]
    steps = 10
    shares_renewable = list(np.linspace(0, 1, steps + 1))

    # gams options
    output_stream = sys.stdout
    countries = ["DE"]
    years_re = [2019]
    years_dem = [2019]
    shares_renewable = [0.5]
    t1 = time.time()
    df_out = simulate_demand_and_weather_years(
        countries=countries,
        shares_renewable=shares_renewable,
        years_re=years_re,
        years_dem=years_dem,
        output_stream=output_stream,
    )
    print(f"Elapsed time: {((time.time() - t1)/60):.2f} minutes")
    # df_out.to_parquet("./results/results_weather_years.parquet")
    print("Done!")
