from dashboard import dashboard_minStorage
from dashboard.data import get_storage_results


if __name__ == "__main__":

    fn_results = "./data/results_storage.parquet"
    fn_results = (
        "https://jabspublicbucket.s3.eu-central-1.amazonaws.com/results_storage.parquet"
    )
    fn_results = "s3://jabspublicbucket/results_st"
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
    settings = {"countries": ALL_COUNTRIES, "start": ["2023/01/01 00:00"]}
    country = "DE"
    start = "2023/01/01 00:00"
    storage_options = None
    # get_storage_results(fn_results, country, start, storage_options=storage_options)
    dashboard_minStorage(fn_results, settings, storage_options)
