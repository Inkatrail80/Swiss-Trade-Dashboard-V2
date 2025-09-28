# -*- coding: utf-8 -*-
from dash import Dash, dcc, html, Input, Output, State
import pandas as pd
import plotly.express as px
import os
import textwrap
import humanize
from translations import LANG
import dash_bootstrap_components as dbc
import dash_mantine_components as dmc


# =========================
# Load data
# =========================
df = pd.read_csv("trade_subset_latam.csv.gz", sep=";", encoding="utf-8", compression="gzip")

# Datatypes
df["year"] = pd.to_numeric(df["year"], errors="coerce").astype("Int64")
df["chf_num"] = pd.to_numeric(df["chf_num"], errors="coerce").fillna(0).astype(float)

for col in ["country_en", "HS2_Description", "HS4_Description", "HS6_Description", "HS8_Description", "traffic"]:
    if col in df.columns:
        df[col] = df[col].fillna("Unknown").astype(str)

# Flow-Mapping
df["Flow"] = df["traffic"].map({"EXP": "Export", "IMP": "Import"}).fillna(df["traffic"])


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
    }


}

# =========================
# Hilfsfunktionen
# =========================

# Hilfsfunktion: wrappe Texte (z. B. HS-Beschreibungen)
def wrap_text(s, width=30):
    if pd.isna(s):
        return ""
    return "<br>".join(textwrap.wrap(str(s), width=width))

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
    if legend == "horizontal":
        legend_cfg = GRAPH_STYLE["legend_horizontal"]
    elif legend == "vertical":
        legend_cfg = GRAPH_STYLE["legend_vertical"]
    elif legend == "bottom_outside":
        legend_cfg = GRAPH_STYLE["legend_bottom_vertical"]   # neu
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
        hoverlabel=dict(
            align="left"
        )
    )
    return fig


HOVERTEXTS = {
    "year_flow": (
        "<b>Year:</b> %{x}<br>"
        "<b>Flow:</b> %{fullData.name}<br>"
        "<b>CHF:</b> %{y:,.0f}<extra></extra>"
    ),
    "year_product": (
        "<b>Year:</b> %{x}<br>"
        "<b>Product:</b> %{customdata[0]}<br>"
        "<b>CHF:</b> %{y:,.0f}<extra></extra>"
    ),
    "country": (
        "<b>Country:</b> %{y}<br>"
        "<b>Flow:</b> %{fullData.name}<br>"
        "<b>CHF:</b> %{x:,.0f}<extra></extra>"
    ),
    "product": (
        "<b>Product:</b> %{y}<br>"
        "<b>Flow:</b> %{fullData.name}<br>"
        "<b>CHF:</b> %{x:,.0f}<extra></extra>"
    ),
    "treemap": (
        "<b>Flow:</b> %{parent}<br>"
        "<b>Description:</b> %{label}<br>"
        "<b>CHF:</b> %{value:,.0f}<extra></extra>"
    )
}

# =========================
# App
# =========================
app = Dash(__name__, suppress_callback_exceptions=True, external_stylesheets=[dbc.themes.BOOTSTRAP])
server = app.server

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
                            "textAlign": "center",
                            "letterSpacing": "2px",
                        }
                    ),
                    html.H3(
                        "LATAM 2019–2024",
                        style={
                            "marginTop": "10px",
                            "color": "#555",
                            "fontFamily": "Arial, sans-serif",
                            "fontSize": "22px",
                            "fontStyle": "italic",
                            "textAlign": "center",
                            "letterSpacing": "1px",
                        }
                    )
                ],
                style={
                    "textAlign": "center",
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
                    # Language separat
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

                        # Description (Mantine MultiSelect)
                        html.Div([
                            html.Label(id="product_label", style={"fontWeight": "bold"}),
                            dmc.MultiSelect(
                                id="product",
                                data=[],  # wird durch Callback gefüllt
                                searchable=True,
                                clearable=True,
                                nothingFound="No results",
                                maxDropdownHeight=500,
                                style={"width": "100%", "fontFamily": "Arial", "font-size":"16px"}
                            )
                        ], style={"flex": 1, "display": "flex", "flexDirection": "column"})
                    ],
                    style={"display": "flex", "gap": "20px", "margin": "25px", "width": "100vw"}),
                ]),


                # KPIs
                html.Div(id="kpis", style={
                    "display": "flex",
                    "justifyContent": "space-between",
                    "marginBottom": "20px",
                    "fontFamily": "Arial"
                }),

                # Tabs
                dcc.Tabs(id="tabs", value="trend", children=[
                    dcc.Tab(label="📈 Trade Volume by Year", value="trend"),
                    dcc.Tab(label="🌍 Trade by Country", value="country"),
                    dcc.Tab(label="📦 Trade by Product", value="product"),
                    dcc.Tab(label="🌍📦 Top Products per Country", value="country_products"),
                    dcc.Tab(label="📈 Trade Trend per Product", value="trend_hs"),
                    dcc.Tab(label="📂 Treemap", value="treemap_hs"),
                    dcc.Tab(label="🌐 Sankey Trade Flow", value="sankey"),
                ], persistence=True, persistence_type="session", style={"fontFamily": "Arial"}),

                html.Div(id="tabs-content", style={"fontFamily": "Arial"}),

                # Footer
                html.Div(
                    "This App was developed by Patrick Kull with Swiss Open Government Data (opendata.swiss)",
                    style={"textAlign": "center", "marginTop": "40px", "color": "gray", "fontSize": "12px", "fontFamily": "Arial"}
                )
            ])


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
    years = [int(y) for y in year] if year else []
    dff = df.copy()
    if country:
        dff = dff[dff["country_en"].isin(country)]

    if product:
        if hs_level == "HS2_Description":
            dff = dff[dff["HS2"].isin(product)]
        elif hs_level == "HS4_Description":
            dff = dff[dff["HS4"].isin(product)]
        elif hs_level == "HS6_Description":
            dff = dff[dff["HS6"].isin(product)]
        elif hs_level == "HS8_Description":
            dff = dff[dff["HS8"].isin(product)]
        else:
            dff = dff[dff[hs_level].isin(product)]



    dff_year = dff[dff["year"].isin(years)].copy()

    # ================= KPIs =================
    exp_sum = dff_year.loc[dff_year["Flow"] == "Export", "chf_num"].sum()
    imp_sum = dff_year.loc[dff_year["Flow"] == "Import", "chf_num"].sum()
    balance, volume = exp_sum - imp_sum, exp_sum + imp_sum
    if not years:
        year_label = "All years"
    elif len(years) == 1:
        year_label = str(years[0])
    else:
        year_label = f"{min(years)}–{max(years)}"





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

        # Basisdaten aggregieren
        df_trend = dff.groupby(["year", "Flow"])["chf_num"].sum().reset_index()

        # Sicherstellen, dass für jedes Jahr beide Flows existieren
        years = df_trend["year"].unique()
        flows = ["Export", "Import"]
        full_index = pd.MultiIndex.from_product([years, flows], names=["year", "Flow"])

        df_trend = (
            df_trend.set_index(["year", "Flow"])
            .reindex(full_index, fill_value=0)
            .reset_index()
        )

        # Balance berechnen (Export - Import) – robust
        balance = (
            df_trend.pivot(index="year", columns="Flow", values="chf_num")
            .fillna(0)
        )

        # fehlende Spalten sicherstellen
        for col in ["Export", "Import"]:
            if col not in balance.columns:
                balance[col] = 0

        balance["Balance"] = balance["Export"] - balance["Import"]



        # Länder-Label für Titel
        country_label = ", ".join(country) if country else "LATAM"

        # Gestapelte Balken (Export + Import)
        fig = px.bar(
            df_trend,
            x="year",
            y="chf_num",
            color="Flow",
            barmode="stack",
            title=f"📈 Trade Volume by Year – {country_label}",
            template=GRAPH_STYLE["template"],
            color_discrete_map={
                "Export": GRAPH_STYLE["color_export"],
                "Import": GRAPH_STYLE["color_import"]
            }
        )

        # Balance-Linie hinzufügen
        fig.add_scatter(
            x=balance.index,
            y=balance["Balance"],
            mode="lines+markers+text",
            name="Balance",
            line=dict(color=GRAPH_STYLE["color_trade"], width=5, dash="dot"),
            marker=dict(size=16, symbol="circle"),
            text=[human_format(v) for v in balance["Balance"]],
            textposition="top center",
            hovertemplate="<b>Year:</b> %{x}<br><b>Balance:</b> %{y:,.0f}<extra></extra>"
        )

        # Hovertexte für Balken
        fig.update_traces(
            hovertemplate="<b>Year:</b> %{x}<br><b>Flow:</b> %{fullData.name}<br><b>CHF:</b> %{y:,.0f}<extra></extra>",
            selector=dict(type="bar")
        )

        # Layout
        fig = apply_standard_layout(
            fig,
            x_title="Year",
            y_title="CHF",
            legend="horizontal",
            height=900,
            legend_title="Flow"
        )

        content = html.Div(
            dcc.Graph(
                id="trend",
                figure=fig,
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
        content = html.Div([
            html.Div([
                html.Label("HS-Level:", style={
                    "marginLeft": "20px",
                    "fontFamily": "Arial",
                    "lineHeight": "40px",
                    "font-weight": "bold",
                }),
                dmc.Select(
                    id="hs_level_trend",
                    data=[
                        {"label": "HS2", "value": "HS2_Description"},
                        {"label": "HS4", "value": "HS4_Description"},
                        {"label": "HS6", "value": "HS6_Description"},
                        {"label": "HS8", "value": "HS8_Description"},
                    ],
                    value="HS2_Description",
                    clearable=False,
                    style={"width": 200}
                ),
            ], style={"margin": "20px", "display": "flex",
            "alignItems": "center",   # Label + Dropdown zentrieren
            "gap": "15px",
            "margin": "40px"
       }),

            # 👉 nur Platzhalter, Inhalte kommen aus update_trend_hs
            html.Div(id="trend_hs_content")
        ])





    elif tab == "country":
        country_ranking = (
            dff_year.groupby(["country_en", "Flow"])["chf_num"].sum().reset_index()
        )
        totals = country_ranking.groupby("country_en")["chf_num"].sum().reset_index()
        top_countries = totals.sort_values("chf_num", ascending=False).head(25)["country_en"]
        country_ranking = country_ranking[country_ranking["country_en"].isin(top_countries)]

        def format_years(years: list[int]) -> str:
            """Format year selection for titles (explicit years)."""
            if not years:
                return "All Years"
            years_sorted = sorted(years)
            return ", ".join(str(y) for y in years_sorted)

        years_label = format_years(years)

        fig = px.bar(
            country_ranking, x="chf_num", y="country_en",
            color="Flow", barmode="stack", orientation="h",
            title=f"🌍 Trade by Country (Export + Import, {years_label})",
            template=GRAPH_STYLE["template"],
            color_discrete_map={
                "Export": GRAPH_STYLE["color_export"],
                "Import": GRAPH_STYLE["color_import"]
            }
        )
        fig.update_traces(

            hovertemplate="<b>Country:</b> %{y}<br><b>Flow:</b> %{fullData.name}<br><b>CHF:</b> %{x:,.0f}<extra></extra>"
        )

        fig.update_layout(yaxis=dict(categoryorder="total ascending"))
        fig = apply_standard_layout(fig, x_title="CHF", y_title="Country", legend="horizontal", height=900)
        
        content = html.Div(
        dcc.Graph(
                id="product_ranking",
                figure=fig,
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

        # Aggregation nach Flow + HS-Level
        product_ranking = (
            dff_year.groupby([code_col, "Flow", desc_col])["chf_num"].sum().reset_index()
        )

        # Summen pro Produkt
        totals = (
            product_ranking.groupby(code_col)["chf_num"]
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

        # Label für Achse
        product_labels = product_ranking.groupby(code_col)[desc_col].first().to_dict()
        product_ranking["hs_label"] = product_ranking[code_col] + " – " + product_ranking[desc_col]

        # Kürzen für Anzeige (nur falls nötig)
        def shorten_text(t, max_len=80):
            return t if len(t) <= max_len else t[:max_len] + "..."
        product_ranking["hs_wrapped"] = product_ranking["hs_label"].apply(shorten_text)

        # Balken-Beschriftungen
        product_ranking["CHF_label"] = product_ranking["chf_num"].apply(human_format)

        # Titel
        def format_years(years: list[int]) -> str:
            if not years:
                return "All Years"
            years_sorted = sorted(years)
            return ", ".join(str(y) for y in years_sorted)

        def format_countries(countries: list[str]) -> str:
            if not countries:
                return "LATAM"
            return ", ".join(countries)

        years_label = format_years(years)
        countries_label = format_countries(country)

        # Plot
        fig = px.bar(
            product_ranking,
            x="chf_num", y="hs_wrapped",
            color="Flow", orientation="h",
            title=f"📦 Trade by Product ({countries_label}, {years_label})",
            template=GRAPH_STYLE["template"],
            color_discrete_map={
                "Export": GRAPH_STYLE["color_export"],
                "Import": GRAPH_STYLE["color_import"]
            },
            text="CHF_label",
            custom_data=[code_col, desc_col]   # für Hovertext
        )

        # Hovertext
        fig.update_traces(
            textposition="outside",
            insidetextanchor="start",
            hovertemplate=(
                "<b>Tariff code:</b> %{customdata[0]}<br>"
                "<b>Description:</b> %{customdata[1]}<br>"
                "<b>Flow:</b> %{fullData.name}<br>"
                "<b>CHF:</b> %{text}<extra></extra>"
            )
        )

        # Layout
        fig.update_layout(
            yaxis=dict(categoryorder="total ascending"),
            margin=dict(l=400, r=80, t=80, b=80)
        )
        fig = apply_standard_layout(fig, x_title="CHF", y_title="Product", legend="horizontal", height=900)

        content = html.Div(
            dcc.Graph(
                id="product_ranking",
                figure=fig,
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
                "Top Products:",
                style={
                    "marginLeft": "20px",
                    "fontFamily": "Arial",
                    "lineHeight": "40px",
                    "font-weight":"bold",
                }
            ),
            dmc.Select(
                id="country_products_topn",
                data=[{"label": f"Top {n}", "value": str(n)} for n in [5, 10, 20, 25, 50, 100]],
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

    elif tab == "sankey":
        # HS-Level → passende Spalten
        if hs_level == "HS2_Description":
            code_col, label_col = "HS2", "HS2_Label"
        elif hs_level == "HS4_Description":
            code_col, label_col = "HS4", "HS4_Label"
        elif hs_level == "HS6_Description":
            code_col, label_col = "HS6", "HS6_Label"
        else:
            code_col, label_col = "HS8", "HS8_Label"

        # Aggregation
        dff_sankey = (
            dff_year.groupby(["Flow", "country_en", code_col, label_col])["chf_num"]
            .sum()
            .reset_index()
        )

        # Node-Liste: Flow + Länder + Codes (kurz!)
        all_nodes = (
            list(dff_sankey["Flow"].unique())
            + list(dff_sankey["country_en"].unique())
            + list(dff_sankey[code_col].unique())
        )
        node_map = {name: i for i, name in enumerate(all_nodes)}

        # Links aufbauen
        sources, targets, values, customdata = [], [], [], []
        for _, row in dff_sankey.iterrows():
            # Flow → Country
            sources.append(node_map[row["Flow"]])
            targets.append(node_map[row["country_en"]])
            values.append(row["chf_num"])
            customdata.append(f"{row['Flow']} → {row['country_en']}<br>CHF {row['chf_num']:,.0f}")

            # Country → Product (kurzer Code als Node, volle Info im Hover)
            sources.append(node_map[row["country_en"]])
            targets.append(node_map[row[code_col]])
            values.append(row["chf_num"])
            customdata.append(
                f"{row['country_en']} → {row[label_col]}<br>CHF {row['chf_num']:,.0f}"
            )

        import plotly.graph_objects as go
        fig = go.Figure(data=[go.Sankey(
            node=dict(
                pad=20,
                thickness=20,
                line=dict(color="black", width=0.5),
                label=all_nodes,   # nur kurze Namen
                color="lightblue"
            ),
            link=dict(
                source=sources,
                target=targets,
                value=values,
                customdata=customdata,
                hovertemplate="%{customdata}<extra></extra>",
                color="rgba(0,100,200,0.3)"
            )
        )])

        fig.update_layout(
            title="🔗 Trade Sankey Flow (Flow → Country → Product)",
            font=dict(size=14, family="Arial")
        )

        content = html.Div(
            dcc.Graph(
                id="sankey_graph",
                figure=fig,
                style={"height": "90vh", "width": "90vw"}
            ),
            style={
                "display": "flex",
                "justifyContent": "center",
                "alignItems": "center",
                "padding": "20px",
            }
        )



    elif tab == "treemap_hs":
        treemap_data = (
            dff_year.groupby(["Flow", "country_en", "HS6_Description"])["chf_num"]
            .sum()
            .reset_index()
        )

        # Top 15 Länder
        top_countries = (
            treemap_data.groupby("country_en")["chf_num"].sum().reset_index()
            .sort_values("chf_num", ascending=False)
            .head(15)["country_en"]
        )
        treemap_data = treemap_data[treemap_data["country_en"].isin(top_countries)]

        # Pro Land+Flow: bestes Produkt + Rest
        frames = []
        for (flow, country), group in treemap_data.groupby(["Flow", "country_en"]):
            if group.empty:
                continue
            best = group.nlargest(1, "chf_num")
            rest_sum = group["chf_num"].sum() - best["chf_num"].iloc[0]
            rest = pd.DataFrame([{
                "Flow": flow,
                "country_en": country,
                "HS6_Description": "Other products",
                "chf_num": rest_sum
            }])
            frames.append(pd.concat([best, rest], ignore_index=True))

        treemap_top = pd.concat(frames, ignore_index=True)

        # Wrap Text
        treemap_top["HS6_wrapped"] = treemap_top["HS6_Description"].apply(lambda t: wrap_text(t, width=40))

        fig = px.treemap(
            treemap_top,
            path=["Flow", "country_en", "HS6_wrapped"],
            values="chf_num",
            color="Flow",
            color_discrete_map={"Export": GRAPH_STYLE["color_export"], "Import": GRAPH_STYLE["color_import"]},
            title="📂 Treemap: Top Produkt + Rest pro Land"
        )

        fig.update_traces(
            customdata=treemap_top[["Flow", "country_en"]].values,
            hovertemplate=(
                "<b>Flow:</b> %{customdata[0]}<br>"
                "<b>Land:</b> %{customdata[1]}<br>"
                "<b>Produkt (HS6):</b> %{label}<br>"
                "<b>CHF:</b> %{value:,.0f}<extra></extra>"
            )
        )

        fig.update_layout(uniformtext=dict(minsize=14, mode="show"), hoverlabel=dict(align="left"))
        fig = apply_standard_layout(fig, legend=True, height=900)
        content = dcc.Graph(figure=fig, style={"height": "100vh"})



    return kpis, content

@app.callback(
    Output("country_products_output", "children"),
    [Input("country", "value"),
     Input("year", "value"),
     Input("country_products_topn", "value")]
)


def update_country_products(selected_countries, years, top_n):

    years = [int(y) for y in years] if years else []
    top_n = int(top_n)
    # Daten nach Jahren filtern (globaler Filter)
    dff_tab = df[df["year"].isin(years)].copy()
    dff_tab = dff_tab[dff_tab["chf_num"] > 0]

    # Basisdaten: Land x Flow x Produkt
    data = (
        dff_tab.groupby(["country_en", "Flow", "HS6_Description"])["chf_num"]
        .sum()
        .reset_index()
    )

    # Falls kein Land gewählt → alle Länder anzeigen
    if selected_countries:
        countries = selected_countries
    else:
        countries = sorted(data["country_en"].unique())

    rows = []
    for c in countries:
        for flow in ["Export", "Import"]:
            df_flow = (
                data[(data["country_en"] == c) & (data["Flow"] == flow)]
                .nlargest(top_n, "chf_num")
                .copy()
            )
            df_flow["HS6_wrapped"] = df_flow["HS6_Description"].apply(lambda t: wrap_and_shorten(t, 30, 60))

            # 🔹 Titel dynamisch: Top-N, Flow, Land, Jahr(e)
            years_label = f"{min(years)}–{max(years)}" if len(years) > 1 else str(years[0])
            title = f"Top {top_n} {flow}s – {c} ({years_label})"

            fig = px.bar(
                df_flow,
                x="chf_num", y="HS6_wrapped",
                orientation="h",
                title=title,
                template=GRAPH_STYLE["template"],
                color_discrete_sequence=[GRAPH_STYLE["color_export"]] if flow == "Export" else [GRAPH_STYLE["color_import"]],
                text=df_flow["chf_num"].apply(human_format)
            )
            fig.update_traces(
                textposition="outside",
                insidetextanchor="start",
                cliponaxis=False,   # verhindert, dass Texte abgeschnitten werden
                hovertemplate=(  # <<<<< HIER
                    "<b>Product:</b> %{y}<br>"
                    "<b>CHF:</b> %{text}<extra></extra>"  # <--- HIER
            )
            )


            fig.update_layout(
                yaxis=dict(categoryorder="total ascending", title="Produkt"),
                xaxis=dict(title="CHF"),
                margin=dict(l=300, r=120, t=80, b=80)  # mehr Platz links/rechts/unten
            )

            # Anzahl Produkte für diese Grafik
            n_products = len(df_flow)
            height = max(450, n_products * 40)

            fig.update_layout(
                yaxis=dict(categoryorder="total ascending", title="Produkt"),
                xaxis=dict(title="CHF"),
                margin=dict(l=250, r=50, t=80, b=50)
            )

            fig.update_yaxes(
                automargin=True,
                tickfont=dict(size=14)
            )

            fig = apply_standard_layout(fig, legend=False, height=height)


            if flow == "Export":
                col_export = dcc.Graph(figure=fig)
            else:
                col_import = dcc.Graph(figure=fig)

        # Eine Zeile: Ländername + Export + Import nebeneinander
        # Eine Zeile: Ländername + Export + Import nebeneinander
        row = html.Div([
            # feste Breite für die Länder-Spalte
            html.Div(
                html.H4(c, style={"textAlign": "left", "fontSize": "20px"}),
                style={"flex": "0 0 220px", "padding": "10px"}   # <-- feste Breite
            ),
            html.Div(col_export, style={"flex": "2", "padding": "20px"}),
            html.Div(col_import, style={"flex": "2", "padding": "20px"})
        ], style={"display": "flex", "gap": "10px", "margin": "50px"})


        rows.append(row)

    return html.Div(rows, style={"display": "flex", "flexDirection": "column", "gap": "30px"})

@app.callback(
    Output("trend_hs_content", "children"),
    [Input("country", "value"),
     Input("hs_level_trend", "value")]
)

def update_trend_hs(country, hs_level):
    all_years = df["year"].dropna().unique()
    min_year, max_year = int(all_years.min()), int(all_years.max())

    dff_hs = df[(df["year"] >= min_year) & (df["year"] <= max_year)].copy()
    if country:
        dff_hs = dff_hs[dff_hs["country_en"].isin(country)]

    # Gruppierung nach Jahr + Flow + HS-Description
    trend_hs = (
        dff_hs.groupby(["year", hs_level, "Flow"])["chf_num"]
        .sum()
        .reset_index()
    )

    # Kürzen für Legende (nicht umbrechen, nur abschneiden)
    def shorten_text(t, max_len=50):
        if not isinstance(t, str):
            return ""
        return t if len(t) <= max_len else t[:max_len] + "…"

    trend_hs["hs_label"] = trend_hs[hs_level].apply(shorten_text)

    # ===================== Exporte =====================
    df_exp = trend_hs[trend_hs["Flow"] == "Export"]

    fig_exp = px.line(
        df_exp,
        x="year", y="chf_num",
        color="hs_label",
        line_group="hs_label",
        markers=True,
        title=f"📈 Export Trend by {hs_level.replace('_Description','')} ({min_year}–{max_year})",
        template=GRAPH_STYLE["template"]
    )
    fig_exp.update_traces(
        marker=dict(size=10),  # Punkte größer
        hovertemplate=(
            "<b>Year:</b> %{x}<br>"
            "<b>Description:</b> %{fullData.name}<br>"
            "<b>CHF:</b> %{y:,.0f}<extra></extra>"
        )
    )
    fig_exp = apply_standard_layout(fig_exp, "Year", "CHF", legend="bottom_outside", height=900)

    # ===================== Importe =====================
    df_imp = trend_hs[trend_hs["Flow"] == "Import"]

    fig_imp = px.line(
        df_imp,
        x="year", y="chf_num",
        color="hs_label",
        line_group="hs_label",
        markers=True,
        title=f"📈 Import Trend by {hs_level.replace('_Description','')} ({min_year}–{max_year})",
        template=GRAPH_STYLE["template"]
    )
    fig_imp.update_traces(
        marker=dict(size=10),
        hovertemplate=(
            "<b>Year:</b> %{x}<br>"
            "<b>Description:</b> %{fullData.name}<br>"
            "<b>CHF:</b> %{y:,.0f}<extra></extra>"
        )
    )
    fig_imp = apply_standard_layout(fig_imp, "Year", "CHF", legend="bottom_outside", height=900)

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

    return options


@app.callback(
    Output("tabs", "children"),
    Input("language", "value")
)
def update_tabs(lang):

    if not lang:
       lang = "en"  # Fallback erzwingen
    labels = LANG.get(lang, LANG["en"])
    labels = LANG.get(lang, LANG["en"])
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
    app.run(host="0.0.0.0", port=port, debug=True)
