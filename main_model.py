import os
import time
import numpy as np
import pandas as pd
from model import simulate_min_storage, get_entsoe_data

ALL_COUNTRIES = [
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
    periods.

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


if __name__ == "__main__":
    tic = time.time()
    countries = ALL_COUNTRIES
    dates = [
        # ("2017/06/01 00:00", "2018/05/31 23:00"),
        ("2023/01/01 00:00", "2023/12/31 23:00"),
    ]
    df = simulate_min_storage_by_country(
        countries=countries,
        dates=dates,
        shares_renewable=np.arange(0, 1.0001, 0.01),
        fn_out="./data/results_storage.parquet",
        # C:/Users/abrel/Documents/
        gamsopt={"license": "Z:/GAMS/gamslice_basel.txt"},
        label_base="base",
        fn_entsoe="./data/renewables_with_load.parquet",
        store_single_country=True,
    )
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
