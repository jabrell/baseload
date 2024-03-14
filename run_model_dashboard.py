from dashboard import dashboard_minStorage


if __name__ == "__main__":
    fn_results = "./data/results_storage.parquet"
    fn_results = (
        "https://jabspublicbucket.s3.eu-central-1.amazonaws.com/results_storage.parquet"
    )
    dashboard_minStorage(fn_results)
    # fn_gen = "./data/renewables_with_load.parquet"
    # fn_cap = "./data/renewables_capacity.parquet"
    # profile_dashboard(fn_gen, fn_cap)
