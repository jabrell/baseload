from typing import Any
import pandas as pd
import gams.transfer as gt
from .utils import create_inputs
from .gams_model import GamsModel


def extract_solution_storage(gdx: gt.Container) -> pd.DataFrame:
    """Extract solutions for minimum storage model

    Args:
        gdx: gdx container with solution values
    """
    # get labels
    re_labels = gdx["r"].records["i"].tolist()
    base_label = [i for i in gdx["i"].records["i"].tolist() if i not in re_labels][0]
    all_labels = re_labels + [base_label]
    cols_curtail = {c: f"curtailment{c.capitalize()}" for c in all_labels}

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
        .join(
            gdx["STO"]
            .records.pivot_table("level", "t", "s")
            .rename(columns={"storage": "storageLevel"})
        )
    ).assign(MAX_STO=gdx["MAX_STO"].records["level"].iloc[0])

    df_curtail = gdx["curtailment"].records
    if df_curtail is not None:
        df_curtail = (
            df_curtail.pivot_table("value", "t", "i")
            .fillna(0)
            .rename(columns=cols_curtail)
        )
        df = df.join(df_curtail)
    # ensure that all columns are in the frame even if values are zero
    for c in cols_curtail.values():
        if c not in df.columns:
            df[c] = 0.0

    # get scenario specification
    # base generation
    agen_base = gdx["agen"].records
    if agen_base is None:
        agen_base = pd.DataFrame([{"i": base_label, "value": 0.0}])
    else:
        agen_base = gdx["agen"].records
    # renewable generation
    agen_re = gdx["agen_re"].records
    if len(agen_re) > 0:
        agen_re = (
            gdx["sh_res"]
            .records.assign(value=lambda df: df["value"] * agen_re.iat[0, 0])
            .rename(columns={"r": "i"})
        )

    agen = pd.concat([agen_base, agen_re]).assign(
        share=lambda df: df["value"] / df["value"].sum()
    )
    df["share_generation"] = agen["value"].sum() / df["demand"].sum()
    df["share_renewable"] = agen.query(f"i in {re_labels}")["share"].sum()
    max_sto = gdx["MAX_STO"].records["level"].iloc[0]
    if max_sto is None:
        df["share_storage"] = 0.0
    else:
        df["share_storage"] = max_sto / df["demand"].sum()
    cost_curtail = gdx["cost_curtailment"].records.set_index("i")["value"].to_dict()
    df["costCurtailNuclear"] = cost_curtail.get("nuclear", 0)
    df["costCurtailRenewable"] = cost_curtail.get("renewable", 0)
    return df


def simulate_min_storage(
    data: pd.DataFrame,
    shares_renewable: list[float],
    share_generation: float = 1,
    renewables: list[str] = ["renewable"],
    share_renewable_technologies: dict[str:float] = None,
    fn_out: str | None = None,
    gamsopt: dict[str:str] | None = None,
    output: Any | None = None,
    label_base: str = "nuclear",
):
    """Run the model that minimizes storage given the share of renewable
    generation and total generation in terms of demand

    Args:
        data: Dataframe with hourly generation and demand data
        share_renewable: share of renewable generation in total generation
        renewables: list with names of renewable technologies
        share_renewable_technologies: dictionary with share of renewable generation
            in total renewable output (e.g. if we have wind and solar, the joint
            output would be 100 MWh and wind has 80% share, then the dictionary
            would be {"wind": 0.8, "solar": 0.2})
            If None, will be inferred from the data
        share_generation: share of total generation in demand
        fn_out: name of file to save results. If None, results are not saved
        gamsopt: dictionary with options for GAMS model
        output: destination of gams output stream#
        label_base: label for base scenario
    """
    lst_df = []
    cost_curtailment = {label_base: 2}
    cost_curtailment.update({r: 1 for r in renewables})
    for share_renewable in shares_renewable:  #
        # only optimize the storage share
        gdx = create_inputs(
            data,
            share_generation=share_generation,
            share_renewable=share_renewable,
            renewables=renewables,
            share_renewable_technologies=share_renewable_technologies,
            optimize_res_share=False,
            cost_curtailment=cost_curtailment,
            label_base=label_base,
        )
        # gdx.write("./model/test.gdx")
        model = GamsModel(files=["./model/model_min_storage.gms"], options=gamsopt)
        model.add_database(container=gdx, in_model_name="data")
        try:
            sol = model.run(output=output)
            # check solution statistics
            stats = sol["stats"].records.set_index("uni")["value"].to_dict()
            assert (
                stats["modelstat"] <= 2 and stats["solvestat"] == 1
            ), f"Model did not solve correctly: {stats}"
            obj = sol["Cost"].records.iat[0, 0]
            print(
                f"Minimize storage need for renewable share of {share_renewable*100}%. Objective: {obj:.0f}"
            )
            lst_df.append(extract_solution_storage(sol).assign(scenario="storageOnly"))
        except:
            print(f"Problems in solving for renewable share of {share_renewable}%")
            continue

        # scenarios that optimize the storage share
        gdx = create_inputs(
            data,
            share_generation=share_generation,
            share_renewable=share_renewable,
            renewables=renewables,
            share_renewable_technologies=share_renewable_technologies,
            optimize_res_share=True,
            cost_curtailment=cost_curtailment,
            label_base=label_base,
        )
        gdx.write("./model/test.gdx")
        model = GamsModel(files=["./model/model_min_storage.gms"], options=gamsopt)
        model.add_database(container=gdx, in_model_name="data")
        try:
            sol = model.run(output=output)
            # check solution statistics
            stats = sol["stats"].records.set_index("uni")["value"].to_dict()
            assert (
                stats["modelstat"] <= 2 and stats["solvestat"] == 1
            ), f"Model did not solve correctly: {stats}"
            obj = sol["Cost"].records.iat[0, 0]
            print(
                f"Minimize storage need for renewable share of {share_renewable*100}% with optimized RE technology share. Objective: {obj:.0f}"
            )
            lst_df.append(extract_solution_storage(sol).assign(scenario="optimalRE"))
        except Exception as e:
            print(
                f"Problems in solving for renewable share of {share_renewable}% with optimized RE technology share."
            )
            continue

    df = (
        pd.concat(lst_df)
        .reset_index()
        .assign(date=lambda df: pd.to_datetime(df["t"]))
        .drop("t", axis=1)
    )
    if fn_out is not None:
        df.to_parquet(fn_out, index=False)
    return df
