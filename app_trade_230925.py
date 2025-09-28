# -*- coding: utf-8 -*-
"""Dash application for analysing Swiss trade flows.

The module was refactored to improve readability, consistency and
translation handling while keeping the original functionality intact.
"""
from __future__ import annotations

from dash import Dash, Input, Output, dcc, html
import dash_bootstrap_components as dbc
import dash_mantine_components as dmc
import humanize
import os
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import textwrap

from translations import LANG


# =========================
# Configuration
# =========================
DEFAULT_LANG = "en"
DEFAULT_HS_LEVEL = "HS6_Description"
DEFAULT_TAB = "trend"
DEFAULT_COUNTRY_PRODUCTS_TOP = "5"
TOP_COUNTRY_LIMIT = 25
TOP_PRODUCT_LIMIT = 20
TREEMAP_TOP_COUNTRIES = 15
TREEMAP_MIN_VALUE = 10000

HS_LEVEL_CONFIG: dict[str, dict[str, str]] = {
    # Mapping is shared across the app so we keep it in a single place.
    "HS2_Description": {"code": "HS2", "label": "HS2_Label", "description": "HS2_Description"},
    "HS4_Description": {"code": "HS4", "label": "HS4_Label", "description": "HS4_Description"},
    "HS6_Description": {"code": "HS6", "label": "HS6_Label", "description": "HS6_Description"},
    "HS8_Description": {"code": "HS8", "label": "HS8_Label", "description": "HS8_Description"},
}

GRAPH_STYLE = {
    "font_family": "Arial",
    "font_size": 16,
    "title_size": 22,
    # KPI card base style is reused for all cards to avoid duplication.
    "kpi_card": {
        "boxShadow": "3px 3px 12px rgba(0,0,0,0.15)",
        "borderRadius": "15px",
        "padding": "30px",
        "margin": "30px",
        "flex": "1",
        "textAlign": "center",
        "fontWeight": "bold",
        "fontSize": "28px",
        "background": "white",
        "fontFamily": "Arial",
        "height": "220px",
    },
    # Brand colours centralised for reuse across all charts.
    "color_export": "#00c08d",
    "color_import": "#e6301f",
    "color_trade": "#022B7E",
    "template": "plotly_white",
    "bg_color_export": "#ecfffa",
    "bg_color_import": "#fef3f2",
    "bg_color_balance": "#b4ccfe",
    "bg_color_trade": "#f0f0f0",
    "legend_horizontal": {
        "orientation": "h",
        "y": -0.25,
        "x": 0.5,
        "xanchor": "center",
        "yanchor": "top",
        "bgcolor": "rgba(255,255,255,0.6)",
        "bordercolor": "lightgray",
        "borderwidth": 1,
        "font": {"size": 14},
    },
    "legend_vertical": {
        "orientation": "v",
        "y": 1,
        "x": 1.05,
        "xanchor": "left",
        "yanchor": "top",
        "bgcolor": "rgba(255,255,255,0.6)",
        "bordercolor": "lightgray",
        "borderwidth": 1,
        "font": {"size": 14},
    },
    "legend_bottom_vertical": {
        "orientation": "v",
        "y": -0.3,
        "x": 0,
        "xanchor": "left",
        "yanchor": "top",
        "bgcolor": "rgba(255,255,255,0.6)",
        "bordercolor": "lightgray",
        "borderwidth": 1,
        "font": {"size": 14},
        "itemsizing": "trace",
    },
}


# =========================
# Data loading
# =========================
def load_dataset() -> pd.DataFrame:
    """Load and standardise the trade dataset."""

    data = pd.read_csv(
        "trade_subset_latam.csv.gz",
        sep=";",
        encoding="utf-8",
        compression="gzip",
    )

    data["year"] = pd.to_numeric(data["year"], errors="coerce").astype("Int64")
    data["chf_num"] = pd.to_numeric(data["chf_num"], errors="coerce").fillna(0).astype(float)

    for column in ["country_en", "HS2_Description", "HS4_Description", "HS6_Description", "HS8_Description", "traffic"]:
        if column in data.columns:
            data[column] = data[column].fillna("Unknown").astype(str)

    # Map raw traffic codes to user friendly labels for reuse in the app.
    data["Flow"] = data["traffic"].map({"EXP": "Export", "IMP": "Import"}).fillna(data["traffic"])

    # Ensure consistent eight digit product keys.
    data["tn_key"] = (
        data["tn_key"].astype(str).str.replace("[^0-9]", "", regex=True).str.zfill(8)
    )

    # Prepare HS hierarchy helpers once to avoid recomputation in callbacks.
    data["HS2"] = data["tn_key"].str[:2]
    data["HS2_Label"] = data["HS2"] + " – " + data["HS2_Description"]

    data["HS4"] = data["tn_key"].str[:4]
    data["HS4_Label"] = data["HS4"].str[:2] + data["HS4"].str[2:] + " – " + data["HS4_Description"]

    data["HS6"] = data["tn_key"].str[:6]
    data["HS6_Label"] = data["HS6"].str[:4] + "." + data["HS6"].str[4:] + " – " + data["HS6_Description"]

    data["HS8"] = data["tn_key"].str[:8]
    data["HS8_Label"] = data["HS8"].str[:4] + "." + data["HS8"].str[4:] + " – " + data["HS8_Description"]

    return data


df = load_dataset()


# =========================
# Helper utilities
# =========================
def get_labels(lang: str | None) -> dict[str, str]:
    """Return translation labels with a graceful fallback."""

    return LANG.get(lang or DEFAULT_LANG, LANG[DEFAULT_LANG])


def ensure_list(values: list[str] | str | None) -> list[str]:
    """Normalise callback inputs to a list of strings."""

    if values is None:
        return []
    if isinstance(values, list):
        return [str(v) for v in values if v]
    return [str(values)]


def wrap_text(text: str, width: int = 30) -> str:
    """Wrap a string with HTML line breaks."""

    if not isinstance(text, str):
        return ""
    return "<br>".join(textwrap.wrap(text, width=width))


def wrap_and_shorten(text: str, wrap_width: int = 30, max_len: int = 60) -> str:
    """Shorten and wrap long text labels for better readability."""

    if not isinstance(text, str):
        return ""
    truncated = text if len(text) <= max_len else text[:max_len] + "…"
    return "<br>".join(textwrap.wrap(truncated, width=wrap_width))


def human_format(value: float | int | None) -> str:
    """Format large numbers with readable suffixes (e.g. 1.2M)."""

    if value is None or pd.isna(value):
        return "0"
    formatted = humanize.intword(value, format="%.1f")
    return (
        formatted.replace(" thousand", "T")
        .replace(" million", "M")
        .replace(" billion", "Bn")
        .replace(" trillion", "Tn")
    )


def apply_standard_layout(
    figure: go.Figure,
    labels: dict[str, str],
    *,
    x_title: str = "",
    y_title: str = "",
    legend: str | bool = "horizontal",
    height: int = 1000,
    legend_title: str | None = None,
) -> go.Figure:
    """Apply a consistent layout used across all charts."""

    legend_config = None
    if legend == "horizontal":
        legend_config = GRAPH_STYLE["legend_horizontal"]
    elif legend == "vertical":
        legend_config = GRAPH_STYLE["legend_vertical"]
    elif legend == "bottom_outside":
        legend_config = GRAPH_STYLE["legend_bottom_vertical"]

    figure.update_layout(
        height=height,
        xaxis_title=x_title,
        yaxis_title=y_title,
        template=GRAPH_STYLE["template"],
        font={"family": GRAPH_STYLE["font_family"], "size": GRAPH_STYLE["font_size"]},
        title={"font": {"size": GRAPH_STYLE["title_size"]}},
        legend=legend_config,
        legend_title_text=legend_title,
        hoverlabel={"align": "left"},
    )
    return figure


def format_year_period(years: list[int], labels: dict[str, str]) -> str:
    """Create a human readable year selection string."""

    if not years:
        return labels["year_all"]
    ordered = sorted(years)
    if len(ordered) == 1:
        return str(ordered[0])
    return labels["year_range"].format(start=ordered[0], end=ordered[-1])


def format_country_label(countries: list[str], labels: dict[str, str]) -> str:
    """Return a comma separated country list with fallback."""

    if not countries:
        return labels["countries_all"]
    return labels["country_separator"].join(countries)


def sanitise_hs_level(hs_level: str | None) -> str:
    """Ensure we always have a valid HS level selection."""

    if hs_level in HS_LEVEL_CONFIG:
        return hs_level
    return DEFAULT_HS_LEVEL


def filter_dataframe(
    base: pd.DataFrame,
    *,
    years: list[int],
    countries: list[str],
    hs_level: str,
    products: list[str],
) -> pd.DataFrame:
    """Apply all user filters to the dataset."""

    filtered = base.copy()

    if countries:
        filtered = filtered[filtered["country_en"].isin(countries)]

    if products:
        hs_info = HS_LEVEL_CONFIG[hs_level]
        filtered = filtered[filtered[hs_info["code"]].isin(products)]

    if years:
        filtered = filtered[filtered["year"].isin(years)]

    return filtered


def build_kpi_cards(filtered: pd.DataFrame, years: list[int], labels: dict[str, str]) -> html.Div:
    """Create KPI cards summarising exports, imports and balance."""

    exp_sum = filtered.loc[filtered["Flow"] == "Export", "chf_num"].sum()
    imp_sum = filtered.loc[filtered["Flow"] == "Import", "chf_num"].sum()
    balance_value = exp_sum - imp_sum
    volume_value = exp_sum + imp_sum
    period_label = format_year_period(years, labels)

    def build_card(title: str, value: float, colour: str, background: str) -> html.Div:
        return html.Div(
            [
                html.Div(title, style={"fontSize": "20px", "padding": "16px"}),
                html.Div(
                    f"CHF {value:,.0f}".replace(",", "'"),
                    style={"fontSize": "28px", "fontWeight": "bold"},
                ),
            ],
            style={**GRAPH_STYLE["kpi_card"], "color": colour, "backgroundColor": background},
        )

    return html.Div(
        [
            build_card(f"{labels['kpi_exports']} {period_label}", exp_sum, GRAPH_STYLE["color_export"], GRAPH_STYLE["bg_color_export"]),
            build_card(f"{labels['kpi_imports']} {period_label}", imp_sum, GRAPH_STYLE["color_import"], GRAPH_STYLE["bg_color_import"]),
            build_card(f"{labels['kpi_balance']} {period_label}", balance_value, GRAPH_STYLE["color_trade"], GRAPH_STYLE["bg_color_balance"]),
            build_card(f"{labels['kpi_volume']} {period_label}", volume_value, "black", GRAPH_STYLE["bg_color_trade"]),
        ],
        style={
            "display": "flex",
            "gap": "25px",
            "padding": "10px",
            "justifyContent": "space-evenly",
            "width": "100%",
            "height": "250px",
            "alignItems": "center",
        },
    )


def create_trend_content(data: pd.DataFrame, countries: list[str], labels: dict[str, str]) -> html.Div:
    """Render the yearly trade volume chart including trade balance."""

    if data.empty:
        # Provide an empty graph rather than failing when no data is left.
        empty_fig = go.Figure()
        empty_fig.update_layout(title=labels["graph_trend_title"].format(period=labels["year_all"]))
        return dcc.Graph(id="trend_graph", figure=empty_fig)

    trend = data.groupby(["year", "Flow"])["chf_num"].sum().reset_index()
    years = trend["year"].unique()
    flows = ["Export", "Import"]
    full_index = pd.MultiIndex.from_product([years, flows], names=["year", "Flow"])
    trend = trend.set_index(["year", "Flow"]).reindex(full_index, fill_value=0).reset_index()

    balance = trend.pivot(index="year", columns="Flow", values="chf_num").fillna(0)
    for flow in flows:
        if flow not in balance.columns:
            balance[flow] = 0
    balance["Balance"] = balance["Export"] - balance["Import"]

    country_label = format_country_label(countries, labels)
    period_label = format_year_period(sorted(data["year"].dropna().unique().tolist()), labels)
    chart_title = labels["graph_trend_title"].format(period=period_label, countries=country_label)

    fig = px.bar(
        trend,
        x="year",
        y="chf_num",
        color="Flow",
        barmode="stack",
        template=GRAPH_STYLE["template"],
        title=chart_title,
        color_discrete_map={"Export": GRAPH_STYLE["color_export"], "Import": GRAPH_STYLE["color_import"]},
    )

    fig.update_traces(
        hovertemplate=(
            f"<b>{labels['hover_year']}:</b> %{{x}}<br>"
            f"<b>{labels['hover_flow']}:</b> %{{fullData.name}}<br>"
            f"<b>{labels['hover_chf']}:</b> %{{y:,.0f}}<extra></extra>"
        ),
        selector={"type": "bar"},
    )

    fig.add_scatter(
        x=balance.index,
        y=balance["Balance"],
        mode="lines+markers+text",
        name=labels["kpi_balance"],
        line={"color": GRAPH_STYLE["color_trade"], "width": 5, "dash": "dot"},
        marker={"size": 16, "symbol": "circle"},
        text=[human_format(v) for v in balance["Balance"]],
        textposition="top center",
        hovertemplate=(
            f"<b>{labels['hover_year']}:</b> %{{x}}<br>"
            f"<b>{labels['kpi_balance']}:</b> %{{y:,.0f}}<extra></extra>"
        ),
    )

    fig = apply_standard_layout(
        fig,
        labels,
        x_title=labels["axis_year"],
        y_title=labels["axis_chf"],
        legend="horizontal",
        height=900,
        legend_title=labels["legend_flow"],
    )

    return html.Div(
        dcc.Graph(id="trend_graph", figure=fig, style={"height": "80vh", "width": "80vw"}),
        style={"display": "flex", "justifyContent": "center", "alignItems": "center", "padding": "20px"},
    )


def create_country_content(data: pd.DataFrame, years: list[int], labels: dict[str, str]) -> html.Div:
    """Render stacked trade by country chart."""

    if data.empty:
        empty_fig = go.Figure()
        empty_fig.update_layout(title=labels["graph_country_title"].format(period=format_year_period(years, labels)))
        return dcc.Graph(id="country_graph", figure=empty_fig)

    country_ranking = data.groupby(["country_en", "Flow"])["chf_num"].sum().reset_index()
    totals = country_ranking.groupby("country_en")["chf_num"].sum().reset_index()
    top_countries = totals.sort_values("chf_num", ascending=False).head(TOP_COUNTRY_LIMIT)["country_en"]
    country_ranking = country_ranking[country_ranking["country_en"].isin(top_countries)]

    period_label = format_year_period(years, labels)
    fig = px.bar(
        country_ranking,
        x="chf_num",
        y="country_en",
        color="Flow",
        barmode="stack",
        orientation="h",
        template=GRAPH_STYLE["template"],
        title=labels["graph_country_title"].format(period=period_label),
        color_discrete_map={"Export": GRAPH_STYLE["color_export"], "Import": GRAPH_STYLE["color_import"]},
    )

    fig.update_traces(
        hovertemplate=(
            f"<b>{labels['hover_country']}:</b> %{{y}}<br>"
            f"<b>{labels['hover_flow']}:</b> %{{fullData.name}}<br>"
            f"<b>{labels['hover_chf']}:</b> %{{x:,.0f}}<extra></extra>"
        )
    )

    fig.update_layout(yaxis={"categoryorder": "total ascending"})
    fig = apply_standard_layout(
        fig,
        labels,
        x_title=labels["axis_chf"],
        y_title=labels["axis_country"],
        legend="horizontal",
        height=900,
        legend_title=labels["legend_flow"],
    )

    return html.Div(
        dcc.Graph(id="country_graph", figure=fig, style={"height": "80vh", "width": "80vw"}),
        style={"display": "flex", "justifyContent": "center", "alignItems": "center", "padding": "20px"},
    )


def create_product_content(
    data: pd.DataFrame,
    years: list[int],
    countries: list[str],
    hs_level: str,
    labels: dict[str, str],
) -> html.Div:
    """Render the top products chart for the selected HS level."""

    if data.empty:
        empty_fig = go.Figure()
        empty_fig.update_layout(title=labels["graph_product_title"].format(
            countries=format_country_label(countries, labels),
            period=format_year_period(years, labels),
        ))
        return dcc.Graph(id="product_graph", figure=empty_fig)

    hs_info = HS_LEVEL_CONFIG[hs_level]
    product_ranking = data.groupby([hs_info["code"], "Flow", hs_info["description"]])["chf_num"].sum().reset_index()
    totals = product_ranking.groupby(hs_info["code"])["chf_num"].sum().reset_index()
    totals["chf_num"] = pd.to_numeric(totals["chf_num"], errors="coerce")
    totals = totals[totals["chf_num"] >= TREEMAP_MIN_VALUE]
    top_products = totals.sort_values("chf_num", ascending=False).head(TOP_PRODUCT_LIMIT)[hs_info["code"]]
    product_ranking = product_ranking[product_ranking[hs_info["code"]].isin(top_products)]

    product_ranking["hs_label"] = product_ranking[hs_info["code"]] + " – " + product_ranking[hs_info["description"]]
    product_ranking["hs_wrapped"] = product_ranking["hs_label"].apply(lambda value: value if len(value) <= 80 else value[:80] + "…")
    product_ranking["CHF_label"] = product_ranking["chf_num"].apply(human_format)

    period_label = format_year_period(years, labels)
    country_label = format_country_label(countries, labels)
    fig = px.bar(
        product_ranking,
        x="chf_num",
        y="hs_wrapped",
        color="Flow",
        orientation="h",
        text="CHF_label",
        template=GRAPH_STYLE["template"],
        title=labels["graph_product_title"].format(countries=country_label, period=period_label),
        color_discrete_map={"Export": GRAPH_STYLE["color_export"], "Import": GRAPH_STYLE["color_import"]},
        custom_data=[hs_info["code"], hs_info["description"]],
    )

    fig.update_traces(
        textposition="outside",
        insidetextanchor="start",
        hovertemplate=(
            f"<b>{labels['hover_tariff_code']}:</b> %{{customdata[0]}}<br>"
            f"<b>{labels['hover_description']}:</b> %{{customdata[1]}}<br>"
            f"<b>{labels['hover_flow']}:</b> %{{fullData.name}}<br>"
            f"<b>{labels['hover_chf']}:</b> %{{text}}<extra></extra>"
        ),
    )

    fig.update_layout(yaxis={"categoryorder": "total ascending"}, margin={"l": 400, "r": 80, "t": 80, "b": 80})
    fig = apply_standard_layout(
        fig,
        labels,
        x_title=labels["axis_chf"],
        y_title=labels["axis_product"],
        legend="horizontal",
        height=900,
        legend_title=labels["legend_flow"],
    )

    return html.Div(
        dcc.Graph(id="product_graph", figure=fig, style={"height": "80vh", "width": "80vw"}),
        style={"display": "flex", "justifyContent": "center", "alignItems": "center", "padding": "20px"},
    )


def create_country_products_layout(labels: dict[str, str]) -> html.Div:
    """Return the layout for the country-products tab."""

    options = [
        {"label": labels["top_n_template"].format(n=n), "value": str(n)}
        for n in [5, 10, 20, 25, 50, 100]
    ]

    filter_row = html.Div(
        [
            html.Label(labels["label_top_products"], id="top_products_label", style={
                "marginLeft": "20px",
                "fontFamily": "Arial",
                "lineHeight": "40px",
                "fontWeight": "bold",
            }),
            dmc.Select(
                id="country_products_topn",
                data=options,
                value=DEFAULT_COUNTRY_PRODUCTS_TOP,
                clearable=False,
                # Persist the user choice to avoid losing it when translations reload the layout.
                persistence=True,
                persistence_type="session",
                style={"width": 150},
            ),
        ],
        style={"margin": "20px", "display": "flex", "alignItems": "center", "gap": "15px"},
    )

    return html.Div([
        filter_row,
        html.Div(
            id="country_products_output",
            style={"display": "flex", "flexDirection": "column", "gap": "30px"},
        ),
    ])


def create_sankey_content(data: pd.DataFrame, hs_level: str, labels: dict[str, str]) -> html.Div:
    """Render Sankey diagram linking flow, country and product."""

    if data.empty:
        empty_fig = go.Figure()
        empty_fig.update_layout(title=labels["sankey_title"])
        return dcc.Graph(id="sankey_graph", figure=empty_fig)

    hs_info = HS_LEVEL_CONFIG[hs_level]
    sankey = data.groupby(["Flow", "country_en", hs_info["code"], hs_info["label"]])["chf_num"].sum().reset_index()

    nodes = list(sankey["Flow"].unique()) + list(sankey["country_en"].unique()) + list(sankey[hs_info["code"]].unique())
    node_map = {name: index for index, name in enumerate(nodes)}

    sources: list[int] = []
    targets: list[int] = []
    values: list[float] = []
    customdata: list[str] = []

    for _, row in sankey.iterrows():
        sources.append(node_map[row["Flow"]])
        targets.append(node_map[row["country_en"]])
        values.append(row["chf_num"])
        customdata.append(
            f"{row['Flow']} → {row['country_en']}<br>{labels['hover_chf']}: {row['chf_num']:,.0f}"
        )

        sources.append(node_map[row["country_en"]])
        targets.append(node_map[row[hs_info["code"]]])
        values.append(row["chf_num"])
        customdata.append(
            f"{row['country_en']} → {row[hs_info['label']]}<br>{labels['hover_chf']}: {row['chf_num']:,.0f}"
        )

    fig = go.Figure(
        data=[
            go.Sankey(
                node={
                    "pad": 20,
                    "thickness": 20,
                    "line": {"color": "black", "width": 0.5},
                    "label": nodes,
                    "color": "lightblue",
                },
                link={
                    "source": sources,
                    "target": targets,
                    "value": values,
                    "customdata": customdata,
                    "hovertemplate": "%{customdata}<extra></extra>",
                    "color": "rgba(0,100,200,0.3)",
                },
            )
        ]
    )

    fig.update_layout(title=labels["sankey_title"], font={"size": 14, "family": "Arial"})

    return html.Div(
        dcc.Graph(id="sankey_graph", figure=fig, style={"height": "90vh", "width": "90vw"}),
        style={"display": "flex", "justifyContent": "center", "alignItems": "center", "padding": "20px"},
    )


def create_treemap_content(data: pd.DataFrame, labels: dict[str, str]) -> html.Div:
    """Render treemap summarising top product per country and flow."""

    if data.empty:
        empty_fig = go.Figure()
        empty_fig.update_layout(title=labels["graph_treemap_title"])
        return dcc.Graph(id="treemap_graph", figure=empty_fig)

    treemap = data.groupby(["Flow", "country_en", "HS6_Description"])["chf_num"].sum().reset_index()

    top_countries = (
        treemap.groupby("country_en")["chf_num"].sum().reset_index().sort_values("chf_num", ascending=False)
    ).head(TREEMAP_TOP_COUNTRIES)["country_en"]
    treemap = treemap[treemap["country_en"].isin(top_countries)]

    frames = []
    for (flow, country), group in treemap.groupby(["Flow", "country_en"]):
        if group.empty:
            continue
        best = group.nlargest(1, "chf_num")
        rest_sum = group["chf_num"].sum() - best["chf_num"].iloc[0]
        rest = pd.DataFrame(
            [{"Flow": flow, "country_en": country, "HS6_Description": labels["treemap_other"], "chf_num": rest_sum}]
        )
        frames.append(pd.concat([best, rest], ignore_index=True))

    treemap_top = pd.concat(frames, ignore_index=True)
    treemap_top["HS6_wrapped"] = treemap_top["HS6_Description"].apply(lambda value: wrap_text(value, width=40))

    fig = px.treemap(
        treemap_top,
        path=["Flow", "country_en", "HS6_wrapped"],
        values="chf_num",
        color="Flow",
        color_discrete_map={"Export": GRAPH_STYLE["color_export"], "Import": GRAPH_STYLE["color_import"]},
        title=labels["graph_treemap_title"],
    )

    fig.update_traces(
        customdata=treemap_top[["Flow", "country_en"]].values,
        hovertemplate=(
            f"<b>{labels['treemap_hover_flow']}:</b> %{{customdata[0]}}<br>"
            f"<b>{labels['treemap_hover_country']}:</b> %{{customdata[1]}}<br>"
            f"<b>{labels['treemap_hover_product']}:</b> %{{label}}<br>"
            f"<b>{labels['treemap_hover_value']}:</b> %{{value:,.0f}}<extra></extra>"
        ),
    )

    fig = apply_standard_layout(fig, labels, legend="vertical", height=900)
    fig.update_layout(uniformtext={"minsize": 14, "mode": "show"})

    return dcc.Graph(id="treemap_graph", figure=fig, style={"height": "100vh"})


def build_tab_content(
    tab: str,
    *,
    filtered_all_years: pd.DataFrame,
    filtered_years: pd.DataFrame,
    years: list[int],
    countries: list[str],
    hs_level: str,
    labels: dict[str, str],
) -> html.Div:
    """Dispatch helper for the selected tab."""

    if tab == "trend":
        return create_trend_content(filtered_all_years, countries, labels)

    if tab == "country":
        return create_country_content(filtered_years, years, labels)

    if tab == "product":
        return create_product_content(filtered_years, years, countries, hs_level, labels)

    if tab == "country_products":
        return create_country_products_layout(labels)

    if tab == "treemap_hs":
        return create_treemap_content(filtered_years, labels)

    if tab == "sankey":
        return create_sankey_content(filtered_years, hs_level, labels)

    if tab == "trend_hs":
        return html.Div([
            html.Div(
                [
                    html.Label(labels["label_hs_level_trend"], style={
                        "marginLeft": "20px",
                        "fontFamily": "Arial",
                        "lineHeight": "40px",
                        "fontWeight": "bold",
                    }),
                    dmc.Select(
                        id="hs_level_trend",
                        data=labels["hs_level_trend_options"],
                        value="HS2_Description",
                        clearable=False,
                        persistence=True,
                        persistence_type="session",
                        style={"width": 200},
                    ),
                ],
                style={"margin": "20px", "display": "flex", "alignItems": "center", "gap": "15px"},
            ),
            html.Div(id="trend_hs_content"),
        ])

    return html.Div()


# =========================
# Layout
# =========================
def create_layout(default_labels: dict[str, str]) -> dmc.MantineProvider:
    """Construct the root layout for the Dash app."""

    year_options = [
        {"label": str(int(year)), "value": str(int(year))}
        for year in sorted(df["year"].dropna().unique())
    ]

    country_options = [
        {"label": country, "value": country}
        for country in sorted(df["country_en"].unique())
    ]

    return dmc.MantineProvider(
        theme={"fontFamily": "Arial, sans-serif", "primaryColor": "red"},
        children=[
            html.Div(
                [
                    html.Div(
                        [
                            html.H1(
                                default_labels["header_title"],
                                id="app_title",
                                style={
                                    "margin": "0",
                                    "fontFamily": "Arial, sans-serif",
                                    "fontSize": "48px",
                                    "fontWeight": "bold",
                                    "background": "linear-gradient(90deg, #D52B1E, #022B7E)",
                                    "WebkitBackgroundClip": "text",
                                    "WebkitTextFillColor": "transparent",
                                    "textAlign": "center",
                                    "letterSpacing": "2px",
                                },
                            ),
                            html.H3(
                                default_labels["header_subtitle"],
                                id="app_subtitle",
                                style={
                                    "marginTop": "10px",
                                    "color": "#555",
                                    "fontFamily": "Arial, sans-serif",
                                    "fontSize": "22px",
                                    "fontStyle": "italic",
                                    "textAlign": "center",
                                    "letterSpacing": "1px",
                                },
                            ),
                        ],
                        style={
                            "textAlign": "center",
                            "marginBottom": "40px",
                            "padding": "20px",
                            "borderRadius": "12px",
                            "background": "linear-gradient(145deg, #f9f9f9, #e8eef7)",
                            "boxShadow": "4px 6px 15px rgba(0,0,0,0.15)",
                        },
                    ),
                    html.Div(
                        [
                            html.Div(
                                [
                                    html.Label("", id="lang_label", style={"fontWeight": "bold"}),
                                    dmc.Select(
                                        id="language",
                                        data=default_labels["language_options"],
                                        value=DEFAULT_LANG,
                                        clearable=False,
                                        required=True,
                                        style={"width": 180},
                                    ),
                                ],
                                style={"marginBottom": "20px"},
                            ),
                            html.Div(
                                [
                                    html.Label("", id="year_label", style={"fontWeight": "bold"}),
                                    dmc.MultiSelect(
                                        id="year",
                                        data=year_options,
                                        value=[str(int(df["year"].max()))],
                                        searchable=True,
                                        clearable=True,
                                        style={"width": 250},
                                    ),
                                ],
                                style={"display": "flex", "flexDirection": "column"},
                            ),
                            html.Div(
                                [
                                    html.Label("", id="country_label", style={"fontWeight": "bold"}),
                                    dmc.MultiSelect(
                                        id="country",
                                        data=country_options,
                                        searchable=True,
                                        clearable=True,
                                        style={"width": 300},
                                    ),
                                ],
                                style={"display": "flex", "flexDirection": "column"},
                            ),
                            html.Div(
                                [
                                    html.Label("", id="hs_level_label", style={"fontWeight": "bold"}),
                                    dmc.Select(
                                        id="hs_level",
                                        data=default_labels["hs_level_options"],
                                        value=DEFAULT_HS_LEVEL,
                                        clearable=False,
                                        required=True,
                                        style={"width": 280},
                                    ),
                                ],
                                style={"display": "flex", "flexDirection": "column"},
                            ),
                            html.Div(
                                [
                                    html.Label("", id="product_label", style={"fontWeight": "bold"}),
                                    dmc.MultiSelect(
                                        id="product",
                                        data=[],
                                        searchable=True,
                                        clearable=True,
                                        nothingFoundMessage=default_labels["nothing_found"],
                                        maxDropdownHeight=500,
                                        style={"width": "100%", "fontFamily": "Arial", "fontSize": "16px"},
                                    ),
                                ],
                                style={"flex": 1, "display": "flex", "flexDirection": "column"},
                            ),
                        ],
                        style={"display": "flex", "gap": "20px", "marginBottom": "20px", "width": "100%"},
                    ),
                    html.Div(id="kpis", style={"display": "flex", "justifyContent": "space-between", "marginBottom": "20px", "fontFamily": "Arial"}),
                    dcc.Tabs(
                        id="tabs",
                        value=DEFAULT_TAB,
                        children=[
                            dcc.Tab(label=default_labels["tab_trend"], value="trend"),
                            dcc.Tab(label=default_labels["tab_country"], value="country"),
                            dcc.Tab(label=default_labels["tab_product"], value="product"),
                            dcc.Tab(label=default_labels["tab_country_products"], value="country_products"),
                            dcc.Tab(label=default_labels["tab_trend_hs"], value="trend_hs"),
                            dcc.Tab(label=default_labels["tab_treemap"], value="treemap_hs"),
                            dcc.Tab(label=default_labels["tab_sankey"], value="sankey"),
                        ],
                        persistence=True,
                        persistence_type="session",
                        style={"fontFamily": "Arial"},
                    ),
                    html.Div(id="tabs-content", style={"fontFamily": "Arial"}),
                    html.Div(
                        default_labels["footer_text"],
                        id="footer_text",
                        style={"textAlign": "center", "marginTop": "40px", "color": "gray", "fontSize": "12px", "fontFamily": "Arial"},
                    ),
                ]
            )
        ],
    )


# =========================
# Dash application
# =========================
app = Dash(__name__, suppress_callback_exceptions=True, external_stylesheets=[dbc.themes.BOOTSTRAP])
server = app.server
app.layout = create_layout(get_labels(DEFAULT_LANG))


# =========================
# Callbacks
# =========================
@app.callback(
    [Output("kpis", "children"), Output("tabs-content", "children")],
    [Input("year", "value"), Input("country", "value"), Input("hs_level", "value"), Input("product", "value"), Input("tabs", "value"), Input("language", "value")],
)
def update_dashboard(year, country, hs_level, product, tab, lang):
    """Update KPI cards and the active tab content."""

    labels = get_labels(lang)
    hs_level = sanitise_hs_level(hs_level)
    years = [int(y) for y in ensure_list(year)]
    countries = ensure_list(country)
    products = ensure_list(product)

    filtered_all_years = filter_dataframe(
        df,
        years=[],
        countries=countries,
        hs_level=hs_level,
        products=products,
    )
    if years:
        filtered_years = filter_dataframe(
            df,
            years=years,
            countries=countries,
            hs_level=hs_level,
            products=products,
        )
    else:
        # Mirror the original behaviour: when no year is selected, the KPI section shows zeroes.
        filtered_years = filtered_all_years.iloc[0:0].copy()

    kpi_section = build_kpi_cards(filtered_years, years, labels)
    content = build_tab_content(
        tab,
        filtered_all_years=filtered_all_years,
        filtered_years=filtered_years,
        years=years,
        countries=countries,
        hs_level=hs_level,
        labels=labels,
    )

    return kpi_section, content


@app.callback(Output("product", "data"), Input("hs_level", "value"))
def update_product_options(hs_level):
    """Update product options when the HS level changes."""

    hs_level = sanitise_hs_level(hs_level)
    hs_info = HS_LEVEL_CONFIG[hs_level]
    df_temp = df[[hs_info["code"], hs_info["label"]]].drop_duplicates().sort_values(hs_info["code"])
    return [{"label": row[hs_info["label"]], "value": row[hs_info["code"]]} for _, row in df_temp.iterrows()]


@app.callback(Output("tabs", "children"), Input("language", "value"))
def update_tabs(lang):
    """Translate tab captions dynamically."""

    labels = get_labels(lang)
    return [
        dcc.Tab(label=labels["tab_trend"], value="trend"),
        dcc.Tab(label=labels["tab_country"], value="country"),
        dcc.Tab(label=labels["tab_product"], value="product"),
        dcc.Tab(label=labels["tab_country_products"], value="country_products"),
        dcc.Tab(label=labels["tab_trend_hs"], value="trend_hs"),
        dcc.Tab(label=labels["tab_treemap"], value="treemap_hs"),
        dcc.Tab(label=labels["tab_sankey"], value="sankey"),
    ]


@app.callback(
    [
        Output("lang_label", "children"),
        Output("year_label", "children"),
        Output("country_label", "children"),
        Output("hs_level_label", "children"),
        Output("product_label", "children"),
        Output("app_title", "children"),
        Output("app_subtitle", "children"),
        Output("footer_text", "children"),
        Output("language", "data"),
        Output("hs_level", "data"),
        Output("product", "nothingFoundMessage"),
    ],
    Input("language", "value"),
)
def update_texts(lang):
    """Translate all static labels and select options."""

    labels = get_labels(lang)
    return (
        labels["label_language"],
        labels["label_year"],
        labels["label_country"],
        labels["label_hs_level"],
        labels["label_description"],
        labels["header_title"],
        labels["header_subtitle"],
        labels["footer_text"],
        labels["language_options"],
        labels["hs_level_options"],
        labels["nothing_found"],
    )


@app.callback(
    Output("country_products_output", "children"),
    [Input("country", "value"), Input("year", "value"), Input("country_products_topn", "value"), Input("language", "value")],
)
def update_country_products(selected_countries, years, top_n, lang):
    """Generate top product charts per country and flow."""

    labels = get_labels(lang)
    years_list = [int(year) for year in ensure_list(years)]
    if not years_list:
        # Use full range when nothing is selected to avoid empty results.
        years_list = sorted(df["year"].dropna().unique().astype(int))

    filtered = df[df["year"].isin(years_list)].copy()
    filtered = filtered[filtered["chf_num"] > 0]

    data = filtered.groupby(["country_en", "Flow", "HS6_Description"])["chf_num"].sum().reset_index()
    countries = ensure_list(selected_countries) or sorted(data["country_en"].unique())
    if not countries:
        return html.Div(labels["country_products_no_data"], style={"padding": "20px"})

    rows = []
    top_n_int = int(top_n) if top_n else int(DEFAULT_COUNTRY_PRODUCTS_TOP)
    period_label = format_year_period(years_list, labels)

    for country in countries:
        country_rows = []
        for flow, flow_label in [("Export", labels["flow_export"]), ("Import", labels["flow_import"])]:
            subset = data[(data["country_en"] == country) & (data["Flow"] == flow)].nlargest(top_n_int, "chf_num")
            if subset.empty:
                graph = html.Div(labels["country_products_no_data"], style={"padding": "20px"})
            else:
                subset["HS6_wrapped"] = subset["HS6_Description"].apply(lambda value: wrap_and_shorten(value, 30, 60))
                fig = px.bar(
                    subset,
                    x="chf_num",
                    y="HS6_wrapped",
                    orientation="h",
                    title=labels["graph_country_products_title"].format(
                        n=top_n_int,
                        flow_label=flow_label,
                        country=country,
                        period=period_label,
                    ),
                    template=GRAPH_STYLE["template"],
                    color_discrete_sequence=[
                        GRAPH_STYLE["color_export"] if flow == "Export" else GRAPH_STYLE["color_import"]
                    ],
                    text=subset["chf_num"].apply(human_format),
                )
                fig.update_traces(
                    textposition="outside",
                    insidetextanchor="start",
                    cliponaxis=False,
                    hovertemplate=(
                        f"<b>{labels['hover_product']}:</b> %{{y}}<br>"
                        f"<b>{labels['hover_chf']}:</b> %{{text}}<extra></extra>"
                    ),
                )
                fig.update_layout(
                    yaxis={"categoryorder": "total ascending", "title": labels["axis_product"]},
                    xaxis={"title": labels["axis_chf"]},
                    margin={"l": 250, "r": 50, "t": 80, "b": 50},
                )
                height = max(450, len(subset) * 40)
                fig = apply_standard_layout(fig, labels, legend=False, height=height)
                graph = dcc.Graph(figure=fig)

            country_rows.append(graph)

        row = html.Div(
            [
                html.Div(
                    html.H4(country, style={"textAlign": "left", "fontSize": "20px"}),
                    style={"flex": "0 0 220px", "padding": "10px"},
                ),
                html.Div(country_rows[0], style={"flex": "2", "padding": "20px"}),
                html.Div(country_rows[1], style={"flex": "2", "padding": "20px"}),
            ],
            style={"display": "flex", "gap": "10px", "margin": "50px"},
        )
        rows.append(row)

    return html.Div(rows, style={"display": "flex", "flexDirection": "column", "gap": "30px"})


@app.callback(Output("trend_hs_content", "children"), [Input("country", "value"), Input("hs_level_trend", "value"), Input("language", "value")])
def update_trend_hs(countries, hs_level, lang):
    """Render export and import trend charts for the HS trend tab."""

    labels = get_labels(lang)
    hs_level = sanitise_hs_level(hs_level)
    hs_info = HS_LEVEL_CONFIG[hs_level]

    all_years = df["year"].dropna().astype(int)
    min_year, max_year = int(all_years.min()), int(all_years.max())
    filtered = df[(df["year"] >= min_year) & (df["year"] <= max_year)].copy()

    country_list = ensure_list(countries)
    if country_list:
        filtered = filtered[filtered["country_en"].isin(country_list)]

    trend = filtered.groupby(["year", hs_level, "Flow"])["chf_num"].sum().reset_index()

    def shorten(value: str, max_len: int = 50) -> str:
        if not isinstance(value, str):
            return ""
        return value if len(value) <= max_len else value[:max_len] + "…"

    trend["hs_label"] = trend[hs_level].apply(shorten)
    period_label = labels["year_range"].format(start=min_year, end=max_year)
    hs_label = next(
        (option["label"] for option in labels["hs_level_trend_options"] if option["value"] == hs_level),
        hs_info["label"].split("_")[0],
    )

    figures = []
    for flow, flow_label in [("Export", labels["flow_export"]), ("Import", labels["flow_import"])]:
        subset = trend[trend["Flow"] == flow]
        fig = px.line(
            subset,
            x="year",
            y="chf_num",
            color="hs_label",
            line_group="hs_label",
            markers=True,
            template=GRAPH_STYLE["template"],
            title=(
                labels["graph_trend_hs_export_title"]
                if flow == "Export"
                else labels["graph_trend_hs_import_title"]
            ).format(hs_label=hs_label, period=period_label),
        )
        fig.update_traces(
            marker={"size": 10},
            hovertemplate=(
                f"<b>{labels['hover_year']}:</b> %{{x}}<br>"
                f"<b>{labels['hover_description']}:</b> %{{fullData.name}}<br>"
                f"<b>{labels['hover_chf']}:</b> %{{y:,.0f}}<extra></extra>"
            ),
        )
        fig = apply_standard_layout(
            fig,
            labels,
            x_title=labels["axis_year"],
            y_title=labels["axis_chf"],
            legend="bottom_outside",
            height=900,
        )
        figures.append(dcc.Graph(figure=fig))

    return html.Div(figures, style={"display": "flex", "gap": "20px", "padding": "20px"})


# =========================
# App runner
# =========================
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8050))
    app.run(host="0.0.0.0", port=port, debug=True)
