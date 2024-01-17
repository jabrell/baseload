import pandas as pd
import plotly.graph_objects as go
import plotly.express as px


def get_plot_variable(
    df_annual: pd.DataFrame,
    cost_res: float,
    cost_nuc: float,
    cost_sto: float,
    cost_ens: float,
    share_generation: float,
    curtail_res_first=True,
) -> pd.DataFrame:
    """Get data for plotting depending and calculate cost"""
    return (
        df_annual.query(f"share_generation == {share_generation}")
        .query(f"curtailRenewableFirst == {curtail_res_first}")
        .assign(
            cost=lambda df: (
                (df["nuclear"] + df["curtailNuclear"]) * cost_nuc
                + (df["renewable"] + df["curtailRenewable"]) * cost_res
                + df["energyNotServed"] * cost_ens
                + df["demand"] * df["share_storage"] * cost_sto
            )
        )
        .drop(["curtailRenewableFirst", "share_generation"], axis=1)
    ).round(1)


def plot_heatmap(df_plot: pd.DataFrame, variable: str = "cost") -> go.Figure:
    """Plot heat map for a given variable

    Args:
        df_plot: basic data for plotting already filtered for generation share
        variable: variable to plot
    """
    df = df_plot.pivot_table(
        variable,
        "share_storage",
        "share_renewable",
    )
    fig = px.imshow(
        df.values,
        x=df.columns,
        y=df.index,
        labels=dict(
            x="Renewable share [%]",
            y="Storage size [% of total demand]",
            color=f"{variable}",
        ),
        aspect="auto",
    )
    fig.update_layout(
        xaxis=dict(tickmode="array", tickvals=df.columns),
        yaxis=dict(tickmode="array", tickvals=df.index),
    )
    return fig
