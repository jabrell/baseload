import os


def get_temp_dir() -> str:
    """Get path to tempory directory. If not exists will be created"""
    temp_dir = os.path.join(os.getcwd(), "_temp")
    if not os.path.exists(temp_dir):
        os.makedirs(temp_dir)
    return temp_dir


def get_standard_entsoe_input() -> str:
    """Get path to standard input file with ENTSOE data"""
    return os.path.join(
        os.path.dirname(__file__), "..", "data", "renewables_with_load.parquet"
    )
