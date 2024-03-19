import os
import pandas as pd
import gams.transfer as gt


def get_temp_dir() -> str:
    """Get path to temporary directory. If not exists will be created"""
    temp_dir = os.path.join(os.getcwd(), "_temp")
    if not os.path.exists(temp_dir):
        os.makedirs(temp_dir)
    return temp_dir


def get_standard_entsoe_input() -> str:
    """Get path to standard input file with ENTSOE data"""
    return os.path.join(
        os.path.dirname(__file__), "..", "data", "renewables_with_load.parquet"
    )


def get_entsoe_data(
    country: str, start: str, end: str, fn: str | None = None
) -> pd.DataFrame:
    """Get renewable and demand data for a given country

    Args:
        country: name of the country as letter ENTSOE code
        start: first hour to be included
        end: last hour to be included
        fn: name of parquet file with input data. If empty, standard one is used.
    """
    if fn is None:
        fn = get_standard_entsoe_input()
    df = pd.read_parquet(
        fn,
        filters=[
            ("country", "==", country),
            ("dateTime", ">=", pd.to_datetime(start)),
            ("dateTime", "<=", pd.to_datetime(end)),
        ],
    )
    return df


def create_inputs(
    data: pd.DataFrame,
    share_generation: float = 1,
    share_renewable: float = 0.5,
    share_storage: float = 0,
    renewables: list[str] = ["renewable"],
    optimize_res_share: bool = False,
    share_renewable_technologies: dict[str:float] | None = None,
    total_demand: float | None = None,
    cost_curtailment: dict[str, float] = {"nuclear": 1, "renewable": 0},
    label_base: str = "nuclear",
) -> gt.Container:
    """Create inputs for model run based on ENTSOE renewable generation and demand.

    - Total generation over the time horizon is provided as multiple of total
      demand over the whole time horizon and then allocated to nuclear and
      renewable generation based on the exogenous share
    - For nuclear power the profile is assumed to be constant over the whole time
      horizon
    - For renewable generation the profile is inferred based in the input data
    - Maximum storage size is determined as share of total demand
    - Total demand can be normalized to given number

    Args:
        data: A dataframe with the following columns:
            "demand", renewables, "datetime"
        share_generation: multiplier used to derive total generation as multiple
            of total demand
        share_renewable: Share of renewable in total generation
        renewables: list with names of renewable technologies
        share_renewable_technologies: dictionary with share of renewable generation
            in total renewable output (e.g. if we have wind and solar, the joint
            output would be 100 MWh and wind has 80% share, then the dictionary
            would be {"wind": 0.8, "solar": 0.2})
            If None, will be inferred from the data
        share_storage: Storage size as share of total demand
        cost_curtailment: Cost of curtailment by technology
        label_base: label for base technology
    Returns
        gdx container with data for model
    """
    assert (
        share_renewable >= 0 and share_renewable <= 1
    ), "Share of renewable has to be within the 0,1 interval."
    assert data["dateTime"].is_unique, "Date index is not unique"
    # ensure that renewables are positive
    for r in renewables:
        data[r] = data[r].clip(lower=0)
    if share_renewable_technologies is None:
        share_renewable_technologies = (
            data[renewables].sum() / data[renewables].sum().sum()
        ).to_dict()
    assert (
        round(sum(share_renewable_technologies.values()), 4) == 1
    ), "Renewable shares do not sum to 1"

    gdx = gt.Container()

    # total demand and generation of each technology
    if total_demand is None:
        total_demand = data["demand"].sum()

    total_generation_base = [
        (label_base, share_generation * total_demand * (1 - share_renewable))
    ]
    total_generation_renewable = share_generation * total_demand * share_renewable
    max_storage = total_demand * share_storage

    # derive profiles and demand
    df_profiles = data[["dateTime", "demand"] + renewables].set_index("dateTime")
    df_profiles = df_profiles / df_profiles.sum()
    df_profiles[label_base] = 1 / len(df_profiles)
    df_profiles = df_profiles.reset_index()
    df_demand = df_profiles[["dateTime", "demand"]].assign(
        demand=lambda df: df["demand"] * total_demand
    )

    # create sets
    i = gt.Set(
        gdx, "i", records=([label_base] + renewables), description="Technologies"
    )
    r = gt.Set(
        gdx, "r", domain=[i], records=renewables, description="renewable technologies"
    )
    s = gt.Set(gdx, "s", records=["storage"], description="storage")
    t = gt.Set(gdx, "t", description="periods", records=list(data["dateTime"].unique()))

    # parameters
    gt.Parameter(gdx, "dem", domain=[t], records=data[["dateTime", "demand"]])
    gt.Parameter(gdx, "agen", domain=[i], records=total_generation_base)
    gt.Parameter(gdx, "agen_re", records=total_generation_renewable)
    gt.Parameter(
        gdx,
        "alpha",
        domain=[i, t],
        records=df_profiles[["dateTime", label_base] + renewables]
        .set_index("dateTime")
        .stack()
        .swaplevel()
        .reset_index(),
    )
    gt.Parameter(
        gdx,
        "sh_res",
        domain=[r],
        records=share_renewable_technologies.items(),
        description="share of renewable technologies in total renewable generation",
    )
    if optimize_res_share:
        gt.Parameter(gdx, "optimize_res_share", records=[1])
    else:
        gt.Parameter(gdx, "optimize_res_share", records=[0])
    gt.Parameter(gdx, "dem", domain=[t], records=df_demand)
    gt.Parameter(
        gdx,
        "max_sto",
        domain=[s],
        records=[["storage", max_storage]],
    )
    gt.Parameter(
        gdx,
        "cost_curtailment",
        domain=[i],
        records=[(k, v) for k, v in cost_curtailment.items()],
    )
    return gdx
