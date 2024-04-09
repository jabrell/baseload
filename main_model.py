import os
import time
import sys
from typing import Any

import numpy as np
import pandas as pd

from model import (
    simulate_min_storage_by_country,
    run_entsoe_countries,
    simulate_min_storage,
)


def run_artificial_counties(
    fn_data: str,
    gamsopt: dict[str, str] | None = None,
    output: Any | None = None,
    label_base: str = "base",
    use_historic_reshares: bool = False,
    fn_out: str | None = None,
):
    """Run scenarios for artificial countries

    Args:
        fn_data: name of input file with data
        gamsopt: dictionary with options for GAMS model
        label_base: label for base scenario
        output: destination of gams output stream
        use_historic_reshares: if True will use the historic share of wind and
            solar generation for the scenario without optimizing over the shares
            By default a 50% %50 share is used.
        fn_out: name of output file
    """
    df_in = pd.read_parquet(fn_data)
    shares_renewable = np.arange(0, 1.0001, 0.01)
    label_base = "base"
    countries = df_in["country"].unique()
    start = df_in["dateTime"].min()
    end = df_in["dateTime"].max()

    # convert capacity factors to generation
    lst_df = []
    for country in countries:
        print("-------- Simulate for", country)
        df_ = df_in.query(f"country == '{country}'").drop(columns="country")
        if use_historic_reshares:
            shares_renewable_technologies = (
                df_[["wind_share", "solar_share"]]
                .rename(columns={"wind_share": "wind", "solar_share": "solar"})
                .iloc[0]
                .to_dict()
            )
        else:
            # take an artificial 50% 50% share for wind and solar
            shares_renewable_technologies = {"wind": 0.5, "solar": 0.5}
        data = df_.drop(columns=["wind_share", "solar_share"])

        lst_df.append(
            simulate_min_storage(
                data=data,
                shares_renewable=shares_renewable,
                share_renewable_technologies=shares_renewable_technologies,
                renewables=["wind", "solar"],
                label_base=label_base,
                gamsopt=gamsopt,
                output=output,
            ).assign(
                country=country,
                start=str(start),
                end=str(end),
            )
        )
    df = pd.concat(lst_df)
    if fn_out is not None:
        df.to_parquet(fn_out)
    print("here")
    return df


if __name__ == "__main__":
    # fn_results = "s3://jabspublicbucket/results_artificial"
    # df = get_storage_results(
    #     fn_results, country="mildSummerPeakES_north", start="2023-01-01 00:00:00"
    # )
    # print("here")
    # sys.exit()

    # some code to upload results partioned to s3
    # fn_s3 = "s3://jabspublicbucket/results_st"
    # ]
    # df = pd.read_parquet(fn)
    # df.to_parquet(fn_s3, partition_cols=partition_cols)
    # C:/Users/abrel/Documents/
    # \\wwz-jumbo.storage.p.unibas.ch\wwz-home01$\abrell\GAMS
    gamsopt = {
        "license": "//wwz-jumbo.storage.p.unibas.ch/wwz-home01$/abrell/GAMS/gamslice_basel.txt"
    }
    tic = time.time()
    df = run_artificial_counties(
        fn_data="./data/artificial_countries.parquet",
        gamsopt=gamsopt,
        # output=sys.stdout,
        fn_out="./data/results_artificial.parquet",
    )
    partition_cols = ["country"]
    df.to_parquet(
        "s3://jabspublicbucket/results_artificial_neu", partition_cols=partition_cols
    )

    # to run the scenarios based on entsoe data
    # run_entsoe_countries(gamsopt=gamsopt)
    toc = time.time()
    print(f"Time taken: {(toc - tic)/60} minutes")
    print("Finished!")


# legacy code
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
