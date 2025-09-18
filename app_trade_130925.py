# -*- coding: utf-8 -*-
from dash import Dash, dcc, html, Input, Output, State
import pandas as pd
import plotly.express as px
import os
import textwrap
import humanize

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
        "margin": "10px",
        "flex": "1",
        "textAlign": "center",
        "fontWeight": "bold",
        "fontSize": "22px",
        "background": "white",
        "fontFamily": "Arial"
    },

    # Farben
    "color_export": "#E30613",   # Export = Swiss Red
    "color_import": "#008C6A",   # Import = Petrol Green
    "color_trade": "#1A3C80",    # Balance / Trade = Dark Blue
    "template": "plotly_white",

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
app = Dash(__name__, suppress_callback_exceptions=True)
server = app.server

app.layout = html.Div([
    # Header
    html.Div([
        html.H1("Swiss Trade Dashboard", style={"marginBottom": "0", "fontFamily": "Arial"}),
        html.H3("LATAM 2019–2024", style={"marginTop": "0", "color": "gray", "fontFamily": "Arial"})
    ], style={
        "textAlign": "center",
        "marginBottom": "30px",
        "padding": "20px",
        "borderRadius": "12px",
        "boxShadow": "4px 4px 15px rgba(0,0,0,0.2)",
        "background": "linear-gradient(145deg, #ffffff, #f0f0f0)"
    }),

    # Filters
    html.Div([
        # Erste Reihe: Dropdowns
        html.Div([
            html.Label("Year:", style={"fontFamily": "Arial", "alignSelf": "center"}),
            dcc.Dropdown(
                id="year",
                options=[{"label": str(y), "value": int(y)} for y in sorted(df["year"].dropna().unique())],
                value=[int(df["year"].max())],
                multi=True,
                style={"width": "150px", "fontFamily": "Arial"}
            ),

            html.Label("Country:", style={"fontFamily": "Arial", "alignSelf": "center"}),
            dcc.Dropdown(
                id="country",
                options=[{"label": l, "value": l} for l in sorted(df["country_en"].unique())],
                multi=True,
                style={"width": "250px", "fontFamily": "Arial"}
            ),

            html.Label("Product:", style={"fontFamily": "Arial", "alignSelf": "center"}),
            dcc.Dropdown(
                id="product",
                options=[{"label": p, "value": p} for p in sorted(df["HS6_Description"].unique())],
                multi=True,
                style={"flex": "1", "fontFamily": "Arial"}
            ),

            html.Label("HS-Level:", style={"fontFamily": "Arial", "alignSelf": "center"}), 
            dcc.Dropdown(
                id="hs_level",
                options=[
                    {"label": "HS2", "value": "HS2_Description"},
                    {"label": "HS4", "value": "HS4_Description"},
                    {"label": "HS6", "value": "HS6_Description"},
                    {"label": "HS8", "value": "HS8_Description"}
                ],
                value="HS2_Description",
                clearable=False,
                style={"width": "180px", "fontFamily": "Arial"}
            )
        ], style={"display": "flex", "gap": "20px", "marginBottom": "20px"}),

        # Zweite Reihe: Slider auf voller Breite
        html.Div([
            html.Label("Min. CHF:", style={"fontFamily": "Arial", "marginBottom": "10px"}),
            dcc.Slider(
                id="chf_slider",
                min=0,
                max=1_000_000_000,
                step=1_000_000,
                value=0,    
                marks={
                    0: "0",
                    1_000_000_000: "1Bn"
                },
                tooltip={"placement": "bottom", "always_visible": True},
                updatemode="mouseup"
            ),

        ], style={
            "width": "100%",
            "padding": "0 40px",
            "marginBottom": "30px"
        })
    ]),

    # KPIs
    html.Div(id="kpis", style={
        "display": "flex",
        "justifyContent": "space-around",
        "marginBottom": "20px",
        "fontFamily": "Arial"
    }),

    # Tabs
    dcc.Tabs(id="tabs", value="trend", children=[
    dcc.Tab(label="📈 Trade Volume by Year", value="trend", style={"fontFamily": "Arial"}),
    dcc.Tab(label="🌍 Trade by Country", value="country", style={"fontFamily": "Arial"}),
    dcc.Tab(label="📦 Trade by Product", value="product", style={"fontFamily": "Arial"}),
    dcc.Tab(label="📦 Top Products per Country 🌍", value="country_products", style={"fontFamily": "Arial"}),
    dcc.Tab(label="📈 Trade Trend per Product", value="trend_hs", style={"fontFamily": "Arial"}),
    dcc.Tab(label="📂 Treemap", value="treemap_hs", style={"fontFamily": "Arial"})
    ],
    persistence=True,             # Merkt sich den gewählten Tab
    persistence_type="session",   # Gilt pro Sitzung
    style={"fontFamily": "Arial"}),


    html.Div(id="tabs-content", style={"fontFamily": "Arial"}),

    # Footer
    html.Div(
        "This App was developped by Patrick with Swiss Open Government Data",
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
     Input("product", "value"),
     Input("hs_level", "value"),
     Input("chf_slider", "value"),
     Input("tabs", "value")]
)
def update_dashboard(year, country, product, hs_level, chf_min, tab):
    dff = df.copy()
    if country:
        dff = dff[dff["country_en"].isin(country)]
    if product:
        dff = dff[dff["HS6_Description"].isin(product)]
    dff = dff[dff["chf_num"] >= chf_min]

    dff_year = dff[dff["year"].isin(year)].copy()

    # ================= KPIs =================
    exp_sum = dff_year.loc[dff_year["Flow"] == "Export", "chf_num"].sum()
    imp_sum = dff_year.loc[dff_year["Flow"] == "Import", "chf_num"].sum()
    balance, volume = exp_sum - imp_sum, exp_sum + imp_sum
    year_label = f"{min(year)}–{max(year)}" if len(year) > 1 else str(year[0])

    kpis = html.Div([
        html.Div([
            html.Div("Exports " + year_label, style={"fontSize": "16px", "marginBottom": "8px"}),
            html.Div(f"CHF {exp_sum:,.0f}".replace(",", "'"),
                     style={"fontSize": "26px", "fontWeight": "bold"})
        ], style={**GRAPH_STYLE["kpi_card"], "color": GRAPH_STYLE["color_export"],
                  "backgroundColor": "#fdecea"}),

        html.Div([
            html.Div("Imports " + year_label, style={"fontSize": "16px", "marginBottom": "8px"}),
            html.Div(f"CHF {imp_sum:,.0f}".replace(",", "'"),
                     style={"fontSize": "26px", "fontWeight": "bold"})
        ], style={**GRAPH_STYLE["kpi_card"], "color": GRAPH_STYLE["color_import"],
                  "backgroundColor": "#e8f5e9"}),

        html.Div([
            html.Div("Balance " + year_label, style={"fontSize": "16px", "marginBottom": "8px"}),
            html.Div(f"CHF {balance:,.0f}".replace(",", "'"),
                     style={"fontSize": "26px", "fontWeight": "bold"})
        ], style={**GRAPH_STYLE["kpi_card"], "color": GRAPH_STYLE["color_trade"],
                  "backgroundColor": "#e3f2fd"}),

        html.Div([
            html.Div("Volume " + year_label, style={"fontSize": "16px", "marginBottom": "8px"}),
            html.Div(f"CHF {volume:,.0f}".replace(",", "'"),
                     style={"fontSize": "26px", "fontWeight": "bold"})
        ], style={**GRAPH_STYLE["kpi_card"], "color": "black",
                  "backgroundColor": "#f5f5f5"})
    ], style={"display": "flex", "gap": "25px", "padding": "25px", "justifyContent": "space-evenly"})





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

        # Balance berechnen (Export - Import)
        balance = (
            df_trend.pivot(index="year", columns="Flow", values="chf_num")
            .fillna(0)
        )
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
        # Letzte 5 Jahre auswählen
        max_year = dff["year"].max()
        last_years = list(range(max_year - 5, max_year + 1))
        dff_6 = dff[dff["year"].isin(last_years)].copy()

        # Gruppierung nach tn_key (stabil) + Flow
        trend_hs = (
            dff_6.groupby(["year", "tn_key", hs_level, "Flow"])["chf_num"]
            .sum()
            .reset_index()
        )

        # Einheitliche Beschriftung pro tn_key (erste vorkommende Description nehmen)
        label_map = (
            trend_hs.groupby("tn_key")[hs_level].first().to_dict()
        )
        trend_hs["hs_label"] = trend_hs["tn_key"].map(label_map)

        # Wrapping für bessere Lesbarkeit
        trend_hs["hs_label_wrapped"] = trend_hs["hs_label"].apply(lambda x: wrap_text(x, width=35))

        # Customdata für Hover (tn_key + wrapped label)
        trend_hs["customdata"] = list(zip(trend_hs["tn_key"], trend_hs["hs_label_wrapped"]))

        # Top 15 Kategorien nach Gesamtvolumen
        totals = trend_hs.groupby("tn_key")["chf_num"].sum().reset_index()
        top15 = totals.sort_values("chf_num", ascending=False).head(15)["tn_key"]
        trend_hs = trend_hs[trend_hs["tn_key"].isin(top15)]

        # -------------------- Exporte --------------------
        df_exp = trend_hs[trend_hs["Flow"] == "Export"]
        fig_exp = px.line(
            df_exp,
            x="year", y="chf_num",
            color="hs_label_wrapped",   # Wrapped für Legende
            line_group="tn_key",        # Stabilisierung pro Produkt
            markers=True,
            custom_data=["tn_key", "hs_label_wrapped"],
            title=f"📈 Export Trend by {hs_level.replace('_Description','')} (Top 15, {min(last_years)}–{max_year})",
            template=GRAPH_STYLE["template"]
        )
        fig_exp.update_traces(
            mode="lines+markers",
            marker=dict(size=12),
            hovertemplate=(
                "<b>Year:</b> %{x}<br>"
                "<b>CHF:</b> %{y:,.0f}<br>"
                "<b>tn_key:</b> %{customdata[0]}<br>"
                "<b>Description:</b> %{customdata[1]}<extra></extra>"
            )
        )
        fig_exp.update_layout(hoverlabel=dict(align="left"))
        fig_exp = apply_standard_layout(
            fig_exp, "Year", "CHF",
            legend="bottom_outside", height=900,
            legend_title=f"Legend ({hs_level.replace('_Description','')})"
        )

        # -------------------- Importe --------------------
        df_imp = trend_hs[trend_hs["Flow"] == "Import"]
        fig_imp = px.line(
            df_imp,
            x="year", y="chf_num",
            color="hs_label_wrapped",
            line_group="tn_key",
            markers=True,
            custom_data=["tn_key", "hs_label_wrapped"],
            title=f"📈 Import Trend by {hs_level.replace('_Description','')} (Top 15, {min(last_years)}–{max_year})",
            template=GRAPH_STYLE["template"]
        )
        fig_imp.update_traces(
            mode="lines+markers",
            marker=dict(size=12),
            hovertemplate=(
                "<b>Year:</b> %{x}<br>"
                "<b>CHF:</b> %{y:,.0f}<br>"
                "<b>tn_key:</b> %{customdata[0]}<br>"
                "<b>Description:</b> %{customdata[1]}<extra></extra>"
            )
        )
        fig_imp.update_layout(hoverlabel=dict(align="left"))
        fig_imp = apply_standard_layout(
            fig_imp, "Year", "CHF",
            legend="bottom_outside", height=900,
            legend_title=f"Legend ({hs_level.replace('_Description','')})"
        )

        # -------------------- Layout nebeneinander --------------------
        content = html.Div([
            html.Div(dcc.Graph(id="trend_hs_exp", figure=fig_exp), style={"flex": "1"}),
            html.Div(dcc.Graph(id="trend_hs_imp", figure=fig_imp), style={"flex": "1"})
        ], style={"display": "flex", "gap": "20px", "padding": "50px"})





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

        years_label = format_years(year)

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
        # Aggregation: nach tn_key & Flow summieren
        product_ranking = (
            dff_year.groupby(["tn_key", "Flow", "HS6_Description"])["chf_num"].sum().reset_index()
        )

        # Summen pro Produkt
        totals = (
            product_ranking.groupby("tn_key")["chf_num"]
            .sum()
            .reset_index()
        )

        # Sicherstellen, dass chf_num float ist
        totals["chf_num"] = pd.to_numeric(totals["chf_num"], errors="coerce")

        # Nur Produkte >= 10'000 CHF berücksichtigen
        totals = totals[totals["chf_num"] >= 10000]

        # Top 20 auswählen (oder weniger, wenn <20 übrig sind)
        top_products = (
            totals.sort_values("chf_num", ascending=False)
            .head(20)["tn_key"]
        )

        # Filter auf Haupttabelle anwenden
        product_ranking = product_ranking[product_ranking["tn_key"].isin(top_products)]
        # Eine HS8-Description pro tn_key wählen (falls mehrere → erste nehmen)
        product_labels = (
            product_ranking.groupby("tn_key")["HS6_Description"].first().to_dict()
        )
        product_ranking["HS8_Label"] = product_ranking["tn_key"].map(product_labels)

        # Kürzen für Achse
        def shorten_text(t, max_len=80):
            return t if len(t) <= max_len else t[:max_len] + "..."

        product_ranking["HS8_wrapped"] = product_ranking["HS8_Label"].apply(shorten_text)

        # Balken-Beschriftungen mit human_format vorbereiten
        product_ranking["CHF_label"] = product_ranking["chf_num"].apply(human_format)

        def format_years(years: list[int]) -> str:
            if not years:
                return "All Years"
            years_sorted = sorted(years)
            return ", ".join(str(y) for y in years_sorted)

        def format_countries(countries: list[str]) -> str:
            if not countries:
                return "LATAM"
            return ", ".join(countries)



        # Labels für Titel
        years_label = format_years(year)
        countries_label = format_countries(country)


        # Plot
        fig = px.bar(
            product_ranking, 
            x="chf_num", y="HS8_wrapped",
            color="Flow", orientation="h",
            title=f"📦 Trade by Product ({countries_label}, {years_label})",
            template=GRAPH_STYLE["template"],
            color_discrete_map={
                "Export": GRAPH_STYLE["color_export"],
                "Import": GRAPH_STYLE["color_import"]
            },
            text="CHF_label"   # <--- HIER die neue Spalte
        )

        # Hovertext
        fig.update_traces(
            textposition="outside",        # "inside" = im Balken, "outside" = daneben
            insidetextanchor="start",      # bessere Platzierung für horizontale Balken
            hovertemplate=(
                "<b>Product:</b> %{y}<br>"
                "<b>Flow:</b> %{fullData.name}<br>"
                "<b>CHF:</b> %{text}<extra></extra>"  # <--- HIER statt %{x:,.0f}
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
                "Top-N Produkte:",
                style={
                    "marginLeft": "20px",
                    "fontFamily": "Arial",
                    "lineHeight": "40px"   # sorgt für vertikale Zentrierung
                }
            ),
            dcc.Dropdown(
                id="country_products_topn",
                options=[{"label": f"Top {n}", "value": n} for n in [5, 10, 20, 25,50,100]],
                value=5,
                clearable=False,
                style={"width": "150px"}
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
                cliponaxis=False   # verhindert, dass Texte abgeschnitten werden
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
            html.Div(col_export, style={"flex": "2", "padding": "10px"}),
            html.Div(col_import, style={"flex": "2", "padding": "10px"})
        ], style={"display": "flex", "gap": "10px", "marginBottom": "40px"})


        rows.append(row)

    return html.Div(rows, style={"display": "flex", "flexDirection": "column", "gap": "30px"})


# =========================
# Run
# =========================
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8050))
    app.run(host="0.0.0.0", port=port, debug=True)
