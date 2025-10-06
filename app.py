# -*- coding: utf-8 -*-
from dash import Dash, dcc, html, Input, Output
import logging
import os
import textwrap
import dash_bootstrap_components as dbc
import dash_mantine_components as dmc
import humanize
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from translations import LANG


# =========================
# Logging configuration
# =========================
LOG_LEVEL = os.environ.get("APP_LOG_LEVEL", "INFO").upper()
logging.basicConfig(
    level=getattr(logging, LOG_LEVEL, logging.INFO),
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
)
LOGGER = logging.getLogger(__name__)

# =========================
# Load data
# =========================
DATA_PATH = os.environ.get("TRADE_DATA_PATH", "trade_subset_latam.csv.gz")
LOGGER.info("Loading trade dataset from %s", DATA_PATH)
df = pd.read_csv(DATA_PATH, sep=";", encoding="utf-8", compression="gzip")

REQUIRED_COLUMNS = {
    "year",
    "chf_num",
    "traffic",
    "country_en",
    "tn_key",
    "HS2_Description",
    "HS4_Description",
    "HS6_Description",
    "HS8_Description",
}
missing_columns = REQUIRED_COLUMNS - set(df.columns)
if missing_columns:
    LOGGER.error("Missing required columns in dataset: %s", ", ".join(sorted(missing_columns)))
    raise ValueError(f"Dataset is missing required columns: {sorted(missing_columns)}")

# Datatypes
df["year"] = pd.to_numeric(df["year"], errors="coerce").astype("Int16")
df["chf_num"] = pd.to_numeric(df["chf_num"], errors="coerce").fillna(0).astype(float)

for col in ["country_en", "HS2_Description", "HS4_Description", "HS6_Description", "HS8_Description", "traffic"]:
    df[col] = df[col].fillna("Unknown").astype(str)

# Flow-Mapping
df["Flow"] = df["traffic"].map({"EXP": "Export", "IMP": "Import"}).fillna(df["traffic"])
LOGGER.info("Dataset loaded with %d rows and %d columns", df.shape[0], df.shape[1])


# Einheitliches tn_key-Format (8-stellig, nur Ziffern)
df["tn_key"] = (
    df["tn_key"]
    .astype(str)
    .str.replace("[^0-9]", "", regex=True)
    .str.zfill(8)
)

# ================================
# HS-Level Dimensionen vorbereiten
# ================================

# HS2
df["HS2"] = df["tn_key"].str[:2]
df["HS2_Label"] = df["HS2"] + " – " + df["HS2_Description"]

# HS4
df["HS4"] = df["tn_key"].str[:4]
df["HS4_Label"] = df["HS4"].str[:2] + df["HS4"].str[2:] + " – " + df["HS4_Description"]

# HS6
df["HS6"] = df["tn_key"].str[:6]
df["HS6_Label"] = (
    df["HS6"].str[:4] + "." + df["HS6"].str[4:] +
    " – " + df["HS6_Description"]
)

# HS8
df["HS8"] = df["tn_key"].str[:8]
df["HS8_Label"] = (
    df["HS8"].str[:4] + "." + df["HS8"].str[4:] +
    " – " + df["HS8_Description"]
)

# Speicher optimieren: kategorische Spalten und kompaktes Jahr-Format
category_columns = [
    "country_en",
    "traffic",
    "Flow",
    "HS2",
    "HS2_Label",
    "HS2_Description",
    "HS4",
    "HS4_Label",
    "HS4_Description",
    "HS6",
    "HS6_Label",
    "HS6_Description",
    "HS8",
    "HS8_Label",
    "HS8_Description",
]
for col in category_columns:
    if col in df.columns:
        df[col] = df[col].astype("category")

LOGGER.debug(
    "HS codes prepared | unique HS2=%d HS4=%d HS6=%d HS8=%d",
    df["HS2"].nunique(dropna=True),
    df["HS4"].nunique(dropna=True),
    df["HS6"].nunique(dropna=True),
    df["HS8"].nunique(dropna=True),
)

# =========================
# Style
# =========================
GRAPH_STYLE = {
    "font_family": "Arial",
    "font_size": 16,
    "title_size": 22,

    # Standardkarten (KPIs)
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
        "height":"220px"
    },

    # Farben
    "color_export": "#00c08d",   # Export
    "color_import": "#e6301f",   # Import
    "color_trade": "#022B7E",    # Balance
    "template": "plotly_white",
    "bg_color_export": "#ecfffa",
    "bg_color_import": "#fef3f2",
    "bg_color_balance": "#b4ccfe",
    "bg_color_trade": "#f0f0f0",

    # Legenden-Layouts
    "legend_horizontal": {
        "orientation": "h",
        "y": -0.25,
        "x": 0.5,
        "xanchor": "center",
        "yanchor": "top",
        "bgcolor": "rgba(255,255,255,0.6)",
        "bordercolor": "lightgray",
        "borderwidth": 1,
        "font": dict(size=14)
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
        "font": dict(size=14)
    },
    "legend_bottom_vertical": {
        "orientation": "v",    # vertikal = untereinander
        "y": -0.3,             # unterhalb der Grafik
        "x": 0,                # links anfangen
        "xanchor": "left",
        "yanchor": "top",
        "bgcolor": "rgba(255,255,255,0.6)",
        "bordercolor": "lightgray",
        "borderwidth": 1,
        "font": dict(size=14),
        "itemsizing": "trace"  # jeder Trace gleich breit dargestellt
    },
    "legend_bottom_full": {
        "orientation": "h",
        "y": -0.25,
        "x": 0,
        "xanchor": "left",
        "yanchor": "top",
        "bgcolor": "rgba(255,255,255,0.6)",
        "bordercolor": "lightgray",
        "borderwidth": 1,
        "font": dict(size=14),
        "itemsizing": "trace"
    }
}

# =========================
# App
# =========================
app = Dash(__name__, suppress_callback_exceptions=True, external_stylesheets=[dbc.themes.BOOTSTRAP])
server = app.server

# =========================
# Hilfsfunktionen
# =========================


def get_filtered_data(year, country, hs_level, product):
    """Gefiltertes DataFrame zurückgeben."""
    year_tuple = tuple(int(y) for y in year) if year else ()
    country_tuple = tuple(country) if country else ()
    product_tuple = tuple(product) if product else ()
    if hs_level and hs_level not in {
        "HS2_Description",
        "HS4_Description",
        "HS6_Description",
        "HS8_Description",
    }:
        LOGGER.warning("Unsupported hs_level '%s' provided. Falling back to HS6_Description", hs_level)
        hs_level = "HS6_Description"

    dff = df
    LOGGER.debug(
        "Filtering data | years=%s countries=%s hs_level=%s product_count=%s",
        year_tuple if year_tuple else "ALL",
        country_tuple if country_tuple else "ALL",
        hs_level,
        len(product_tuple) if product_tuple else 0,
    )

    if country_tuple:
        dff = dff[dff["country_en"].isin(country_tuple)]
        LOGGER.debug("Applied country filter -> %d rows", len(dff))

    if product_tuple:
        hs_column = {
            "HS2_Description": "HS2",
            "HS4_Description": "HS4",
            "HS6_Description": "HS6",
            "HS8_Description": "HS8",
        }.get(hs_level, hs_level)
        if hs_column not in dff.columns:
            LOGGER.error("HS column '%s' not found in dataframe columns", hs_column)
            raise KeyError(f"HS column '{hs_column}' not found")
        dff = dff[dff[hs_column].isin(product_tuple)]
        LOGGER.debug("Applied product filter (%s) -> %d rows", hs_column, len(dff))

    if year_tuple:
        dff = dff[dff["year"].isin(year_tuple)]
        LOGGER.debug("Applied year filter -> %d rows", len(dff))

    LOGGER.debug("Final filtered dataset has %d rows", len(dff))
    return dff


def wrap_and_shorten(text, wrap_width=30, max_len=60):
    if not isinstance(text, str):
        return ""
    # Zuerst kürzen, falls zu lang
    if len(text) > max_len:
        text = text[:max_len] + "…"
    # Danach umbrechen
    return "<br>".join(textwrap.wrap(text, width=wrap_width))


def human_format(num: float) -> str:
    """Zahlen im Stil 1.2 M, 3.4 Bn, etc. formatieren."""
    if num is None or pd.isna(num):
        return "0"
    txt = humanize.intword(num, format="%.1f")
    # Englische Endungen in Kurzformen umwandeln
    return (txt
            .replace(" thousand", "T")
            .replace(" million", "M")
            .replace(" billion", "Bn")
            .replace(" trillion", "Tn"))

def apply_standard_layout(fig, x_title="", y_title="", legend="horizontal", height=1000, legend_title=None):
    show_legend = True
    if legend is False:
        legend_cfg = None
        show_legend = False
    elif legend == "horizontal":
        legend_cfg = GRAPH_STYLE["legend_horizontal"]
    elif legend == "vertical":
        legend_cfg = GRAPH_STYLE["legend_vertical"]
    elif legend == "bottom_outside":
        legend_cfg = GRAPH_STYLE["legend_bottom_vertical"]   # neu
    elif legend == "bottom_full":
        legend_cfg = GRAPH_STYLE["legend_bottom_full"]
    else:
        legend_cfg = None


    fig.update_layout(
        height=height,
        xaxis_title=x_title,
        yaxis_title=y_title,
        font=dict(
            family=GRAPH_STYLE["font_family"],
            size=GRAPH_STYLE["font_size"]
        ),
        title=dict(font=dict(size=GRAPH_STYLE["title_size"])),
        legend=legend_cfg,
        legend_title_text=legend_title if legend_title else None,
        showlegend=show_legend,
        hoverlabel=dict(
            align="left"
        )
    )
    return fig

def build_empty_figure(title: str, message: str) -> go.Figure:
    """Return a placeholder figure with a standard message."""
    fig = go.Figure()
    fig.add_annotation(
        text=message,
        showarrow=False,
        font=dict(size=18),
        x=0.5,
        y=0.5,
        xref="paper",
        yref="paper",
    )
    fig.update_xaxes(visible=False)
    fig.update_yaxes(visible=False)
    fig.update_layout(title=title)
    return apply_standard_layout(fig, legend=False, height=600)


def log_dataframe_snapshot(name: str, frame: pd.DataFrame) -> None:
    """Log standard diagnostics for a dataframe snapshot."""
    if frame.empty:
        LOGGER.warning("%s dataframe is empty after filtering", name)
    else:
        LOGGER.debug(
            "%s dataframe snapshot | rows=%d cols=%d | years=%s-%s",
            name,
            frame.shape[0],
            frame.shape[1],
            frame["year"].min() if "year" in frame.columns else "n/a",
            frame["year"].max() if "year" in frame.columns else "n/a",
        )

# =========================
# App Layout
# =========================
app.layout = dmc.MantineProvider(
    theme={
        "fontFamily": "Arial, sans-serif",
        "primaryColor": "red",   # 🇨🇭 kannst du ändern
    },
    children=[
        html.Div([

            # =========================
            # Header
            # =========================
            html.Div([
                # Flex-Reihe mit Logo links und Textblock rechts
                html.Div([
                    html.Img(
                        src="/assets/logo.png",
                        style={
                            "height": "150px",
                            "marginRight": "100px",
                        }
                    ),

                    # Textblock (H1 + H3 übereinander)
                    html.Div([
                        html.H1(
                            "Swiss Trade Insights",
                            style={
                                "margin": "0",
                                "fontFamily": "Arial, sans-serif",
                                "fontSize": "48px",
                                "fontWeight": "bold",
                                "background": "linear-gradient(90deg, #D52B1E, #022B7E)",
                                "WebkitBackgroundClip": "text",
                                "WebkitTextFillColor": "transparent",
                                "letterSpacing": "2px",
                            }
                        ),
                        html.H3(
                            "LATAM 2019–2024",
                            style={
                                "margin": "8px 0 0 0",
                                "color": "#555",
                                "fontFamily": "Arial, sans-serif",
                                "fontSize": "22px",
                                "fontStyle": "italic",
                                "letterSpacing": "1px",
                            }
                        ),
                    ],
                    style={
                        "display": "flex",
                        "flexDirection": "column",
                        "justifyContent": "center",
                        "alignItems": "flex-start",
                        "textAlign": "left",
                    }),
                ],
                style={
                    "display": "flex",
                    "alignItems": "center",        # vertikal zentriert
                    "justifyContent": "center",    # zentriert Gesamtblock
                    "textAlign": "left",
                }),
            ],
            style={
                "margin": "25px",
                "padding": "20px",
                "borderRadius": "12px",
                "background": "linear-gradient(145deg, #f9f9f9, #e8eef7)",
                "boxShadow": "4px 6px 15px rgba(0,0,0,0.15)",
            }),

            # =========================
            # Filters
            # =========================
            html.Div([
                # Language
                html.Div([
                    html.Label(id="lang_label", style={"fontWeight": "bold"}),
                    dmc.Select(
                        id="language",
                        data=[
                            {"label": "English", "value": "en"},
                            {"label": "Español", "value": "es"},
                        ],
                        value="en",
                        clearable=False,
                        required=True,
                        style={"width": 180}
                    )
                ], style={"marginBottom": "20px"}),

                # Year
                html.Div([
                    html.Label(id="year_label", style={"fontWeight": "bold"}),
                    dmc.MultiSelect(
                        id="year",
                        data=[{"label": str(y), "value": str(int(y))} for y in sorted(df["year"].dropna().unique())],
                        value=[str(int(df["year"].max()))],
                        searchable=True,
                        clearable=True,
                        style={"width": 250}
                    )
                ], style={"display": "flex", "flexDirection": "column"}),

                # Country
                html.Div([
                    html.Label(id="country_label", style={"fontWeight": "bold"}),
                    dmc.MultiSelect(
                        id="country",
                        data=[{"label": l, "value": l} for l in sorted(df["country_en"].unique())],
                        searchable=True,
                        clearable=True,
                        style={"width": 300}
                    )
                ], style={"display": "flex", "flexDirection": "column"}),

                # Tariff Level
                html.Div([
                    html.Label(id="hs_level_label", style={"fontWeight": "bold"}),
                    dmc.Select(
                        id="hs_level",
                        data=[
                            {"label": "2 digit - broad groups", "value": "HS2_Description"},
                            {"label": "4 digit - groups", "value": "HS4_Description"},
                            {"label": "6 digit - products", "value": "HS6_Description"},
                            {"label": "8 digit - detailed products", "value": "HS8_Description"},
                        ],
                        value="HS6_Description",
                        clearable=False,
                        required=True,
                        style={"width": 280}
                    )
                ], style={"display": "flex", "flexDirection": "column"}),

                # Description
                html.Div([
                    html.Label(id="product_label", style={"fontWeight": "bold"}),
                    dmc.MultiSelect(
                        id="product",
                        data=[],  # wird durch Callback gefüllt
                        searchable=True,
                        clearable=True,
                        nothingFoundMessage="No results",
                        maxDropdownHeight=500,
                        style={"width": "100%", "fontFamily": "Arial", "fontSize": "16px"}
                    )
                ], style={"flex": 1, "display": "flex", "flexDirection": "column"}),

            ], style={"display": "flex", "gap": "20px", "margin": "25px auto", "width": "90%", "justifyContent": "center"}),

            # KPIs
            html.Div(id="kpis", style={
                "display": "flex",
                "justifyContent": "space-between",
                "marginBottom": "20px",
                "fontFamily": "Arial"
            }),

            # Tabs
            dcc.Tabs(
                id="tabs",
                value="trend",
                children=[
                    dcc.Tab(label="📈 Trade Volume by Year", value="trend"),
                    dcc.Tab(label="🌍 Trade by Country", value="country"),
                    dcc.Tab(label="📦 Trade by Product", value="product"),
                    dcc.Tab(label="🌍📦 Top Products per Country", value="country_products"),
                    dcc.Tab(label="📈 Trade Trend per Product", value="trend_hs"),
                ],
                persistence=True,
                persistence_type="session",
                style={"fontFamily": "Arial"}
            ),

            html.Div(id="tabs-content", style={"fontFamily": "Arial"}),

            # Footer
            html.Div(
                "This App was developed by Patrick Kull with Swiss Open Government Data (opendata.swiss)",
                style={"textAlign": "center", "marginTop": "40px", "color": "gray", "fontSize": "12px", "fontFamily": "Arial"}
            )
        ])
    ]
)

# =========================
# Callbacks
# =========================

@app.callback(
    [Output("kpis", "children"),
     Output("tabs-content", "children")],
    [Input("year", "value"),
     Input("country", "value"),
     Input("hs_level", "value"),
     Input("product", "value"),
     Input("tabs", "value"),
     Input("language", "value")]
)

def update_dashboard(year, country, hs_level, product, tab, lang):

    # === Fallbacks erzwingen ===
    if not hs_level:
        hs_level = "HS6_Description"
    if not lang:
        lang = "en"

    labels = LANG.get(lang, LANG["en"])  # fallback: englisch
    years = tuple(int(y) for y in year) if year else ()

    flow_label_map = {
        "Export": labels["flow_export"],
        "Import": labels["flow_import"],
    }
    flow_color_map = {
        labels["flow_export"]: GRAPH_STYLE["color_export"],
        labels["flow_import"]: GRAPH_STYLE["color_import"],
    }
    legend_title_flow = labels["legend_flow"]
    axis_year = labels["axis_year"]
    axis_chf = labels["axis_chf"]
    axis_country = labels["axis_country"]
    axis_product = labels["axis_product"]
    axis_tariff_code = labels["axis_tariff_code"]
    no_data_message = labels["chart_no_data"]

    LOGGER.debug(
        "update_dashboard called | years=%s countries=%s hs_level=%s product_count=%s tab=%s lang=%s",
        years if years else "ALL",
        country if country else "ALL",
        hs_level,
        len(product) if product else 0,
        tab,
        lang,
    )

    dff = get_filtered_data(years, country, hs_level, product)
    log_dataframe_snapshot("Filtered data", dff)

    if years:
        dff_year = dff[dff["year"].isin(years)].copy()
    else:
        dff_year = dff.copy()

    log_dataframe_snapshot("Filtered data (year restricted)", dff_year)


    # ================= KPIs =================
    exp_sum = dff_year.loc[dff_year["Flow"] == "Export", "chf_num"].sum()
    imp_sum = dff_year.loc[dff_year["Flow"] == "Import", "chf_num"].sum()
    balance, volume = exp_sum - imp_sum, exp_sum + imp_sum
    if not years:
        year_label = labels["label_all_years"]
    elif len(years) == 1:
        year_label = str(years[0])
    else:
        year_label = f"{min(years)}–{max(years)}"

    LOGGER.debug(
        "KPI values | exports=%.2f imports=%.2f balance=%.2f volume=%.2f",
        exp_sum,
        imp_sum,
        balance,
        volume,
    )

    kpis = html.Div([
        html.Div([
            html.Div(f"{labels['kpi_exports']} {year_label}", style={"fontSize": "20px", "padding": "16px"}),
            html.Div(f"CHF {exp_sum:,.0f}".replace(",", "'"),
                     style={"fontSize": "28px", "fontWeight": "bold"})
        ], style={**GRAPH_STYLE["kpi_card"], "color": GRAPH_STYLE["color_export"],
                  "backgroundColor": GRAPH_STYLE["bg_color_export"]}), #"#fdecea"

        html.Div([
            html.Div(f"{labels['kpi_imports']} {year_label}", style={"fontSize": "20px", "padding": "16px"}),
            html.Div(f"CHF {imp_sum:,.0f}".replace(",", "'"),
                     style={"fontSize": "28px", "fontWeight": "bold"})
        ], style={**GRAPH_STYLE["kpi_card"], "color": GRAPH_STYLE["color_import"],
                  "backgroundColor": GRAPH_STYLE["bg_color_import"]}),

        html.Div([
            html.Div(f"{labels['kpi_balance']} {year_label}", style={"fontSize": "20px", "padding": "16px"}),
            html.Div(f"CHF {balance:,.0f}".replace(",", "'"),
                     style={"fontSize": "28px", "fontWeight": "bold"})
        ], style={**GRAPH_STYLE["kpi_card"], "color": GRAPH_STYLE["color_trade"],
                  "backgroundColor": GRAPH_STYLE["bg_color_balance"]}),

        html.Div([
            html.Div(f"{labels['kpi_volume']} {year_label}", style={"fontSize": "20px", "padding": "16px"}),
            html.Div(f"CHF {volume:,.0f}".replace(",", "'"),
                     style={"fontSize": "28px", "fontWeight": "bold"})
        ], style={**GRAPH_STYLE["kpi_card"], "color": "black",
                  "backgroundColor": GRAPH_STYLE["bg_color_trade"]})
    ], style={"display": "flex", "gap": "25px", "padding": "10px", "justifyContent": "space-evenly", "width":"100%", "height":"250px", "align-items":"center"})





    # Tabs
    content = None
    
    if tab == "trend":
        # ---------------------------
        # Trade Trend (Exports + Imports + Balance)
        # ---------------------------

        # Jahre immer vom Gesamtdatensatz
        min_year, max_year = int(df["year"].min()), int(df["year"].max())
        all_years = list(range(min_year, max_year + 1))
        flows = ["Export", "Import"]

        # 👉 Basierend auf df (NICHT auf dff_year mit Year-Filter)
        dff_trend = df

        # nur Country / Product filtern
        if country:
            dff_trend = dff_trend[dff_trend["country_en"].isin(country)]
        if product:
            if hs_level == "HS2_Description":
                dff_trend = dff_trend[dff_trend["HS2"].isin(product)]
            elif hs_level == "HS4_Description":
                dff_trend = dff_trend[dff_trend["HS4"].isin(product)]
            elif hs_level == "HS6_Description":
                dff_trend = dff_trend[dff_trend["HS6"].isin(product)]
            elif hs_level == "HS8_Description":
                dff_trend = dff_trend[dff_trend["HS8"].isin(product)]
            else:
                dff_trend = dff_trend[dff_trend[hs_level].isin(product)]

        country_label = ", ".join(country) if country else "LATAM"
        chart_title = labels["chart_trade_volume_title"].format(location=country_label)

        if dff_trend.empty:
            LOGGER.warning("Trend dataset empty; returning placeholder figure")
            trend_fig = build_empty_figure(chart_title, no_data_message)
        else:
            # Aggregation
            df_trend = dff_trend.groupby(["year", "Flow"])["chf_num"].sum().reset_index()

            # MultiIndex für alle Jahre × Flows
            full_index = pd.MultiIndex.from_product([all_years, flows], names=["year", "Flow"])
            df_trend = (
                df_trend.set_index(["year", "Flow"])
                .reindex(full_index, fill_value=0)
                .reset_index()
            )

            # Balance berechnen
            balance = (
                df_trend.pivot(index="year", columns="Flow", values="chf_num")
                .fillna(0)
            )
            for col in flows:
                if col not in balance.columns:
                    balance[col] = 0
            balance["Balance"] = balance["Export"] - balance["Import"]

            df_trend["Flow_localized"] = df_trend["Flow"].map(flow_label_map).fillna(df_trend["Flow"])

            # 📊 Export + Import Balken
            fig = px.bar(
                df_trend,
                x="year",
                y="chf_num",
                color="Flow_localized",
                barmode="stack",
                title=chart_title,
                template=GRAPH_STYLE["template"],
                color_discrete_map=flow_color_map,
                category_orders={"Flow_localized": [flow_label_map["Export"], flow_label_map["Import"]]}
            )

            # ➕ Balance-Linie
            fig.add_scatter(
                x=balance.index,
                y=balance["Balance"],
                mode="lines+markers+text",
                name=labels["chart_trade_volume_balance"],
                line=dict(color=GRAPH_STYLE["color_trade"], width=5, dash="dot"),
                marker=dict(size=12, symbol="circle"),
                text=[human_format(v) for v in balance["Balance"]],
                textposition="top center",
                hovertemplate=(
                    f"<b>{axis_year}:</b> %{{x}}<br>"
                    f"<b>{labels['chart_trade_volume_balance']}:</b> %{{y:,.0f}}<extra></extra>"
                )
            )

            # Hovertexte fix
            fig.update_traces(
                hovertemplate=(
                    f"<b>{axis_year}:</b> %{{x}}<br>"
                    f"<b>{legend_title_flow}:</b> %{{fullData.name}}<br>"
                    f"<b>{axis_chf}:</b> %{{y:,.0f}}<extra></extra>"
                ),
                selector=dict(type="bar")
            )

            # Fixe X-Achse für alle Jahre
            fig.update_xaxes(
                tickmode="linear",
                dtick=1,
                range=[min_year - 0.5, max_year + 0.5]
            )

            # Layout
            trend_fig = apply_standard_layout(
                fig,
                x_title=axis_year,
                y_title=axis_chf,
                legend="horizontal",
                height=900,
                legend_title=legend_title_flow
            )

        LOGGER.debug("Trend chart prepared for %d years", len(all_years))

        content = html.Div(
            dcc.Graph(
                id="trend",
                figure=trend_fig,
                style={"height": "80vh", "width": "80vw"}
            ),
            style={
                "display": "flex",
                "justifyContent": "center",
                "alignItems": "center",
                "padding": "20px",
            }
        )

    elif tab == "trend_hs":
        content = html.Div(
            html.Div(id="trend_hs_content"),
            style={"padding": "20px"}
        )

    elif tab == "country":
        # === Titel mit Ländern und Jahren ===
        def format_years(values: tuple[int, ...]) -> str:
            if not values:
                return labels["label_all_years"]
            years_sorted = sorted(values)
            return ", ".join(str(y) for y in years_sorted)

        def format_countries(countries) -> str:
            if not countries:
                return "LATAM"
            return ", ".join(countries)

        years_label = format_years(years)
        countries_label = format_countries(country)

        title_country = (
            f"🌍 {labels['chart_country_title'].format(flow_info=labels['chart_country_flow_info'], years=years_label)} "
            f"– {countries_label}"
        )

        if dff_year.empty:
            LOGGER.warning("Country tab has no data; showing placeholder")
            country_fig = build_empty_figure(title_country, no_data_message)
        else:
            # Aggregation Export / Import
            country_ranking = (
                dff_year.groupby(["country_en", "Flow"])["chf_num"].sum().reset_index()
            )
            totals = (
                country_ranking.groupby("country_en")["chf_num"]
                .sum().reset_index()
            )
            top_countries = totals.sort_values("chf_num", ascending=False).head(25)["country_en"]
            country_ranking = country_ranking[country_ranking["country_en"].isin(top_countries)]

            # Berechne Trade Balance pro Land
            pivot = (
                country_ranking.pivot(index="country_en", columns="Flow", values="chf_num")
                .fillna(0)
            )
            pivot["Trade balance"] = pivot.get("Export", 0) - pivot.get("Import", 0)
            pivot = pivot.reset_index()

            # Lokalisierte Flow-Namen
            country_ranking["Flow_localized"] = (
                country_ranking["Flow"].map(flow_label_map).fillna(country_ranking["Flow"])
            )

            # Hauptdiagramm: Exporte + Importe (Stacked)
            fig = px.bar(
                country_ranking,
                x="chf_num",
                y="country_en",
                color="Flow_localized",
                barmode="stack",
                orientation="h",
                title=title_country,
                template=GRAPH_STYLE["template"],
                color_discrete_map=flow_color_map,
                category_orders={"Flow_localized": [flow_label_map["Export"], flow_label_map["Import"]]}
            )

            # ➕ Trade Balance Linie / Marker
            fig.add_scatter(
                x=pivot["Trade balance"],
                y=pivot["country_en"],
                mode="markers+text",
                name=labels["chart_trade_volume_balance"],
                marker=dict(
                    color=GRAPH_STYLE["color_trade"],
                    size=12,
                    symbol="diamond"
                ),
                text=[human_format(v) for v in pivot["Trade balance"]],
                textposition="middle right",
                hovertemplate=(
                    f"<b>{axis_country}:</b> %{{y}}<br>"
                    f"<b>{labels['chart_trade_volume_balance']}:</b> %{{x:,.0f}}<extra></extra>"
                ),
            )

            # Hover für Balken
            fig.update_traces(
                hovertemplate=(
                    f"<b>{axis_country}:</b> %{{y}}<br>"
                    f"<b>{legend_title_flow}:</b> %{{fullData.name}}<br>"
                    f"<b>{axis_chf}:</b> %{{x:,.0f}}<extra></extra>"
                ),
                selector=dict(type="bar")
            )

            # Sortierung nach Totalwerten
            fig.update_layout(
                yaxis=dict(categoryorder="total ascending")
            )

            # Standardlayout anwenden
            country_fig = apply_standard_layout(
                fig,
                x_title=axis_chf,
                y_title=axis_country,
                legend="horizontal",
                height=900,
                legend_title=legend_title_flow,
            )

            LOGGER.debug(
                "Country chart prepared with %d countries (including trade balance)",
                country_ranking["country_en"].nunique(),
            )

        content = html.Div(
            dcc.Graph(
                id="country_ranking",
                figure=country_fig,
                style={"height": "80vh", "width": "80vw"}
            ),
            style={
                "display": "flex",
                "justifyContent": "center",
                "alignItems": "center",
                "padding": "20px",
            }
        )


    elif tab == "product":
        # passendes HS-Level bestimmen
        if hs_level == "HS2_Description":
            code_col, label_col, desc_col = "HS2", "HS2_Label", "HS2_Description"
        elif hs_level == "HS4_Description":
            code_col, label_col, desc_col = "HS4", "HS4_Label", "HS4_Description"
        elif hs_level == "HS6_Description":
            code_col, label_col, desc_col = "HS6", "HS6_Label", "HS6_Description"
        else:
            code_col, label_col, desc_col = "HS8", "HS8_Label", "HS8_Description"

        if dff_year.empty:
            LOGGER.warning("Product tab has no data; showing placeholder")
            title_product = labels["chart_product_title"].format(
                location=", ".join(country) if country else "LATAM",
                years=labels["label_all_years"] if not years else ", ".join(str(y) for y in sorted(years)),
            )
            product_fig = build_empty_figure(title_product, no_data_message)
        else:
            # Aggregation nach Flow + HS-Level
            product_ranking = (
                dff_year.groupby([code_col, "Flow", desc_col], observed=True)["chf_num"].sum().reset_index()
            )

            # Summen pro Produkt
            totals = (
                product_ranking.groupby(code_col, observed=True)["chf_num"]
                .sum()
                .reset_index()
            )

            totals["chf_num"] = pd.to_numeric(totals["chf_num"], errors="coerce")

            # Nur Produkte >= 10'000 CHF berücksichtigen
            totals = totals[totals["chf_num"] >= 10000]

            # Top 20 auswählen
            top_products = (
                totals.sort_values("chf_num", ascending=False)
                .head(20)[code_col]
            )

            # Filter anwenden
            product_ranking = product_ranking[product_ranking[code_col].isin(top_products)]

            if product_ranking.empty:
                LOGGER.warning("No products remain after filtering; showing placeholder")
                title_product = labels["chart_product_title"].format(
                    location=", ".join(country) if country else "LATAM",
                    years=labels["label_all_years"] if not years else ", ".join(str(y) for y in sorted(years)),
                )
                product_fig = build_empty_figure(title_product, no_data_message)
            else:
                product_ranking["hs_label"] = (
                    product_ranking[code_col].astype(str) + " – " + product_ranking[desc_col].astype(str)
                )

                # Kürzen für Anzeige (nur falls nötig)
                def shorten_text(t, max_len=80):
                    return t if len(t) <= max_len else t[:max_len] + "..."
                product_ranking["hs_wrapped"] = product_ranking["hs_label"].apply(shorten_text)

                # Balken-Beschriftungen
                product_ranking["CHF_label"] = product_ranking["chf_num"].apply(human_format)

                # Titel
                def format_years(selected_years: tuple[int, ...]) -> str:
                    if not selected_years:
                        return labels["label_all_years"]
                    years_sorted = sorted(selected_years)
                    return ", ".join(str(y) for y in years_sorted)

                def format_countries(countries) -> str:
                    if not countries:
                        return "LATAM"
                    return ", ".join(countries)

                years_label = format_years(years)
                countries_label = format_countries(country)

                product_ranking["Flow_localized"] = (
                    product_ranking["Flow"].map(flow_label_map).fillna(product_ranking["Flow"])
                )

                # Plot
                fig = px.bar(
                    product_ranking,
                    x="chf_num", y="hs_wrapped",
                    color="Flow_localized", orientation="h",
                    title=labels["chart_product_title"].format(location=countries_label, years=years_label),
                    template=GRAPH_STYLE["template"],
                    color_discrete_map=flow_color_map,
                    category_orders={"Flow_localized": [flow_label_map["Export"], flow_label_map["Import"]]},
                    text="CHF_label",
                    custom_data=[code_col, desc_col]   # für Hovertext
                )

                # Hovertext
                fig.update_traces(
                    textposition="outside",
                    insidetextanchor="start",
                    hovertemplate=(
                        f"<b>{axis_tariff_code}:</b> %{{customdata[0]}}<br>"
                        f"<b>{labels['label_description']}:</b> %{{customdata[1]}}<br>"
                        f"<b>{legend_title_flow}:</b> %{{fullData.name}}<br>"
                        f"<b>{axis_chf}:</b> %{{text}}<extra></extra>"
                    )
                )

                # Layout
                fig.update_layout(
                    yaxis=dict(categoryorder="total ascending"),
                    margin=dict(l=400, r=80, t=80, b=80)
                )
                product_fig = apply_standard_layout(
                    fig,
                    x_title=axis_chf,
                    y_title=axis_product,
                    legend="horizontal",
                    height=900,
                    legend_title=legend_title_flow,
                )
                LOGGER.debug("Product chart prepared with %d products", product_ranking[code_col].nunique())

        content = html.Div(
            dcc.Graph(
                id="product_ranking",
                figure=product_fig,
                style={"height": "80vh", "width": "80vw"}
            ),
            style={
                "display": "flex",
                "justifyContent": "center",
                "alignItems": "center",
                "padding": "20px",
            }
        )


    elif tab == "country_products":
        filter_row = html.Div([
            html.Label(
                labels["country_products_top_label"],
                style={
                    "marginLeft": "20px",
                    "fontFamily": "Arial",
                    "lineHeight": "40px",
                    "font-weight":"bold",
                }
            ),
            dmc.Select(
                id="country_products_topn",
                data=[{"label": labels["top_n_option"].format(n=n), "value": str(n)} for n in [5, 10, 20, 25, 50, 100]],
                value="5",    # 👉 String statt Int
                clearable=False,
                style={"width": 150}
            )

        ], style={
            "display": "flex",
            "alignItems": "center",   # Label + Dropdown zentrieren
            "gap": "15px",
            "margin": "40px"
        })

        # Wrapper für die Ausgaben
        content = html.Div([
            filter_row,
            html.Div(id="country_products_output", style={
                "display": "flex",
                "flexDirection": "column",
                "gap": "30px"
            })
        ])



    return kpis, content

@app.callback(
    Output("country_products_output", "children"),
    [Input("country", "value"),
     Input("year", "value"),
     Input("country_products_topn", "value"),
     Input("language", "value")]
)


def update_country_products(selected_countries, years, top_n, lang):
    years = tuple(int(y) for y in years) if years else ()
    top_n = int(top_n) if top_n else 5
    if not lang:
        lang = "en"

    labels = LANG.get(lang, LANG["en"])
    no_data_message = labels["chart_no_data"]
    axis_product = labels["axis_product"]
    axis_chf = labels["axis_chf"]
    LOGGER.debug(
        "update_country_products called | countries=%s years=%s top_n=%d",
        selected_countries if selected_countries else "ALL",
        years if years else "ALL",
        top_n,
    )

    dff_tab = get_filtered_data(years, selected_countries, "HS6_Description", None)
    dff_tab = dff_tab[dff_tab["chf_num"] > 0]
    log_dataframe_snapshot("Country products base", dff_tab)

    if dff_tab.empty:
        return html.Div(
            no_data_message,
            style={"padding": "20px", "fontStyle": "italic"}
        )

    data = (
        dff_tab.groupby(["country_en", "Flow", "HS6_Description"])["chf_num"]
        .sum()
        .reset_index()
    )

    if data.empty:
        return html.Div(
            no_data_message,
            style={"padding": "20px", "fontStyle": "italic"}
        )

    countries = selected_countries or sorted(data["country_en"].unique())

    def format_years_label(values: tuple[int, ...]) -> str:
        if not values:
            return labels["label_all_years"]
        if len(values) == 1:
            return str(values[0])
        return f"{min(values)}–{max(values)}"

    years_label = format_years_label(years)
    rows = []
    for c in countries:
        for flow in ["Export", "Import"]:
            df_flow = (
                data[(data["country_en"] == c) & (data["Flow"] == flow)]
                .nlargest(top_n, "chf_num")
                .copy()
            )

            title_template = (
                labels["chart_top_exports_title"]
                if flow == "Export"
                else labels["chart_top_imports_title"]
            )
            chart_title = title_template.format(top_n=top_n, country=c, years=years_label)

            if df_flow.empty:
                LOGGER.debug("No %s data for country %s", flow, c)
                fig = build_empty_figure(chart_title, no_data_message)
            else:
                df_flow["HS6_wrapped"] = df_flow["HS6_Description"].apply(lambda t: wrap_and_shorten(t, 30, 60))
                fig = px.bar(
                    df_flow,
                    x="chf_num", y="HS6_wrapped",
                    orientation="h",
                    title=chart_title,
                    template=GRAPH_STYLE["template"],
                    color_discrete_sequence=[
                        GRAPH_STYLE["color_export"] if flow == "Export" else GRAPH_STYLE["color_import"]
                    ],
                    text=df_flow["chf_num"].apply(human_format)
                )
                fig.update_traces(
                    textposition="outside",
                    insidetextanchor="start",
                    cliponaxis=False,
                    hovertemplate=(
                        f"<b>{axis_product}:</b> %{{y}}<br>"
                        f"<b>{axis_chf}:</b> %{{text}}<extra></extra>"
                    )
                )
                n_products = len(df_flow)
                height = max(450, n_products * 40)
                fig.update_layout(
                    yaxis=dict(categoryorder="total ascending", title=axis_product),
                    xaxis=dict(title=axis_chf),
                    margin=dict(l=250, r=50, t=80, b=50)
                )
                fig.update_yaxes(automargin=True, tickfont=dict(size=14))
                fig = apply_standard_layout(
                    fig,
                    x_title=axis_chf,
                    y_title=axis_product,
                    legend=False,
                    height=height,
                )

            graph_component = dcc.Graph(figure=fig)
            if flow == "Export":
                col_export = graph_component
            else:
                col_import = graph_component

        row = html.Div([
            html.Div(
                html.H4(c, style={"textAlign": "left", "fontSize": "20px"}),
                style={"flex": "0 0 220px", "padding": "10px"}
            ),
            html.Div(col_export, style={"flex": "2", "padding": "20px"}),
            html.Div(col_import, style={"flex": "2", "padding": "20px"})
        ], style={"display": "flex", "gap": "10px", "margin": "50px"})

        rows.append(row)

    return html.Div(rows, style={"display": "flex", "flexDirection": "column", "gap": "30px"})

@app.callback(
    Output("trend_hs_content", "children"),
    [Input("country", "value"),
     Input("hs_level", "value"),
     Input("tabs", "value"),
     Input("language", "value")]
)

def update_trend_hs(country, hs_level, tab, lang):
    if not hs_level or hs_level not in {
        "HS2_Description",
        "HS4_Description",
        "HS6_Description",
        "HS8_Description",
    }:
        hs_level = "HS6_Description"
    if not lang:
        lang = "en"
    labels = LANG.get(lang, LANG["en"])
    axis_year = labels["axis_year"]
    axis_chf = labels["axis_chf"]
    no_data_message = labels["chart_no_data"]
    LOGGER.debug("update_trend_hs called | countries=%s hs_level=%s", country if country else "ALL", hs_level)

    dff_hs = get_filtered_data(None, country, hs_level, None)
    log_dataframe_snapshot("Trend HS base", dff_hs)

    if dff_hs.empty:
        empty = dcc.Graph(figure=build_empty_figure(labels["chart_trade_trend_title"], no_data_message))
        return html.Div([empty], style={"padding": "20px"})

    all_years = dff_hs["year"].dropna().unique()
    if all_years.size == 0:
        empty = dcc.Graph(figure=build_empty_figure(labels["chart_trade_trend_title"], no_data_message))
        return html.Div([empty], style={"padding": "20px"})

    min_year, max_year = int(all_years.min()), int(all_years.max())

    trend_hs = (
        dff_hs.groupby(["year", hs_level, "Flow"], observed=True)["chf_num"]
        .sum()
        .reset_index()
    )

    if trend_hs.empty:
        empty = dcc.Graph(figure=build_empty_figure(labels["chart_trade_trend_title"], no_data_message))
        return html.Div([empty], style={"padding": "20px"})

    hs_level_labels = {
        "HS2_Description": labels["hs_level_label_HS2_Description"],
        "HS4_Description": labels["hs_level_label_HS4_Description"],
        "HS6_Description": labels["hs_level_label_HS6_Description"],
        "HS8_Description": labels["hs_level_label_HS8_Description"],
    }
    level_label = hs_level_labels.get(hs_level, hs_level.replace("_Description", ""))
    years_range_label = f"{min_year}–{max_year}"

    def shorten_text(t, max_len=50):
        if not isinstance(t, str):
            return ""
        return t if len(t) <= max_len else t[:max_len] + "…"

    trend_hs["hs_label"] = trend_hs[hs_level].apply(shorten_text)

    df_exp = trend_hs[trend_hs["Flow"] == "Export"]
    df_imp = trend_hs[trend_hs["Flow"] == "Import"]

    if df_exp.empty:
        fig_exp = build_empty_figure(
            labels["chart_export_trend_title"].format(level=level_label, years=years_range_label),
            no_data_message,
        )
        fig_exp.update_layout(height=900)
    else:
        fig_exp = px.line(
            df_exp,
            x="year", y="chf_num",
            color="hs_label",
            line_group="hs_label",
            markers=True,
            title=labels["chart_export_trend_title"].format(level=level_label, years=years_range_label),
            template=GRAPH_STYLE["template"]
        )
        fig_exp.update_traces(
            marker=dict(size=10),
            hovertemplate=(
                f"<b>{axis_year}:</b> %{{x}}<br>"
                f"<b>{labels['label_description']}:</b> %{{fullData.name}}<br>"
                f"<b>{axis_chf}:</b> %{{y:,.0f}}<extra></extra>"
            )
        )
        fig_exp = apply_standard_layout(
            fig_exp,
            axis_year,
            axis_chf,
            legend="bottom_full",
            height=900,
        )

    if df_imp.empty:
        fig_imp = build_empty_figure(
            labels["chart_import_trend_title"].format(level=level_label, years=years_range_label),
            no_data_message,
        )
        fig_imp.update_layout(height=900)
    else:
        fig_imp = px.line(
            df_imp,
            x="year", y="chf_num",
            color="hs_label",
            line_group="hs_label",
            markers=True,
            title=labels["chart_import_trend_title"].format(level=level_label, years=years_range_label),
            template=GRAPH_STYLE["template"]
        )
        fig_imp.update_traces(
            marker=dict(size=10),
            hovertemplate=(
                f"<b>{axis_year}:</b> %{{x}}<br>"
                f"<b>{labels['label_description']}:</b> %{{fullData.name}}<br>"
                f"<b>{axis_chf}:</b> %{{y:,.0f}}<extra></extra>"
            )
        )
        fig_imp = apply_standard_layout(
            fig_imp,
            axis_year,
            axis_chf,
            legend="bottom_full",
            height=900,
        )

    LOGGER.debug(
        "Trend HS charts prepared | export_traces=%d import_traces=%d",
        len(fig_exp.data),
        len(fig_imp.data),
    )

    return html.Div([
        html.Div(dcc.Graph(figure=fig_exp), style={"flex": "1"}),
        html.Div(dcc.Graph(figure=fig_imp), style={"flex": "1"})
    ], style={"display": "flex", "gap": "20px", "padding": "20px"})

@app.callback(
    Output("product", "data"),
    Input("hs_level", "value")
)


def update_product_options(hs_level):

    if not hs_level:  
       hs_level = "HS6_Description"   # Fallback erzwingen

    LOGGER.debug("update_product_options called | hs_level=%s", hs_level)


    if hs_level == "HS2_Description":
        df_temp = df[["HS2", "HS2_Label"]].drop_duplicates().sort_values("HS2")
        options = [{"label": row["HS2_Label"], "value": row["HS2"]} for _, row in df_temp.iterrows()]
    elif hs_level == "HS4_Description":
        df_temp = df[["HS4", "HS4_Label"]].drop_duplicates().sort_values("HS4")
        options = [{"label": row["HS4_Label"], "value": row["HS4"]} for _, row in df_temp.iterrows()]
    elif hs_level == "HS6_Description":
        df_temp = df[["HS6", "HS6_Label"]].drop_duplicates().sort_values("HS6")
        options = [{"label": row["HS6_Label"], "value": row["HS6"]} for _, row in df_temp.iterrows()]
    else:
        df_temp = df[["HS8", "HS8_Label"]].drop_duplicates().sort_values("HS8")
        options = [{"label": row["HS8_Label"], "value": row["HS8"]} for _, row in df_temp.iterrows()]

    LOGGER.debug("Prepared %d options for hs_level %s", len(options), hs_level)
    return options


@app.callback(
    Output("tabs", "children"),
    Input("language", "value")
)
def update_tabs(lang):

    if not lang:
       lang = "en"  # Fallback erzwingen
    labels = LANG.get(lang, LANG["en"])
    LOGGER.debug("update_tabs called | lang=%s", lang)
    return [
        dcc.Tab(label=labels["tab_trend"], value="trend"),
        dcc.Tab(label=labels["tab_country"], value="country"),
        dcc.Tab(label=labels["tab_product"], value="product"),
        dcc.Tab(label=labels["tab_country_products"], value="country_products"),
        dcc.Tab(label=labels["tab_trend_hs"], value="trend_hs"),
    ]

@app.callback(
    [Output("lang_label", "children"),
     Output("year_label", "children"),
     Output("country_label", "children"),
     Output("hs_level_label", "children"),
     Output("product_label", "children")],
    Input("language", "value")
)
def update_filter_labels(lang):
    if not lang:
        lang = "en"
    labels = LANG.get(lang, LANG["en"])
    LOGGER.debug("update_filter_labels called | lang=%s", lang)
    return (labels["label_language"],
            labels["label_year"],
            labels["label_country"],
            labels["label_hs_level"],
            labels["label_description"])

# =========================
# Run
# =========================
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8050))
    debug_mode = os.environ.get("DASH_DEBUG", "false").lower() == "true"
    app.run(host="0.0.0.0", port=port, debug=debug_mode)