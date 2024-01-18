import pandas as pd
import gams.transfer as gt
from .utils import get_standard_entsoe_input
from .gams_model import GamsModel


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
    cost_curtailment: dict[str, float] = {"nuclear": 1, "renewable": 0},
    total_demand: float | None = None,
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
            "demand", "renewable", "datetime"
        share_generation: multiplier used to derive total generation as multiple
            of total demand
        share_renewable: Share of renewable in total generation
        share_storage: Storage size as share of total demand
        cost_curtailment: Cost of curtailment by technology
        total_demand: If provided demand will be normalized to the given number
    Returns
        gdx container with data for model
    """
    assert (
        share_renewable >= 0 and share_renewable <= 1
    ), "Share of renewable has to be within the 0,1 interval."
    assert data["dateTime"].is_unique, "Date index is not unique"
    gdx = gt.Container()

    # total demand and generation of each technology

    if total_demand is None:
        total_demand = data["demand"].sum()
    # TODO allow for demand normalization
    total_generation = [
        ("nuclear", share_generation * total_demand * (1 - share_renewable)),
        ("renewable", share_generation * total_demand * share_renewable),
    ]
    max_storage = total_demand * share_storage

    # derive profiles and demand
    df_profiles = data[["dateTime", "demand", "renewable"]].set_index("dateTime")
    df_profiles = df_profiles / df_profiles.sum()
    df_profiles["nuclear"] = 1 / len(df_profiles)
    df_profiles = df_profiles.reset_index()
    df_demand = df_profiles[["dateTime", "demand"]].assign(
        demand=lambda df: df["demand"] * total_demand
    )

    # create sets
    i = gt.Set(gdx, "i", records=["nuclear", "renewable"], description="Technologies")
    s = gt.Set(gdx, "s", records=["storage"], description="storage")
    t = gt.Set(gdx, "t", description="periods", records=list(data["dateTime"].unique()))

    # parameters
    gt.Parameter(gdx, "dem", domain=[t], records=data[["dateTime", "demand"]])
    gt.Parameter(gdx, "agen", domain=[i], records=total_generation)
    gt.Parameter(
        gdx,
        "alpha",
        domain=[i, t],
        records=df_profiles[["dateTime", "nuclear", "renewable"]]
        .set_index("dateTime")
        .stack()
        .swaplevel()
        .reset_index(),
    )
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


def extract_solution(gdx: gt.Container) -> pd.DataFrame:
    """Extract solutions

    Args:
        gdx: gdx container with solution values
    """
    # collect results in a single dataframe
    df = (
        gdx["GEN"]
        .records.pivot_table("level", "t", "i")
        .join(
            gdx["REL"]
            .records.pivot_table("level", "t", "s")
            .join(
                gdx["INJ"].records.pivot_table("level", "t", "s") * (-1),
                rsuffix="in",
                lsuffix="out",
            )
            .assign(netStorage=lambda df: df.sum(1))
            .iloc[:, [-1]]
        )
        .join(gdx["dem"].records.set_index("t")["value"].to_frame("demand"))
        .join(gdx["ENS"].records.set_index("t")["level"].to_frame("energyNotServed"))
        .join(
            gdx["STO"]
            .records.pivot_table("level", "t", "s")
            .rename(columns={"storage": "storageLevel"})
        )
        .join(
            gdx["curtailment"]
            .records.pivot_table("value", "t", "i")
            .fillna(0)
            .rename(
                columns={"nuclear": "curtailNuclear", "renewable": "curtailRenewable"}
            )
        )
    )
    # ensure that all columns are in the frame even if values are zero
    cols = ["curtailNuclear", "curtailRenewable"]
    for c in cols:
        if c not in df.columns:
            df[c] = 0.0
    # get scenario specification
    agen = gdx["agen"].records.assign(share=lambda df: df["value"] / df["value"].sum())
    df["share_generation"] = agen["value"].sum() / df["demand"].sum()
    if "renewable" in agen["i"].unique():
        df["share_renewable"] = agen.query("i == 'renewable'")["share"].iloc[0]
    else:
        df["share_renewable"] = 0.0
    max_sto = gdx["max_sto"].records
    if max_sto is None:
        df["share_storage"] = 0.0
    else:
        df["share_storage"] = max_sto["value"].iloc[0] / df["demand"].sum()
    cost_curtail = gdx["cost_curtailment"].records.set_index("i")["value"].to_dict()
    df["costCurtailNuclear"] = cost_curtail.get("nuclear", 0)
    df["costCurtailRenewable"] = cost_curtail.get("renewable", 0)
    return df


def simulate(
    share_generation: list[float],
    share_renewable: list[float],
    share_storage: list[float],
    cost_curtailment: list[dict[str, float]] = [{"nuclear": 1, "renewable": 0}],
    total_demand: float | None = None,
    country: str = "DE",
    start: str = "2017/01/01 00:00",
    end: str = "2017/12/31 23",
    renewable: str = "windOnshore",
    fn_entsoe: str | None = None,
    fn_out: str | None = None,
):
    """Perform simulations over a set of scenarios.

    - Total generation over the time horizon is provided as multiple of total
      demand over the whole time horizon and then allocated to nuclear and
      renewable generation based on the exogenous share
    - For nuclear power the profile is assumed to be constant over the whole time
      horizon
    - For renewable generation the profile is inferred based in the input data
    - Maximum storage size is determined as share of total demand
    - Total demand can be normalized to given number

    Args:
        share_generation: list of multiplier used to derive total generation as multiple
            of total demand
        share_renewable: list of Share of renewable in total generation
        share_storage: list of Storage size as share of total demand
        cost_curtailment: list of Cost of curtailment by technology
        country: name of the country as letter ENTSOE code
        total_demand: If provided demand will be normalized to the given number
        renewable: renewable source used as input. Possible are:
            windOnshore, solar, windOffshore
        start: first hour to be included
        end: last hour to be included
        renewable: name of renewable source for profile
        fn_entsoe: name of parquet file with input data. If empty, standard one is used.
        fn_out: name of the output parquet file
    """
    # get input data
    df_entsoe = get_entsoe_data(country=country, start=start, end=end, fn=fn_entsoe)
    df_entsoe["renewable"] = df_entsoe[renewable]

    # perform simulations
    lst_df = []

    for s_ren in share_renewable:
        print(f"---- Simulations for renewable share: {s_ren}")
        for s_gen in share_generation:
            print(f"\t---- Simulations for generation share: {s_gen}")
            for s_sto in share_storage:
                for c_cur in cost_curtailment:
                    gdx = create_inputs(
                        df_entsoe,
                        share_generation=s_gen,
                        share_renewable=s_ren,
                        share_storage=s_sto,
                        cost_curtailment=c_cur,
                        total_demand=total_demand,
                    )
                    model = GamsModel()
                    model.add_database(container=gdx, in_model_name="data")
                    try:
                        sol = model.run(output=None)
                        # check solution statistics
                        stats = sol["stats"].records.set_index("uni")["value"].to_dict()
                        assert (
                            stats["modelstat"] <= 2
                        ), f"Model did not solve correctly: {stats}"
                        assert (
                            stats["solvestat"] == 1
                        ), f"Model did not solve correctly: {stats}"
                    except:
                        print(
                            f"Problems in solving with specification (share gen, ren, sto, cost curtailment): {s_gen}, {s_ren}, {s_sto}, {c_cur}"
                        )
                        continue
                    lst_df.append(extract_solution(sol))
    df = (
        pd.concat(lst_df)
        .reset_index()
        .assign(date=lambda df: pd.to_datetime(df["t"]))
        .drop("t", axis=1)
    )
    if fn_out is not None:
        df.to_parquet(fn_out, index=False)
    return df
