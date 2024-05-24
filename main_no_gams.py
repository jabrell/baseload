import numpy as np
from model_no_gams import simulate_storage_need_by_years

if __name__ == "__main__":
    fn_renewable = "./data/renewables_ninja.parquet"
    fn_demand = "./data/renewables_with_load.parquet"

    countries = ["DE", "FR", "GR"]
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
    df_out.to_parquet("./results/results_no_gams.parquet")
