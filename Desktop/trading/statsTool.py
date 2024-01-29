# NEW WIKI DATA MUST BE CLEARED BY HAND FROM " " VIA EXCEL
from dash import dcc, html, Input, Output
import plotly.graph_objects as go
import plotly.express as px
import yfinance as yf
import pandas as pd
import numpy as np
import time
import glob
import dash
import os

# VARIABLES & DICTIONARIES
mode, cutOffDate, trail1, trail2 = 'mac', pd.to_datetime('01.01.2022', format='%d.%m.%Y'), 120, 400

# FETCH & MANIPULATE DATA
def createDfs():
    if mode == 'aramea':
        folderPath = r'W:\Praktikanten und Werkstudenten\Benjamin Suermann\snake'
        filePath = sorted([f for f in glob.glob(f"{folderPath}\\wiki*.csv")], key=os.path.getmtime, reverse=True)
        wikiDataFiles = filePath[:2]
    if mode == 'mac':
        folderPath = "/Users/benjaminsuermann/Downloads"
        filePath = sorted([f for f in glob.glob(f"{folderPath}/*.csv")], key=os.path.getmtime, reverse=False)
        wikiDataFiles = filePath[:2]

    # PRICE DATA
    dfPrice = pd.read_csv(wikiDataFiles[1], sep=';', decimal=',', thousands='.', engine='python', encoding='latin1', skiprows=5)
    dfPrice.drop(dfPrice.columns[1], axis=1, inplace=True)
    dfPrice['Date'] = pd.to_datetime(dfPrice.iloc[:, 0].str[:10], format='%d.%m.%Y')
    dfPrice['Time'] = dfPrice.iloc[:, 0].str[10:].str.strip()
    dfPrice.set_index('Date', inplace=True)
    dfPrice.drop(dfPrice.columns[0], axis=1, inplace=True)
    dfPrice.drop(columns=['Time'], inplace=True)
 
    # TRANSACTION DATA
    dfTransactions = pd.read_csv(wikiDataFiles[0], sep=';', decimal=',', thousands='.', engine='python', encoding='latin1', skiprows=5)
    dfTransactions['Date'] = pd.to_datetime(dfTransactions.iloc[:, 0].str[:10], format='%d.%m.%Y')
    dfTransactions['Time'] = dfTransactions.iloc[:, 0].str[10:].str.strip()
    dfTransactions.set_index('Date', inplace=True)

    # CUTOFF DATE
    dfPrice = dfPrice[dfPrice.index >= cutOffDate]
    dfTransactions = dfTransactions[dfTransactions.index >= cutOffDate]
    dfTransactions.drop(dfTransactions.columns[0], axis=1, inplace=True)
    dfTransactions.insert(0, 'Time', dfTransactions.pop('Time'))

    # RENAME COLUMNS
    transaction_types = ['Wertpapier-Transaktion(Verkauf)', 'Wertpapier-Transaktion(Kauf)']
    dfTransactions = dfTransactions[dfTransactions['Beschreibung'].isin(transaction_types)].replace({
        'Wertpapier-Transaktion(Kauf)': 'buy', 'Wertpapier-Transaktion(Verkauf)': 'sell'}).rename(
        columns={'ÄnderungAnzahl': 'deltaContracts', 'Anzahlnachher': 'Contracts', 'Preis': 'Price', 
                'ÄnderungCash': 'deltaCash', 'Cashnachher': 'Cash'}).filter(regex='^(?!.*Brutto).*$')

    # TRADES PER ISIN
    dfTransactions.sort_values(by=['ISIN', 'Date'], inplace=True)
    dfTransactions['Account'] = dfTransactions.groupby('ISIN')['deltaContracts'].cumsum()
    td = dfTransactions
    isNewIsin = (td['ISIN'] != td['ISIN'].shift()).astype(bool)
    wasAccountZero = (td['Account'].shift() == 0).astype(bool)
    resetTrade = isNewIsin | wasAccountZero
    groupKeys = resetTrade.cumsum()
    td['Trades'] = td.groupby(groupKeys).cumcount() + 1

    # INDEX MAP EQUITY
    dfTransactions['Equity'] = dfTransactions.index.map(dfPrice['Close'])
    dfTransactions['Equity'].ffill(inplace=True)
    dfTransactions['Exposure'] = 1 - ((dfTransactions['Cash'] / 1000) / dfTransactions['Equity'])
    dfTransactions['tradeSize'] = (dfTransactions['deltaCash'] / 1000) / dfTransactions['Equity']

    # COST BASIS
    dfTransactions.reset_index(drop=False, inplace=True)
    dfTransactions['costBasis'] = np.nan
    dfTransactions.loc[dfTransactions['Trades'] == 1, 'costBasis'] = dfTransactions['Price']
    for i, row in dfTransactions.iterrows():
        if row['Trades'] != 1:
            change_amount = row['deltaContracts']
            amount_after = row['Contracts']
            if row['deltaCash'] < 0 and amount_after != 0:
                dfTransactions.at[i, 'costBasis'] = (
                    row['Price'] * (change_amount / amount_after) +
                    dfTransactions.at[i - 1, 'costBasis'] * (1 - (change_amount / amount_after)))
            elif i > 0:
                dfTransactions.at[i, 'costBasis'] = dfTransactions.at[i - 1, 'costBasis']

    # RETURNS
    dfTransactions['percReturnTrade'] = np.where(dfTransactions['deltaCash'] > 0, (dfTransactions['Price'] - dfTransactions['costBasis']) / dfTransactions['costBasis'], np.nan)
    dfTransactions['totalReturnPf'] = dfTransactions['percReturnTrade'] * (dfTransactions['deltaCash'] / (dfTransactions['Equity'] * 100))

    # HOLDING PERIOD
    dfTransactions['holdingInterval'] = np.where(dfTransactions['Trades'] == 1, 0, np.nan)
    for i in range(len(dfTransactions)):
        if dfTransactions.at[i, 'Trades'] > 1:
            lastIndex = dfTransactions[(dfTransactions.index < i) & (dfTransactions['Trades'] == 1)].index.max()
            timeInterval = (dfTransactions.at[i, 'Date'] - dfTransactions.at[lastIndex, 'Date']).days
            dfTransactions.at[i, 'holdingInterval'] = timeInterval

    dfTransactions.set_index('Date', inplace=True)
    dfTransactions.sort_index(inplace=True)

    # STATS
    dfTransactions[f'avgWin{trail1}d'] = dfTransactions['percReturnTrade'].rolling(trail1, min_periods=1).apply(lambda x: np.nanmean(x[x > 0]) if np.any(x > 0) else np.nan)
    dfTransactions[f'avgLoss{trail1}d'] = dfTransactions['percReturnTrade'].rolling(trail1, min_periods=1).apply(lambda x: np.nanmean(x[x < 0]) if np.any(x < 0) else np.nan)
    dfTransactions[f'avgWin{trail2}d'] = dfTransactions['percReturnTrade'].rolling(trail2, min_periods=1).apply(lambda x: np.nanmean(x[x > 0]) if np.any(x > 0) else np.nan)
    dfTransactions[f'avgLoss{trail2}d'] = dfTransactions['percReturnTrade'].rolling(trail2, min_periods=1).apply(lambda x: np.nanmean(x[x < 0]) if np.any(x < 0) else np.nan)
    dfTransactions[f'hitRatio{trail1}d'] = dfTransactions['percReturnTrade'].rolling(trail1, min_periods=1).apply(lambda x: np.sum(x[x > 0]) / np.sum(x) if np.sum(x) != 0 else np.nan)
    dfTransactions[f'hitRatio{trail2}d'] = dfTransactions['percReturnTrade'].rolling(trail2, min_periods=1).apply(lambda x: np.sum(x[x > 0]) / np.sum(x) if np.sum(x) != 0 else np.nan)
    dfTransactions[f'winLossRatio{trail1}d'] = (dfTransactions[f'avgWin{trail1}d'] / -dfTransactions[f'avgLoss{trail1}d']).replace([np.inf, -np.inf], np.nan)
    dfTransactions[f'winLossRatio{trail2}d'] = (dfTransactions[f'avgWin{trail2}d'] / -dfTransactions[f'avgLoss{trail2}d']).replace([np.inf, -np.inf], np.nan)
    dfTransactions[f'annTurnover{trail1}d'] = (dfTransactions['deltaCash'].abs().rolling(trail1).sum() / dfTransactions['Equity'].rolling(trail1).mean()) * (365 / trail1)
    dfTransactions[f'annTurnover{trail2}d'] = (dfTransactions['deltaCash'].abs().rolling(trail2).sum() / dfTransactions['Equity'].rolling(trail2).mean()) * (365 / trail2)
    dfTransactions[f'expectancyValue{trail1}d'] = (dfTransactions[f'hitRatio{trail1}d'] * dfTransactions[f'avgWin{trail1}d']) - ((1 - dfTransactions[f'hitRatio{trail1}d']) * -dfTransactions[f'avgLoss{trail1}d'])
    dfTransactions[f'expectancyValue{trail2}d'] = (dfTransactions[f'hitRatio{trail2}d'] * dfTransactions[f'avgWin{trail2}d']) - ((1 - dfTransactions[f'hitRatio{trail2}d']) * -dfTransactions[f'avgLoss{trail2}d'])
    dfTransactions[f'kelly{trail1}d'] = (dfTransactions[f'hitRatio{trail1}d'] - (1 - dfTransactions[f'hitRatio{trail1}d']) / dfTransactions[f'winLossRatio{trail1}d']).clip(lower=0)
    dfTransactions[f'kelly{trail2}d'] = (dfTransactions[f'hitRatio{trail2}d'] - (1 - dfTransactions[f'hitRatio{trail2}d']) / dfTransactions[f'winLossRatio{trail2}d']).clip(lower=0)

    columns_to_replace = [f'kelly{trail1}d', f'kelly{trail2}d']
    dfTransactions[columns_to_replace] = dfTransactions[columns_to_replace].replace(0, np.nan)

    dfTotal = pd.concat([dfPrice, dfTransactions])

    return dfTotal, dfPrice, dfTransactions
def addSdax(df, cutOffDate):
    sdax = yf.Ticker("^SDAXI").history(start=cutOffDate)[['Close']].round(1)
    sdax.index = sdax.index.date
    sdax.rename(columns={'Close': 'sdax'}, inplace=True)
    df = (df.merge(sdax, left_index=True, right_index=True, how='left')[['sdax'] + [col for col in df.columns if col != 'sdax']])
    df['sdax'].fillna(method='ffill', inplace=True)
    return df

if __name__ == '__main__':
    df = createDfs()[0]
    df = addSdax(df, cutOffDate)

    # DASHBOARD
    dashboardDf = df.drop(columns=['Time', 'Open', 'High', 'Low', 'Beschreibung', 'ISIN', 'deltaContracts', 'Contracts', 'Price', 'Account', 'Trades', 'costBasis'])
    app = dash.Dash(__name__)
    app.layout = html.Div([
        dcc.Dropdown(id='column-dropdown', options=[{'label': col, 'value': col} for col in dashboardDf.columns], value=dashboardDf.columns[0]),
        html.Div(dcc.Graph(id='column-graph', style={'border': '2px solid purple', 'border-radius': '7px'}),
            style={'width': '80%', 'margin': '50px auto'})])
    @app.callback(Output('column-graph', 'figure'), [Input('column-dropdown', 'value')])
    def updateGraph(selected_column):
        fig = px.line(dashboardDf, y=selected_column, line_shape='linear').update_xaxes(title_text='').update_yaxes(title_text='').update_layout(margin=dict(l=100, r=100)).update_traces(line=dict(color='navy'))
        return fig
    app.run_server(debug=True)
