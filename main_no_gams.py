import numpy as np
import pandas as pd
from model_no_gams import simulate_storage_need_by_years


def run_all_combinations(
    countries: list[str] = ["DE", "FR", "GR"],
    fn_out: str = "./results/results_no_gams.parquet",
    fn_renewable="./data/renewables_ninja.parquet",
    fn_demand="./data/renewables_with_load.parquet",
) -> pd.DataFrame:
    """Run model for all weather and demand year combinations

    Args:
        countries (list[str], optional): List of countries to run the model for. Defaults to ["DE", "FR", "GR"].
        fn_out (str, optional): File to save the results to. Defaults to "./results/results_no_gams.parquet".
        fn_renewable (str, optional): File with renewable data. Defaults to "./data/renewables_ninja.parquet".
        fn_demand (str, optional): File with demand data. Defaults to "./data/renewables_with_load.parquet".

    Returns:
        pd.DataFrame: Results for all model runs
    """
    fn_renewable = "./data/renewables_ninja.parquet"
    fn_demand = "./data/renewables_with_load.parquet"
    years_re = range(1980, 2020)
    years_dem = range(2015, 2024)
    steps = 10
    shares_renewable = list(np.linspace(0, 1, steps + 1))

    df_out = simulate_storage_need_by_years(
        countries=countries,
        shares_renewable=shares_renewable,
        years_re=years_re,
        years_dem=years_dem,
        fn_renewable=fn_renewable,
        fn_demand=fn_demand,
    )
    if fn_out is not None:
        df_out.to_parquet(fn_out)


if __name__ == "__main__":
    fn_renewable = "./data/renewables_ninja.parquet"
    fn_demand = "./data/renewables_with_load.parquet"
    run_all_combinations()
