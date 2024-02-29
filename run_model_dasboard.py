from dashboard import dashboard_model, profile_dashboard


if __name__ == "__main__":
    fn_results = "./data/results.parquet"
    dashboard_model(fn_results)
    # fn_gen = "./data/renewables_with_load.parquet"
    # fn_cap = "./data/renewables_capacity.parquet"
    # profile_dashboard(fn_gen, fn_cap)
