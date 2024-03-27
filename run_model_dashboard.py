from dashboard import dashboard_minStorage
from dashboard.data import get_storage_results


def run_country_dashboard(
    fn_results: str,
    storage_options: dict | None = None,
):
    """Run the dashboard with the results of real countries

    Args:
        fn_results: name of file with results
        country: country code
        start: start date
        storage_options: dictionary with options for the dashboard
    """
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
    settings = {
        "countries": ALL_COUNTRIES,
        "start": ["2023/01/01 00:00"],
        "default_country": "DE",
    }
    dashboard_minStorage(fn_results, settings, storage_options)


def run_artificial_country_dashboard(
    fn_results: str,
    storage_options: dict | None = None,
):
    """Run the dashboard with the results of artificial countries

    Args:
        fn_results: name of file with results
        storage_options: dictionary with options for the dashboard
    """
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
    dashboard_minStorage(fn_results, settings, storage_options)


if __name__ == "__main__":
    run_artificial_country_dashboard(
        fn_results="s3://jabspublicbucket/results_artificial"
    )
    # run_country_dashboard(fn_results="s3://jabspublicbucket/results_st")
