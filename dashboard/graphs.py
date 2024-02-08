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
    """Get data for plotting depending and calculate cost
    Args:
        df_annual: results aggregated over the whole time horizon
        cost_res: cost to install renewable generation [Euro/MWh]
        cost_nuc: cost to install nuclear generation [Euro/MWh]
        cost_res: cost to install storage facility [Euro/MWh]
        cost_res: cost to install energy not served [Euro/MWh]
        share_generation: total generation as multiple of demand
        curtail_res_first: indicator whether renewable are curtailed first
    """
    df = (
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
        .set_index(["share_storage", "share_renewable"])
        .reset_index()
    )
    return df


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
        x=[i * 100 for i in df.columns],
        y=[i * 100 for i in df.index],
        labels=dict(
            x="Renewable share [%]",
            y="Storage size [% of total demand]",
            color=f"{variable}",
        ),
        aspect="auto",
    )
    fig.update_layout(
        xaxis=dict(tickmode="array", tickvals=[i * 100 for i in df.columns]),
        yaxis=dict(tickmode="array", tickvals=[i * 100 for i in df.index]),
    )
    return fig


def plot_profile(
    df_p: pd.DataFrame,
    title: str = "",
    tech_order: list[str] | None = None,
    colors: dict[str, str] | None = None,
):
    """Plot profiles

    Args:
        df_p: dataframe with profiles in columns and x-axis as index
        title: title for the plot
        tech_order: order of technologies for stapling. If none, technologies are
            not stapled
        colors: color setting for profiles
    """
    # set default arguments
    tech_order = ["Baseload", "Wind", "Solar"] if tech_order is None else tech_order
    colors = (
        {"Demand": "Red", "Wind": "Green", "Solar": "Orange", "Baseload": "Black"}
        if colors is None
        else colors
    )

    # staple the profiles
    if tech_order is not None:
        base = pd.Series(0, index=df_p.index)
        for t in tech_order[1:]:
            if t in df_p.columns:
                base += df_p[t]
                df_p[t] = base
    # create figure
    fig = go.Figure()
    for c in df_p.columns:
        fig.add_trace(
            go.Scatter(
                x=df_p.index,
                y=df_p[c],
                mode="lines",
                line=dict(color=colors[c]),
                name=c,
            )
        )
        fig.update_layout(
            legend=dict(
                yanchor="bottom", y=-0.3, xanchor="left", x=0.3, orientation="h"
            ),
            yaxis=dict(title="Energy"),
            xaxis=dict(title=df_p.index.name),
            title=dict(text=title, xanchor="center", yanchor="top", x=0.4),
        )
    return fig
