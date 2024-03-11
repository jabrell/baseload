from model import simulate_min_dispatchable, simulate_min_storage, get_entsoe_data
import time
import numpy as np
import pandas as pd
import sys

from model.gams_model import GamsModel
from model.simulation import extract_solution_storage


if __name__ == "__main__":
    tic = time.time()
    country = "DE"
    start = "2017/06/01 00:00"
    end = "2018/05/31 23:00"
    fn_entsoe = "./data/renewables_with_load.parquet"
    # df_gen, df_profiles = get_entsoe_data(
    #     country=country, start=start, end=end, fn=fn_entsoe
    # )
    df_entsoe = get_entsoe_data(
        "DE", start="2017/06/01 00:00", end="2018/05/31 23:00", fn=fn_entsoe
    )
    # todo: add step to create renewables and add possibility to optimize over this share
    renewables = ["windOnshore", "windOffshore", "solar"]
    df_entsoe["renewable"] = df_entsoe[renewables].sum(1)
    df = simulate_min_storage(
        df_entsoe,
        shares_renewable=np.arange(0, 1, 0.01),
        fn_out="./data/results_storage.parquet",
    )

    # former scenarios that minimize the amount of the dispatchable generation
    # df = simulate_min_dispatchable(
    #     share_generation=np.arange(1, 1.25, 0.05),
    #     share_renewable=np.arange(0, 1.1, 0.1),
    #     share_storage=np.arange(0, 0.00011, 0.00001),
    #     cost_curtailment=[
    #         {"nuclear": 1, "renewable": 0},
    #         {"nuclear": 0, "renewable": 1},
    #     ],
    #     total_demand=100,
    #     fn_out="./data/results.parquet",
    #     country="DE",
    #     start="2017/06/01 00:00",
    #     end="2018/05/31 23:00",
    # )
    toc = time.time()
    print(f"Time taken: {(toc - tic)/60} minutes")
    print("Finished!")
