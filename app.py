"""Swiss Trade Dashboard refactored for performance and clarity."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Iterable, List, Sequence, Tuple

import pandas as pd
import plotly.graph_objects as go
from dash import Dash, Input, Output, dcc, html
import dash_bootstrap_components as dbc
import dash_mantine_components as dmc
from flask_caching import Cache

from translations import LANG


# =============================================================
# Data loading & preparation
# =============================================================

DATA_FILE = "trade_subset_latam.csv.gz"

USE_COLUMNS = [
    "tn_key",
    "year",
    "traffic",
    "chf_num",
    "country_en",
    "HS2_Description",
    "HS4_Description",
    "HS6_Description",
    "HS8_Description",
]

DTYPES = {
    "tn_key": "string",
    "year": "Int16",
    "traffic": "category",
    "chf_num": "float32",
    "country_en": "category",
    "HS2_Description": "category",
    "HS4_Description": "category",
    "HS6_Description": "category",
    "HS8_Description": "category",
}


df = pd.read_csv(
    DATA_FILE,
    sep=";",
    usecols=USE_COLUMNS,
    dtype=DTYPES,
    encoding="utf-8",
    compression="gzip",
)

df["year"] = df["year"].astype("Int16")
df["chf_num"] = df["chf_num"].fillna(0).astype("float32")

FLOW_MAP = {"EXP": "Export", "IMP": "Import"}
df["Flow"] = df["traffic"].map(FLOW_MAP)
df["Flow"] = df["Flow"].astype("string").fillna("Other")


def _format_code(series: pd.Series, length: int) -> pd.Series:
    """Normalise product codes by keeping digits only and padding."""
    return (
        series.astype("string")
        .str.replace(r"[^0-9]", "", regex=True)
        .str.zfill(length)
    )


df["HS2"] = _format_code(df["tn_key"], 8).str[:2]
df["HS4"] = _format_code(df["tn_key"], 8).str[:4]
df["HS6"] = _format_code(df["tn_key"], 8).str[:6]
df["HS8"] = _format_code(df["tn_key"], 8).str[:8]


df["HS2_Label"] = df["HS2"] + " – " + df["HS2_Description"].astype("string")
df["HS4_Label"] = (
    df["HS4"].str[:2] + df["HS4"].str[2:] + " – " + df["HS4_Description"].astype("string")
)
df["HS6_Label"] = (
    df["HS6"].str[:4] + "." + df["HS6"].str[4:] + " – " + df["HS6_Description"].astype("string")
)
df["HS8_Label"] = (
    df["HS8"].str[:4] + "." + df["HS8"].str[4:] + " – " + df["HS8_Description"].astype("string")
)

ALL_YEARS = pd.RangeIndex(df["year"].min(), df["year"].max() + 1)

DEFAULT_HS_LEVEL = "HS6_Description"

HS_LEVEL_CONFIG = {
    "HS2_Description": {"code": "HS2", "label": "HS2_Label", "display": "HS2"},
    "HS4_Description": {"code": "HS4", "label": "HS4_Label", "display": "HS4"},
    "HS6_Description": {"code": "HS6", "label": "HS6_Label", "display": "HS6"},
    "HS8_Description": {"code": "HS8", "label": "HS8_Label", "display": "HS8"},
}

PRODUCT_OPTIONS: Dict[str, List[dict]] = {}
for level, cfg in HS_LEVEL_CONFIG.items():
    option_df = (
        df[[cfg["code"], cfg["label"]]]
        .dropna()
        .drop_duplicates()
        .sort_values(cfg["label"])
    )
    PRODUCT_OPTIONS[level] = [
        {"label": str(label), "value": str(code)}
        for code, label in zip(option_df[cfg["code"]], option_df[cfg["label"]])
    ]

COLOR_EXPORT = "#00c08d"
COLOR_IMPORT = "#e6301f"
COLOR_BALANCE = "#022B7E"

GRAPH_TEMPLATE = "plotly_white"


# =============================================================
# App initialisation & caching
# =============================================================

app = Dash(
    __name__,
    external_stylesheets=[dbc.themes.BOOTSTRAP],
    suppress_callback_exceptions=True,
)
server = app.server

cache = Cache(
    app.server,
    config={
        "CACHE_TYPE": "simple",
        "CACHE_DEFAULT_TIMEOUT": 300,
    },
)


# =============================================================
# Helper utilities
# =============================================================


def _normalise_tuple(values: Iterable | None, cast=int) -> Tuple:
    if not values:
        return tuple()
    cleaned = []
    for value in values:
        if value is None:
            continue
        try:
            cleaned.append(cast(value))
        except (ValueError, TypeError):
            continue
    return tuple(sorted(dict.fromkeys(cleaned)))


def _normalise_text_tuple(values: Iterable | None) -> Tuple[str, ...]:
    if not values:
        return tuple()
    cleaned = [str(v) for v in values if v not in (None, "")]
    return tuple(sorted(dict.fromkeys(cleaned)))


def _ensure_hs_level(value: str | None) -> str:
    if value in HS_LEVEL_CONFIG:
        return value
    return DEFAULT_HS_LEVEL


def _format_currency(value: float) -> str:
    rounded = float(value) if value is not None else 0.0
    return f"CHF {rounded:,.0f}".replace(",", "'")


def _format_year_label(years: Sequence[int]) -> str:
    if not years:
        return "All years"
    if len(years) == 1:
        return str(years[0])
    return f"{min(years)}–{max(years)}"


def _build_options(series: pd.Series) -> List[dict]:
    return (
        series.dropna()
        .drop_duplicates()
        .sort_values()
        .apply(lambda val: {"label": val, "value": val})
        .tolist()
    )


def filter_dataframe(
    years: Tuple[int, ...],
    countries: Tuple[str, ...],
    hs_level: str,
    products: Tuple[str, ...],
) -> pd.DataFrame:
    dff = df

    if years:
        dff = dff[dff["year"].isin(years)]
    if countries:
        dff = dff[dff["country_en"].isin(countries)]
    if products:
        code_col = HS_LEVEL_CONFIG[hs_level]["code"]
        dff = dff[dff[code_col].isin(products)]

    return dff


@dataclass(frozen=True)
class MetricResult:
    kpis: dict
    trend: list
    country: list
    product: list
    hs_level: str
    years_label: str


@cache.memoize(timeout=300)
def compute_metrics(
    years: Tuple[int, ...],
    countries: Tuple[str, ...],
    hs_level: str,
    products: Tuple[str, ...],
) -> MetricResult:
    dff = filter_dataframe(years, countries, hs_level, products)

    if dff.empty:
        empty_records = []
        for year in ALL_YEARS:
            empty_records.extend(
                [
                    {"year": year, "Flow": "Export", "CHF": 0.0},
                    {"year": year, "Flow": "Import", "CHF": 0.0},
                    {"year": year, "Flow": "Balance", "CHF": 0.0},
                ]
            )
        return MetricResult(
            kpis={
                "exports": 0.0,
                "imports": 0.0,
                "balance": 0.0,
                "volume": 0.0,
            },
            trend=empty_records,
            country=[],
            product=[],
            hs_level=hs_level,
            years_label=_format_year_label(years),
        )

    grouped = (
        dff.groupby(["year", "Flow"], observed=True)["chf_num"].sum().astype("float64")
    )
    pivot = grouped.unstack(fill_value=0.0).reindex(ALL_YEARS, fill_value=0.0)
    for flow_name in ("Export", "Import"):
        if flow_name not in pivot.columns:
            pivot[flow_name] = 0.0
    pivot["Balance"] = pivot["Export"] - pivot["Import"]

    trend_df = (
        pivot.reset_index()
        .melt(id_vars="year", value_vars=["Export", "Import", "Balance"], var_name="Flow", value_name="CHF")
    )

    kpi_exports = float(pivot["Export"].sum())
    kpi_imports = float(pivot["Import"].sum())
    kpi_balance = float(pivot["Balance"].sum())
    kpi_volume = kpi_exports + kpi_imports

    country_df = (
        dff.groupby(["country_en", "Flow"], observed=True)["chf_num"].sum().reset_index()
    )
    country_df["country_en"] = country_df["country_en"].astype("string")
    country_df = country_df.sort_values("chf_num", ascending=False).head(15)

    label_col = HS_LEVEL_CONFIG[hs_level]["label"]
    product_df = (
        dff.groupby([label_col, "Flow"], observed=True)["chf_num"].sum().reset_index()
    )
    product_df[label_col] = product_df[label_col].astype("string")
    product_df = product_df.sort_values("chf_num", ascending=False).head(15)

    return MetricResult(
        kpis={
            "exports": kpi_exports,
            "imports": kpi_imports,
            "balance": kpi_balance,
            "volume": kpi_volume,
        },
        trend=trend_df.to_dict("records"),
        country=country_df.to_dict("records"),
        product=product_df.to_dict("records"),
        hs_level=hs_level,
        years_label=_format_year_label(years),
    )


def build_trend_figure(records: list) -> go.Figure:
    trend_df = pd.DataFrame(records)
    fig = go.Figure()

    for flow_name, color in [
        ("Export", COLOR_EXPORT),
        ("Import", COLOR_IMPORT),
        ("Balance", COLOR_BALANCE),
    ]:
        flow_df = trend_df[trend_df["Flow"] == flow_name]
        if flow_df.empty:
            continue
        hover_template = (
            "<b>Year:</b> %{x}<br>"
            + (
                "<b>Flow:</b> %{fullData.name}<br><b>CHF:</b> %{y:,.0f}<extra></extra>"
                if flow_name != "Balance"
                else "<b>Balance:</b> %{y:,.0f}<extra></extra>"
            )
        )
        fig.add_trace(
            go.Scatter(
                x=flow_df["year"],
                y=flow_df["CHF"],
                mode="lines+markers",
                name=flow_name,
                line=dict(color=color, width=3),
                marker=dict(size=8),
                hovertemplate=hover_template,
            )
        )

    fig.update_layout(
        template=GRAPH_TEMPLATE,
        margin=dict(l=40, r=40, t=40, b=40),
        legend=dict(orientation="h", y=-0.2, x=0.5, xanchor="center"),
        hovermode="x unified",
        yaxis_title="CHF",
        xaxis_title="Year",
    )
    fig.update_xaxes(range=[ALL_YEARS.start, ALL_YEARS.stop - 1])
    fig.update_yaxes(tickprefix="CHF ")
    return fig


def build_bar_figure(records: list, category_column: str, category_label: str) -> go.Figure:
    if not records:
        return go.Figure()
    df_bar = pd.DataFrame(records)
    df_bar = df_bar.sort_values("chf_num", ascending=True)

    fig = go.Figure()
    for flow_name, color in [("Export", COLOR_EXPORT), ("Import", COLOR_IMPORT)]:
        subset = df_bar[df_bar["Flow"] == flow_name]
        if subset.empty:
            continue
        fig.add_trace(
            go.Bar(
                y=subset[category_column],
                x=subset["chf_num"],
                name=flow_name,
                orientation="h",
                marker_color=color,
                hovertemplate=(
                    f"<b>{category_label}:</b> %{{y}}<br>"
                    "<b>Flow:</b> %{fullData.name}<br>"
                    "<b>CHF:</b> %{x:,.0f}<extra></extra>"
                ),
            )
        )

    fig.update_layout(
        barmode="group",
        template=GRAPH_TEMPLATE,
        margin=dict(l=40, r=40, t=40, b=40),
        legend=dict(orientation="h", y=-0.2, x=0.5, xanchor="center"),
        xaxis_title="CHF",
        yaxis_title="",
    )
    return fig


def build_kpi_card(title: str, value: float) -> dbc.Card:
    return dbc.Card(
        dbc.CardBody(
            [
                html.Div(title, className="kpi-title"),
                html.Div(_format_currency(value), className="kpi-value"),
            ]
        ),
        class_name="kpi-card",
    )


# =============================================================
# Layout configuration
# =============================================================

app.layout = dmc.MantineProvider(
    theme={"fontFamily": "Arial, sans-serif", "primaryColor": "red"},
    children=[
        html.Div(
            [
                html.Div(
                    [
                        html.H1(
                            "Swiss Trade Insights",
                            className="app-title",
                        ),
                        html.H3(
                            "LATAM",
                            className="app-subtitle",
                            id="subtitle-years",
                        ),
                    ],
                    className="header-container",
                ),
                html.Div(
                    [
                        html.Div(
                            [
                                html.Label(id="lang_label"),
                                dmc.Select(
                                    id="language",
                                    data=[
                                        {"label": "English", "value": "en"},
                                        {"label": "Español", "value": "es"},
                                    ],
                                    value="en",
                                    clearable=False,
                                ),
                            ],
                            className="filter-item",
                        ),
                        html.Div(
                            [
                                html.Label(id="year_label"),
                                dmc.MultiSelect(
                                    id="year",
                                    data=[
                                        {"label": str(year), "value": str(year)}
                                        for year in ALL_YEARS
                                    ],
                                    value=[],
                                    searchable=True,
                                    clearable=True,
                                ),
                            ],
                            className="filter-item",
                        ),
                        html.Div(
                            [
                                html.Label(id="country_label"),
                                dmc.MultiSelect(
                                    id="country",
                                    data=_build_options(df["country_en"].astype("string")),
                                    searchable=True,
                                    clearable=True,
                                ),
                            ],
                            className="filter-item",
                        ),
                        html.Div(
                            [
                                html.Label(id="hs_level_label"),
                                dmc.Select(
                                    id="hs_level",
                                    data=[
                                        {
                                            "label": label,
                                            "value": value,
                                        }
                                        for value, label in [
                                            ("HS2_Description", "2 digit - broad groups"),
                                            ("HS4_Description", "4 digit - groups"),
                                            ("HS6_Description", "6 digit - products"),
                                            ("HS8_Description", "8 digit - detailed products"),
                                        ]
                                    ],
                                    value=DEFAULT_HS_LEVEL,
                                    clearable=False,
                                ),
                            ],
                            className="filter-item",
                        ),
                        html.Div(
                            [
                                html.Label(id="product_label"),
                                dmc.MultiSelect(
                                    id="product",
                                    data=[],
                                    searchable=True,
                                    clearable=True,
                                ),
                            ],
                            className="filter-item",
                        ),
                    ],
                    className="filters-container",
                ),
                html.Div(id="kpi-wrapper", className="kpi-wrapper"),
                dcc.Tabs(
                    id="tabs",
                    className="tabs-container",
                    value="trend",
                    children=[
                        dcc.Tab(
                            label="📈 Trend",
                            value="trend",
                            children=[
                                dcc.Graph(id="trend-graph", className="graph"),
                            ],
                        ),
                        dcc.Tab(
                            label="🌍 Country",
                            value="country",
                            children=[
                                dcc.Graph(id="country-graph", className="graph"),
                            ],
                        ),
                        dcc.Tab(
                            label="📦 Product",
                            value="product",
                            children=[
                                dcc.Graph(id="product-graph", className="graph"),
                            ],
                        ),
                    ],
                ),
            ],
            className="app-container",
        )
    ],
)


# =============================================================
# Callbacks
# =============================================================

@app.callback(
    Output("lang_label", "children"),
    Output("year_label", "children"),
    Output("country_label", "children"),
    Output("hs_level_label", "children"),
    Output("product_label", "children"),
    Input("language", "value"),
)
def update_labels(language: str) -> Tuple[str, str, str, str, str]:
    lang = LANG.get(language or "en", LANG["en"])
    return (
        lang["label_language"],
        lang["label_year"],
        lang["label_country"],
        lang["label_hs_level"],
        lang["label_description"],
    )


@app.callback(
    Output("product", "data"),
    Input("hs_level", "value"),
)
def update_product_options(hs_level: str):
    level = _ensure_hs_level(hs_level)
    return PRODUCT_OPTIONS[level]


@app.callback(
    Output("subtitle-years", "children"),
    Output("kpi-wrapper", "children"),
    Output("trend-graph", "figure"),
    Output("country-graph", "figure"),
    Output("product-graph", "figure"),
    Input("language", "value"),
    Input("year", "value"),
    Input("country", "value"),
    Input("hs_level", "value"),
    Input("product", "value"),
)
def update_dashboard(language, year, country, hs_level, product):
    years = _normalise_tuple(year, cast=int)
    countries = _normalise_text_tuple(country)
    level = _ensure_hs_level(hs_level)
    products = _normalise_text_tuple(product)

    metrics = compute_metrics(years, countries, level, products)

    lang = LANG.get(language or "en", LANG["en"])

    kpi_cards = dbc.Row(
        [
            dbc.Col(build_kpi_card(lang["kpi_exports"], metrics.kpis["exports"]), md=3, xs=12),
            dbc.Col(build_kpi_card(lang["kpi_imports"], metrics.kpis["imports"]), md=3, xs=12),
            dbc.Col(build_kpi_card(lang["kpi_balance"], metrics.kpis["balance"]), md=3, xs=12),
            dbc.Col(build_kpi_card(lang["kpi_volume"], metrics.kpis["volume"]), md=3, xs=12),
        ],
        className="kpi-grid",
        justify="center",
    )

    trend_fig = build_trend_figure(metrics.trend)
    country_fig = build_bar_figure(metrics.country, "country_en", "Country")
    label_col = HS_LEVEL_CONFIG[metrics.hs_level]["label"]
    product_fig = build_bar_figure(metrics.product, label_col, "Product")

    return (
        f"{metrics.years_label}",
        kpi_cards,
        trend_fig,
        country_fig,
        product_fig,
    )


# =============================================================
# Styling
# =============================================================

app.index_string = """
<!DOCTYPE html>
<html>
    <head>
        {%metas%}
        <title>Swiss Trade Dashboard</title>
        {%favicon%}
        {%css%}
        <style>
            body {background-color: #f5f7fb; margin: 0; font-family: 'Arial', sans-serif;}
            .app-container {max-width: 1200px; margin: 0 auto; padding: 20px;}
            .header-container {text-align: center; margin-bottom: 30px;}
            .app-title {font-size: 48px; font-weight: 700; margin: 0; background: linear-gradient(90deg, #D52B1E, #022B7E); -webkit-background-clip: text; -webkit-text-fill-color: transparent;}
            .app-subtitle {margin-top: 10px; color: #555; font-style: italic;}
            .filters-container {display: flex; flex-wrap: wrap; justify-content: center; gap: 20px; width: 90%; margin: 0 auto 30px;}
            .filter-item {min-width: 200px; display: flex; flex-direction: column;}
            .filter-item label {font-weight: 600; margin-bottom: 6px;}
            .kpi-wrapper {width: 90%; margin: 0 auto 30px;}
            .kpi-grid {row-gap: 20px;}
            .kpi-card {box-shadow: 3px 3px 12px rgba(0,0,0,0.15); border-radius: 15px; text-align: center; padding: 20px; background: #fff; min-height: 150px; display: flex; align-items: center; justify-content: center;}
            .kpi-title {font-size: 18px; color: #555;}
            .kpi-value {font-size: 28px; font-weight: 700; margin-top: 5px; color: #022B7E;}
            .tabs-container {width: 90%; margin: 0 auto;}
            .graph {min-height: 500px;}
            @media (max-width: 992px) {.filters-container {width: 100%;} .kpi-wrapper {width: 100%;} .tabs-container {width: 100%;}}
        </style>
    </head>
    <body>
        {%app_entry%}
        <footer>
            {%config%}
            {%scripts%}
            {%renderer%}
        </footer>
    </body>
</html>
"""


# =============================================================
# Main entry
# =============================================================

if __name__ == "__main__":
    app.run(debug=False, host="0.0.0.0", port=8050)
