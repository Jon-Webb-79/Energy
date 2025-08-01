import dash
from dash import dcc, html, Input, Output
import plotly.graph_objs as go
import pandas as pd
import sqlite3

# ==========================================================================================
# ==========================================================================================

# File:    mixPlot.py
# Date:    August 1, 2025
# Author:  Jonathan A. Webb
# Purpose: Creates an energy dashboard with the folowing plots 
#          - Energy production / energy fraction from 1973 to present by technology

# ==========================================================================================
# ==========================================================================================
# Relevant Functions

def load_data():
    """
    Load energy production data from a SQLite database and return it as a DataFrame.

    The function reads from the 'EnergyMix' table in the local 'Energy.db' SQLite
    database. It parses the 'Date' column as datetime and drops the 'CrudeOil' column,
    as crude oil is not typically used for electricity generation.

    Returns
    -------
    pd.DataFrame
        A DataFrame containing monthly energy production data by source,
        with 'Date' as a datetime column and 'CrudeOil' excluded.
    """
    conn = sqlite3.connect("Energy.db")
    df = pd.read_sql_query("SELECT * FROM EnergyMix", conn, parse_dates=["Date"])
    conn.close()

    # Drop crude oil column — it's not relevant for electricity
    if "CrudeOil" in df.columns:
        df = df.drop(columns=["CrudeOil"])

    return df

# ------------------------------------------------------------------------------------------ 

def aggregate_annual(df):
    """
    Aggregate monthly energy production data into annual totals.

    This function groups the data by year, sums the numeric columns (energy values),
    and returns a new DataFrame with a datetime 'Date' column representing the start
    of each year.

    Parameters
    ----------
    df : pd.DataFrame
        The input DataFrame with a 'Date' column and monthly energy data.

    Returns
    -------
    pd.DataFrame
        A new DataFrame aggregated by year, with 'Date' representing January 1st
        of each year and numeric values representing annual totals.
    """
    df["Year"] = df["Date"].dt.year
    df_annual = df.groupby("Year").sum(numeric_only=True).reset_index()
    df_annual["Date"] = pd.to_datetime(df_annual["Year"], format="%Y")
    return df_annual.drop(columns=["Year"])

# ------------------------------------------------------------------------------------------ 

def percent_mix(df):
    """
    Convert absolute energy values to percentage share of total production for each time period.

    For each row (e.g., each month or year), this function computes the total energy production
    and converts each energy source to its percentage contribution to that total.

    Parameters
    ----------
    df : pd.DataFrame
        The input DataFrame with numeric energy source columns and a 'Date' column.

    Returns
    -------
    pd.DataFrame
        A DataFrame where each numeric column represents the percentage share of
        the total energy mix for that period (row).
    """
    numeric_cols = df.select_dtypes(include="number").columns
    totals = df[numeric_cols].sum(axis=1)
    return df.assign(**{col: df[col] / totals * 100 for col in numeric_cols})

# ========================================================================================== 
# ========================================================================================== 
# Create Dashboard here 

def create_app():
    df_full = load_data()
    energy_sources = df_full.columns.drop("Date")
    min_year = df_full["Date"].dt.year.min()
    max_year = df_full["Date"].dt.year.max()
    year_marks = {year: str(year) for year in range(min_year, max_year + 1, 2)}

    app = dash.Dash(__name__)
    app.title = "Energy Mix Dashboard"

    app.layout = html.Div(className="dash-container", children=[
        html.H1("U.S. Primary Energy Production"),

        html.Div([
            html.Label("Select Energy Sources:"),
            dcc.Dropdown(
                options=[{"label": col, "value": col} for col in energy_sources],
                value=list(energy_sources),
                multi=True,
                id="source-selector"
            ),
        ]),

        html.Div(className="control-row", children=[
            html.Div([
                html.Label("Time Resolution:"),
                dcc.Dropdown(
                    options=[
                        {"label": "Monthly", "value": "monthly"},
                        {"label": "Annual Sum", "value": "annual"},
                    ],
                    value="monthly",
                    id="time-selector",
                    clearable=False
                ),
            ], className="control-block"),

            html.Div([
                html.Label("Value Type:"),
                dcc.Dropdown(
                    options=[
                        {"label": "Raw Energy (Quadrillion Btu)", "value": "raw"},
                        {"label": "% of Mix", "value": "percent"},
                    ],
                    value="raw",
                    id="view-selector",
                    clearable=False
                ),
            ], className="control-block"),
        ]),

        html.Div([
            dcc.RangeSlider(
                id="year-slider",
                min=min_year,
                max=max_year,
                step=1,
                value=[min_year, max_year],
                marks=year_marks,
                tooltip={"placement": "bottom", "always_visible": False}
            )
        ]),

        dcc.Graph(id="energy-plot", style={"height": "700px"}),

        # Lower third divided into 2/3 and 1/3 columns
        html.Div(className="bottom-row", children=[

            html.Div(id="left-panel", children=[
                # Placeholder — you can insert another dcc.Graph or custom content later
                html.Div("← Placeholder for future plot", style={"height": "700px", "padding": "10px"})
            ], className="left-panel"),

            html.Div(id="right-panel", children=[
                dcc.Graph(id="energy-pie"),
                dcc.Slider(
                    id="pie-year-slider",
                    min=min_year,
                    max=max_year,
                    step=1,
                    value=max_year,
                    marks={year: str(year) for year in range(min_year, max_year + 1, 5)},
                    vertical=True,
                    tooltip={"always_visible": True}
                )
            ], className="right-panel"),
        ]),

        html.A(
            "Source: U.S. Energy Information Administration (EIA)",
            href="https://www.eia.gov/totalenergy/data/browser/index.php?tbl=T01.02#/?f=M&start=197301&end=202504&charted=1-2-3-4-6-13",
            target="_blank",
            style={
                "fontSize": "14px",
                "color": "#3366cc",
                "textDecoration": "none",
                "marginTop": "20px",
                "display": "block",
                "textAlign": "center"
            }
        )
    ])    

    # Store full data and config in the app for use in callbacks
    app.df_full = df_full
    app.energy_sources = energy_sources

    return app, min_year, max_year, year_marks

# ------------------------------------------------------------------------------------------ 

app, min_year, max_year, year_marks = create_app()
@app.callback(
    Output("energy-plot", "figure"),
    Input("source-selector", "value"),
    Input("time-selector", "value"),
    Input("view-selector", "value"),
    Input("year-slider", "value")
)
def update_plot(sources, time_res, view_type, year_range):
    if not sources:
        return go.Figure()

    df = app.df_full.copy()

    start_year, end_year = year_range
    df = df[(df["Date"].dt.year >= start_year) & (df["Date"].dt.year <= end_year)]

    if time_res == "annual":
        df = aggregate_annual(df)

    if view_type == "percent":
        df = percent_mix(df)

    if time_res == "annual":
        df = aggregate_annual(df)

    if view_type == "percent":
        df = percent_mix(df)

    fig = go.Figure()
    hover_format = ".2f" if view_type == "raw" else ".2f%%"
    for col in sources:
        if view_type == "percent":
            hovertemplate = f"{col}: %{{y:.2f}}%<extra></extra>"
        else:
            hovertemplate = f"{col}: %{{y:.2f}}<extra></extra>"

        fig.add_trace(go.Scatter(
            x=df["Date"],
            y=df[col],
            mode="lines",
            name=col,
            line=dict(width=3),
            hovertemplate=hovertemplate
        ))
    
    y_label = "% of Total Mix" if view_type == "percent" else "Quadrillion Btu"
    fig.update_layout(
        xaxis_title="<b>Date</b>",
        yaxis_title=f"<b>{y_label}</b>",

        xaxis=dict(
            title_font=dict(size=26, family="Roboto", color="#333"),
            tickfont=dict(size=14),
            gridcolor="lightgray",
            gridwidth=1,
            zeroline=False
        ),
        yaxis=dict(
            title_font=dict(size=26, family="Roboto", color="#333"),
            tickfont=dict(size=14),
            gridcolor="lightgray",
            gridwidth=1,
            zeroline=False
        ),

        legend=dict(
            font=dict(size=13),
            bgcolor="rgba(255,255,255,0.8)",
            bordercolor="lightgray",
            borderwidth=1
        ),
        hovermode="x unified",
        hoverlabel=dict(
            font=dict(size=14),
            namelength=-1
        ),
        margin=dict(t=60, b=60, l=80, r=40),
        plot_bgcolor="#ffffff",
        paper_bgcolor="#ffffff"
    )

    return fig

# ------------------------------------------------------------------------------------------

@app.callback(
    Output("energy-pie", "figure"),
    Input("pie-year-slider", "value")
)
def update_pie(selected_year):
    df = app.df_full.copy()
    df["Year"] = df["Date"].dt.year

    # Filter to selected year
    df_year = df[df["Year"] == selected_year]

    # Aggregate total by column
    totals = df_year.drop(columns=["Date", "Year"]).sum()

    # Define categories
    pie_data = {
        "Gas": totals.get("GasDry", 0) + totals.get("GasLiquid", 0),
        "Coal": totals.get("Coal", 0),
        "Nuclear": totals.get("Nuclear", 0),
        "Wind": totals.get("Wind", 0),
        "Solar": totals.get("Solar", 0),
        "All Others": (
            totals.get("Hydro", 0) +
            totals.get("Geothermal", 0) +
            totals.get("Biomass", 0)
        )
    }

    fig = go.Figure(data=[
        go.Pie(
            labels=list(pie_data.keys()),
            values=list(pie_data.values()),
            hole=0.4,
            textinfo="label+percent",
            marker=dict(line=dict(color="white", width=2))
        )
    ])
    fig.update_layout(
        title=f"Energy Mix for {selected_year}",
        title_font=dict(size=26, family="Roboto", color="#333"),
        margin=dict(t=40, b=20, l=20, r=20),
        showlegend=True
    )
    return fig

# ========================================================================================== 
# ========================================================================================== 
# Run application

if __name__ == "__main__":
    app.run(debug=True)

# ========================================================================================== 
# ========================================================================================== 
# eof
