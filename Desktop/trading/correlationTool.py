import pandas as pd
import numpy as np
import dash
from dash import dcc, html
from dash.dependencies import Input, Output, State
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import plotly.figure_factory as ff
from visualizationTool import createDashboardCorrelations
from createTool import dataFactory, yfinanceObject

# VARIABLES
trail1 = 200

# FETCH DATA
dataObjects = {
    "NOKEUR": dataFactory().createData("yfinance", "NOKEUR=X", "2000-01-01", "2023-11-24", "1d"),
    "Norway10YR": dataFactory().createData("file", "norway10YR", "2023-01-01", "2023-11-24", "1d", "norway10YR.xlsx", 8),
    "Bund10YR": dataFactory().createData("file", "bund10YR", "2023-01-01", "2023-11-24", "1d", "bund10YR.xlsx", 8),
    "Us10YR": dataFactory().createData("file", "us10YR", "2023-01-01", "2023-11-24", "1d", "us10YR.xlsx", 8),
    "SPY": dataFactory().createData("yfinance", "SPY", "2000-01-01", "2023-11-24", "1d"),
    "DAX": dataFactory().createData("yfinance", "^GDAXI", "2000-01-01", "2023-11-24", "1d"),
    "OSEAX": dataFactory().createData("yfinance", "OSEBX.OL", "2000-01-01", "2023-11-24", "1d"),
    "BrentFuture": dataFactory().createData("file", "brent1ST", "2023-01-01", "2023-11-24", "1d", "brent1ST.xlsx", 8),
    "GoldSpot": dataFactory().createData("yfinance", "GC=F", "2000-01-01", "2023-11-24", "1d"),
    "CopperFuture": dataFactory().createData("file", "copper1ST", "2000-01-01", "2023-11-24", "1d", "copper1ST.xlsx", 8),
    "NorwayUnemployment": dataFactory().createData("file", "norwayUnemployment", "2000-01-01", "2023-11-24", "1d", "norwayUnemployment.xlsx", 8),
    "VIX": dataFactory().createData("yfinance", "^VIX", "2000-01-01", "2023-11-24", "1d")}

# CLEAN AND PREPARE DATA
dfs = {}
for name, obj in dataObjects.items():
    df = obj.fetchData()
    df = df[['Close']] if isinstance(obj, yfinanceObject) else df
    df.sort_index(ascending=True, inplace=True)
    all_dates = pd.date_range(start=df.index.min(), end=df.index.max(), freq='B')
    df = df.reindex(all_dates, method='ffill')
    dfs[name] = df
df = pd.concat(dfs.values(), axis=1)
df.columns = dfs.keys()
df = df.asfreq('D').ffill()

# ADJUST TIME INTERVALS
adjustmentPeriod = 'daily'
if adjustmentPeriod == 'monthly':
    df = df.resample('M').last()
elif adjustmentPeriod == 'daily':
    resampleColumns = [col for col in ['euCPI', 'chinaCPI', 'norwayUnemployment'] if col in df.columns]
    df[resampleColumns] = df[resampleColumns].resample('D').ffill()

# DATA MANIPULATION - TRAILING PERFORMANCES
performanceColumns = ['NOKEUR', 'SPY', 'DAX', 'OSEAX', 'BrentFuture', 'GoldSpot', 'CopperFuture', 'VIX']
df = df.assign(**{f'perf{col}_{trail1}d': df[col].pct_change(periods=trail1) for col in performanceColumns})
df['yieldDeltaNorGer'], df['yieldDeltaNorUs'] = df['Norway10YR'] - df['Bund10YR'], df['Norway10YR'] - df['Us10YR']

# DATA MANIPULATION - TRAILING CORRELATIONS 
correlationColumns = {f'corr_{col}_NOKEUR': df[col].rolling(window=trail1).corr(df[f'perfNOKEUR_{trail1}d']) for col in df.columns if col != 'NOKEUR'}
df = df.assign(**correlationColumns)

# DATA MANIPULATION - DROP UNNECESSARY COLUMNS
df.drop(['Bund10YR', 'SPY', 'DAX', 'OSEAX', 'BrentFuture', 'GoldSpot', 'CopperFuture'], axis=1, inplace=True)

# VISUALIZATION
def createDashboardCorrelations(df, trail1):
    app = dash.Dash(__name__, external_stylesheets=['https://codepen.io/chriddyp/pen/bWLwgP.css'])
    def generateChart(df, columns):
        fig = make_subplots(specs=[[{"secondary_y": len(columns) > 1}]])
        colors = ['#8e44ad', '#f1c40f', '#2c3e50']  # Refreshed color palette
        for i, col in enumerate(columns):
            fig.add_trace(go.Scatter(x=df.index, y=df[col], mode='lines', name=col, line={'color': colors[i % len(colors)]}), secondary_y=i > 0)
        fig.update_layout(margin=dict(l=30, r=30, t=30, b=30), height=550, paper_bgcolor='#fdfbfb', xaxis={'showgrid': False}, yaxis={'showgrid': False})
        return fig
    def generateCorrelationMatrix(df):
        target_column = f'perfNOKEUR_{trail1}d'  # Trailing performance of NOKEUR
        df_filtered = df[[col for col in df.columns if not col.startswith('corr')]]
        corrMatrix = df_filtered.corrwith(df[target_column]).round(2).to_frame().T
        fig = ff.create_annotated_heatmap(z=corrMatrix.values, x=corrMatrix.columns.tolist(), y=[target_column], colorscale='RdYlGn')
        fig.update_layout(margin=dict(l=30, r=30, t=30, b=30), height=550, paper_bgcolor='#fdfbfb')
        return fig
    dropdownStyle = {'backgroundColor': '#fdfbfb', 'color': '#34495e', 'border': '1px solid #3498db', 'width': '90%', 'maxWidth': '1000px'}
    app.layout = html.Div(style={'display': 'flex', 'flexDirection': 'column', 'width': '100%', 'height': '100vh', 'backgroundColor': '#fdfbfb'}, children=[
        html.H1('Empirica Tools', style={'color': '#34495e', 'textAlign': 'center', 'padding': '15px'}),
        dcc.Tabs(style={'color': '#34495e'}, children=[
            dcc.Tab(label='Input Data', style={'backgroundColor': '#ecf0f1'}, selected_style={'backgroundColor': '#dfe6e9', 'color': '#3498db'}, children=[
                dcc.Graph(id='chart', style={'width': '100%', 'height': '85vh'}),
                dcc.Dropdown(id='dropdown', options=[{'label': col, 'value': col} for col in df.columns if not col.startswith('corr')], value=[df.columns[0]], multi=True, style=dropdownStyle)]),
            dcc.Tab(label='Corr Charts', style={'backgroundColor': '#ecf0f1'}, selected_style={'backgroundColor': '#dfe6e9', 'color': '#3498db'}, children=[
                dcc.Graph(id='corr-chart', style={'width': '100%', 'height': '85vh'}),
                dcc.Dropdown(id='corr-dropdown', options=[{'label': col, 'value': col} for col in df.columns if col.startswith('corr')], value=[df.columns[0]] if df.columns[0].startswith('corr') else [], multi=True, style=dropdownStyle)]),
            dcc.Tab(label='Correlation Matrix', style={'backgroundColor': '#ecf0f1'}, selected_style={'backgroundColor': '#dfe6e9', 'color': '#3498db'}, children=[
                dcc.Graph(id='correlation-matrix', style={'width': '100%', 'height': '85vh'}),
                dcc.Dropdown(id='correlation-target-dropdown', options=[{'label': col, 'value': col} for col in df.columns if not col.startswith('corr')], value=df.columns[0], style=dropdownStyle)])])])
    @app.callback(
        Output('chart', 'figure'),
        [Input('dropdown', 'value')])
    def update_chart(selectedColumns):
        return generateChart(df, selectedColumns)
    @app.callback(
        Output('corr-chart', 'figure'),
        [Input('corr-dropdown', 'value')])
    def update_corr_chart(selectedColumns):
        return generateChart(df, selectedColumns)
    @app.callback(
        Output('correlation-matrix', 'figure'),
        [Input('correlation-target-dropdown', 'value')])
    def update_correlation_matrix(target_column):
        try:
            return generateCorrelationMatrix(df)
        except Exception as e:
            print(f"Error in update_correlation_matrix: {e}")
            # Optionally, return an empty figure or a figure with an error message
            return go.Figure()
    app.run_server(debug=True)

# MAIN
if __name__ == "__main__":
    createDashboardCorrelations(df, trail1)