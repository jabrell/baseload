from dashboard import dashboard_minStorage


if __name__ == "__main__":
    fn_results = "./data/results_storage.parquet"
    fn_results = (
        "https://jabspublicbucket.s3.eu-central-1.amazonaws.com/results_storage.parquet"
    )
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
    settings = {"countries": ALL_COUNTRIES, "start": "2023/01/01 00:00"}
    dashboard_minStorage(fn_results, settings)
    # fn_gen = "./data/renewables_with_load.parquet"
    # fn_cap = "./data/renewables_capacity.parquet"
    # profile_dashboard(fn_gen, fn_cap)
