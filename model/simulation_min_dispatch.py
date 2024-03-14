import sys
from typing import Any
import pandas as pd
import gams.transfer as gt
from .gams_model import GamsModel
from .utils import create_inputs, get_entsoe_data


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


def simulate_min_dispatchable(
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
    """Perform simulations over a set of scenarios. This set of scenarios minimizes
    the amount of dispatchable generation given the share of renewable, storage,
    and baseload generation (in total demand).

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
                print(f"\t---- Simulations for storage share: {s_sto}")
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
