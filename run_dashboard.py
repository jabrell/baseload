from dashboard import dashboard, profile_dashboard


if __name__ == "__main__":
    # fn_results = "./data/results.parquet"
    # dashboard(fn_results)
    fn_profiles = "./data/renewables_with_load.parquet"
    profile_dashboard(fn_profiles)
