import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots


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
    colors: dict[str, str],
    title: str = "",
    tech_order: list[str] | None = None,
):
    """Plot profiles

    Args:
        df_p: dataframe with profiles in columns and x-axis as index
        colors: color setting for profiles. Maps column name to display color
            if a column is not used as key, it will not be shown
        title: title for the plot
        tech_order: order of technologies for stapling.
        stack_profiles: indicator to stack profiles in the order provided by tech_order
    """
    # staple the profiles
    if tech_order is not None:
        base = pd.Series(0, index=df_p.index)
        for t in tech_order:
            if t in df_p.columns:
                base += df_p[t]
                df_p[t] = base
    # create figure
    fig = go.Figure()
    for c in colors.keys():
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
                yanchor="bottom", y=-0.3, xanchor="left", x=0.2, orientation="h"
            ),
            yaxis=dict(title="Energy [MWh]", rangemode="tozero"),
            xaxis=dict(title=df_p.index.name),
            title=dict(text=title, xanchor="center", yanchor="top", x=0.45),
        )
    return fig


def plot_daily_generation(
    df: pd.DataFrame,
    days: int = 1,
    tech_order: list[str] | None = None,
    colors: dict[str, str] | None = None,
    percent_daily_demand: bool = False,
):
    """Plot generation by daily sums

    Args:
        df: dataframe with generation and demand in hourly frequency
        days: number of days to aggregate
        tech_order: order of technologies in plot
        colors: colors of items in plot
        percent_daily_demand: if true express values as
            percent of daily demand
    """
    # default settings
    tech_order = ["Baseload", "Wind", "Solar"] if tech_order is None else tech_order
    colors = (
        {"Demand": "Red", "Wind": "Green", "Solar": "Orange", "Baseload": "Black"}
        if colors is None
        else colors
    )
    # if dataframe is empty return empty figure
    if len(df) == 0:
        return go.Figure()
    # resample to daily
    df_daily = df.resample(f"{days}D").sum()
    if percent_daily_demand:
        df_daily = df_daily.div(df_daily["Demand"], axis=0) * 100
        ytitle = "Share in daily demand [%]"
    else:
        ytitle = "Energy [MWh]"

    # create figure
    fig = go.Figure()
    traces = [
        go.Scatter(
            x=df_daily.index,
            y=df_daily[c],
            stackgroup="one",
            mode="lines",
            name=c,
            line=dict(width=0.5, color=colors[c]),
        )
        for c in tech_order
        if c in df_daily.columns
    ]
    traces.append(
        go.Scatter(
            x=df_daily.index,
            y=df_daily["Demand"],
            mode="lines",
            name="Demand",
            line=dict(width=1, color=colors["Demand"]),
        )
    )
    fig.add_traces(traces)
    fig.update_layout(
        yaxis=dict(title=ytitle, rangemode="tozero"),
        margin=go.layout.Margin(
            l=0,  # left margin
            r=0,  # right margin
            b=0,  # bottom margin
            t=0,  # top margin
        ),
    )
    return fig


def plot_cost_storage_scenarios(df: pd.DataFrame, plot_cost: bool = True) -> go.Figure:
    """Plot cost of storage scenarios

    Args:
        df: dataframe with results
        plot_cost: if True, plot cost on second y-axis
    """

    df_s = (
        df.query(f"scenario == 'storageOnly'")[["share_renewable", "MAX_STO", "cost"]]
        .drop_duplicates()
        .assign(share_renewable=lambda x: (x["share_renewable"] * 100).round(1))
    )

    df_res = (
        df.query(f"scenario == 'optimalRE'")[["share_renewable", "MAX_STO", "cost"]]
        .drop_duplicates()
        .assign(share_renewable=lambda x: (x["share_renewable"] * 100).round(1))
    )

    fig = make_subplots(specs=[[{"secondary_y": True}]])

    fig.add_trace(
        go.Scatter(
            x=df_s["share_renewable"],
            y=df_s["MAX_STO"],
            mode="lines",
            line=dict(color="blue"),
            name="Storage only",
        ),
        secondary_y=False,
    )
    fig.add_trace(
        go.Scatter(
            x=df_res["share_renewable"],
            y=df_res["MAX_STO"],
            mode="lines",
            line=dict(color="green"),
            name="RE Portfolio + Storage",
        ),
        secondary_y=False,
    )
    fig.update_layout(
        xaxis=dict(domain=[0, 1], title="Share of Renewables in Demand [%]"),
        yaxis=dict(title="Maximum Storage [MWh]", rangemode="tozero"),
        yaxis2=dict(title="Cost [€]", rangemode="tozero"),
        # legend=dict(orientation="h", yanchor="bottom", y=-0.35, xanchor="left", x=0.2),
    )

    # add the cost on the second y-axis
    plot_cost = False
    if plot_cost:
        fig.add_trace(
            go.Scatter(
                x=df_s["share_renewable"],
                y=df_s["cost"],
                mode="lines",
                line=dict(color="blue", dash="dot"),
                name="Cost: Storage only",
                visible="legendonly",
            ),
            secondary_y=True,
        )

        fig.add_trace(
            go.Scatter(
                x=df_res["share_renewable"],
                y=df_res["cost"],
                mode="lines",
                line=dict(color="green", dash="dash"),
                name="Cost: RE Portfolio + Storage",
                visible="legendonly",
            ),
            secondary_y=True,
        )
        fig.update_layout(
            yaxis2=dict(title="Cost [€]", rangemode="tozero"),
            # legend=dict(orientation="h", yanchor="bottom", y=-0.35, xanchor="left", x=0.2),
        )

    return fig


def plot_storage_results(
    df: pd.DataFrame,
    re_levels: list[float] | None = None,
    scenario: str = "storageOnly",
) -> go.Figure:
    """Plot distributions for storage level and net storage

    Args:
        df: dataframe with results
        re_levels: renewable levels to plot
        scenario: scenario to plot
    """
    if re_levels is None:
        re_levels = [i / 10 for i in range(11)]

    df_p = (
        df.assign(share_renewable=lambda df: df["share_renewable"].round(2))
        .query(f"share_renewable in {re_levels} and scenario == '{scenario}'")
        .assign(share_renewable=lambda x: (x["share_renewable"] * 100).round(1))
    )

    fig = make_subplots(specs=[[{"secondary_y": True}]])
    fig.add_trace(
        go.Box(
            x=df_p["share_renewable"],
            y=df_p["storageLevel"],
            marker_color="darkblue",
            name="Storage Level",
        ),
        secondary_y=False,
    )
    fig.add_trace(
        go.Box(
            x=df_p["share_renewable"],
            y=df_p["netStorage"],
            marker_color=" limegreen",
            name="Net-generation",
        ),
        secondary_y=True,
    )
    fig.update_layout(
        title="Storage Level and Net-generation of Storage",
        xaxis=dict(domain=[0, 1], title="Share of Renewables in Demand [%]"),
        yaxis=dict(title="Storage Level [MWh]", rangemode="tozero"),
        yaxis2=dict(title="Net-generation [MWh]"),
    )
    return fig


def plot_storage_level(
    df: pd.DataFrame,
    scenario: str = "storageOnly",
    re_level: float = 0.5,
    by: str = "week",
) -> go.Figure:
    """Plot storage level over time

    Args:
        df: dataframe with results
        re_level: renewable level to plot
        scenario: scenario to plot
        by: time dimsions for the x-axis
            possible values: "week", "day", "month"
    """
    df_p = (
        df.assign(share_renewable=lambda df: df["share_renewable"].round(2))
        .query(f"share_renewable == {re_level} and scenario == '{scenario}'")
        .assign(
            week=lambda x: x["date"].dt.isocalendar().week,
            day=lambda x: x["date"].dt.dayofyear,
            month=lambda x: x["date"].dt.month,
        )[["date", "storageLevel", "netStorage", "week", "day", "month"]]
    )
    fig = make_subplots(specs=[[{"secondary_y": True}]])
    fig.add_trace(
        go.Box(
            x=df_p[by],
            y=df_p["storageLevel"],
            marker_color="darkblue",
            name="Storage Level",
        ),
        secondary_y=False,
    )
    fig.add_trace(
        go.Box(
            x=df_p[by],
            y=df_p["netStorage"],
            marker_color="limegreen",
            name="Net-generation",
        ),
        secondary_y=True,
    )
    fig.update_layout(
        title=f"Storage Over Time: Scenario '{scenario}' with Renewable Share {round(re_level*100, 0)}%",
        xaxis=dict(domain=[0, 1], title=by.capitalize()),
        yaxis=dict(title="Storage Level [MWh]", rangemode="tozero"),
        yaxis2=dict(title="Net-generation [MWh]"),
    )
    return fig


def plot_renewable_shares(
    df: pd.DataFrame,
    renewables: list[str] = ["wind", "solar"],
    scenario: str = "optimalRE",
    add_observed: bool = True,
):
    """Plot share of each renewable technology in total renewable generation.
    Args:
        df: dataframe with hourly results
        renewables: list of renewable technologies
        scenario: scenario to plot (usually: optimalRE)
        add_observed: if True, plot observed shares from storageOnly scenario
    """
    df_ = (
        df[["scenario", "share_renewable"] + renewables]
        .groupby(["scenario", "share_renewable"])[renewables]
        .sum()
        .assign(total=lambda x: x.sum(1))
    )
    df_ = (
        (df_.div(df_["total"], axis=0) * 100)
        .fillna(0)
        .round(2)
        .reset_index()
        .assign(share_renewable=lambda x: (x["share_renewable"] * 100).round(1))
    )

    # df_.query("scenario == 'optimalRE'")
    df_p = df_.query(f"scenario == '{scenario}'")
    fig = go.Figure()

    colors = ["darkgreen", "orange", "darkblue"]
    for i, r in enumerate(renewables):
        fig.add_trace(
            go.Scatter(
                x=df_p["share_renewable"],
                y=df_p[r],
                mode="lines",
                name=r.capitalize(),
                marker=dict(color=colors[i]),
            )
        )
    # add the observed share
    if add_observed:
        observed = (
            df_.query("scenario == 'storageOnly'")
            .drop_duplicates(subset=renewables)[renewables]
            .iloc[-1]
            .to_dict()
        )
        for i, r in enumerate(renewables):
            fig.add_trace(
                go.Scatter(
                    x=df_p["share_renewable"],
                    y=len(df_p["share_renewable"]) * [observed[r]],
                    mode="lines",
                    name=f"{r.capitalize()} observed",
                    line=dict(color=colors[i], dash="dot"),
                )
            )
    fig.update_layout(
        title=f"Share of Renewable Technologies in Total Renewable Generation",
        xaxis=dict(domain=[0, 1], title="Share of Renewables in Demand [%]"),
        yaxis=dict(
            title="Technology Share in Total RE Generation [%]", rangemode="tozero"
        ),
    )

    return fig
