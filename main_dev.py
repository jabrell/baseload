import pandas as pd
from dashboard.data import (
    get_storage_results,
    calculate_cost_storage_scenarios,
)

if __name__ == "__main__":
    fn_results = "s3://jabspublicbucket/results_artificial_neu"
    ALL_COUNTRIES = [
        "mildSummerPeakES_central",
        "mildSummerPeakES_north",
        "mildSummerPeakES_south",
        "mildWinterPeakDE_central",
        "mildWinterPeakDE_north",
        "mildWinterPeakDE_south",
        "strongSummerPeakGR_central",
        "strongSummerPeakGR_north",
        "strongSummerPeakGR_south",
        "strongWinterPeakFR_central",
        "strongWinterPeakFR_north",
        "strongWinterPeakFR_south",
    ]
    settings = {
        "countries": ALL_COUNTRIES,
        "default_start": "2023-01-01 00:00:00",
        "default_country": "mildWinterPeakDE_central",
    }

    c = "mildWinterPeakDE_central"
    lst_df = []
    for c in ALL_COUNTRIES:
        df = (
            get_storage_results(
                fn_results, country=c, start="2023-01-01 00:00:00", storage_options=None
            )[["scenario", "share_renewable", "MAX_STO"]]
            .drop_duplicates()
            .assign(country=c)
        )
        lst_df.append(df)
    df = pd.concat(lst_df)
    df.to_excel("./data/storage_results.xlsx", index=False)
    print("here")
