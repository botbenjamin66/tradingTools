from dash.dependencies import Input, Output
from datetime import datetime, timedelta
import plotly.graph_objs as go
from dash import dcc, html
import yfinance as yf
import pandas as pd
import numpy as np
import pytz
import dash

### PORTFOLIOS
test = [
    ("ETH-USD", 49, 21, 49, 7, 100, 91, 7.7),
    ("BTC-USD", 55, 20, 60, 26, 300, 84, 2.8),
    ("GC=F", 60, 20, 60, 20, 21, 57, 4.5)]
Q12024 = [
    ("ETH-USD", 49, 21, 49, 7, 100, 91, 7.7),
    ("BTC-USD", 55, 20, 60, 26, 300, 84, 2.8),
    ("GC=F", 60, 20, 60, 20, 21, 57, 4.5),
    ("SI=F", 70, 21, 94, 14, 3, 44, 3.9),
    ("CL=F", 70, 21, 94, 14, 51, 54, 4.0),
    ("QQQ", 40, 21, 87, 17, 50, 73, 4.9),
    ("^N225", 29, 21, 83, 16, 18, 60, 4.7),
    ("GS", 60, 20, 60, 20, 20, 57, 4.6),
    ("NVDA", 70, 21, 94, 14, 66, 61, 3.6),
    ("PLTR", 70, 21, 94, 14, 46, 45, 3.4),
    ("GLEN.L", 63, 21, 63, 21, 30, 53, 3.9),
    
    ("MODG", 21, 7, 0, 0, 82, 73, 7.2),
    ("INFL.PA", 40, 60, 0, 0, 0, 66, 1.5),
    ("USTP.DE", 60, 20, 0, 0, 0, 39, 3.0),
    ("LVO.AS", 33, 2, 0, 0, 35, 83, 4.1),
    ("EURCHF=X", 0, 0, 40, 60, 0, 46, 1.3)]

### FUNCTIONS
def calculateSystem(tickerPriceData, longIn, longOut, shortIn, shortOut, trail):
    
    tickerPriceData['longInLevel'] = tickerPriceData[triggerPrice1].shift(1).rolling(window=longIn).max()
    tickerPriceData['longOutLevel'] = tickerPriceData[triggerPrice1].shift(1).rolling(window=longOut).min()
    tickerPriceData['shortInLevel'] = tickerPriceData[triggerPrice1].shift(1).rolling(window=shortIn).min()
    tickerPriceData['shortOutLevel'] = tickerPriceData[triggerPrice1].shift(1).rolling(window=shortOut).max()

    tickerPriceData['longIn'] = tickerPriceData[triggerPrice1].gt(tickerPriceData[triggerPrice1].shift(1).rolling(window=longIn).max())
    tickerPriceData['longOut'] = tickerPriceData[triggerPrice1].lt(tickerPriceData[triggerPrice1].shift(1).rolling(window=longOut).min())
    tickerPriceData['shortIn'] = tickerPriceData[triggerPrice1].lt(tickerPriceData[triggerPrice1].shift(1).rolling(window=shortIn).min())
    tickerPriceData['shortOut'] = tickerPriceData[triggerPrice1].gt(tickerPriceData[triggerPrice1].shift(1).rolling(window=shortOut).max())

    if not (tickerPriceData['longIn'].any() or tickerPriceData['longOut'].any()):
        tickerPriceData['longExposure'] = 0
    else:
        conditions = [tickerPriceData['longIn'], tickerPriceData['longOut']]
        choices = [1, -1]
        tickerPriceData['deltaExposure'] = np.select(conditions, choices, 0)
        tickerPriceData['longExposure'] = tickerPriceData['deltaExposure'].cumsum()
        indexList = tickerPriceData.index.tolist()
        for i in range(1, len(tickerPriceData)):
            previousIndex, currentIndex = indexList[i-1], indexList[i]
            newValue = min(1, max(0, tickerPriceData.at[previousIndex, 'longExposure'] + tickerPriceData.at[currentIndex, 'deltaExposure']))
            tickerPriceData.at[currentIndex, 'longExposure'] = newValue

    if not (tickerPriceData['shortIn'].any() or tickerPriceData['shortOut'].any()):
        tickerPriceData['shortExposure'] = 0
    else:
        conditions = [tickerPriceData['shortIn'], tickerPriceData['shortOut']]
        choices = [-1, 1]
        tickerPriceData['deltaExposure'] = np.select(conditions, choices, 0)
        tickerPriceData['shortExposure'] = tickerPriceData['deltaExposure'].cumsum()
        indexList = tickerPriceData.index.tolist()
        for i in range(1, len(tickerPriceData)):
            previousIndex, currentIndex = indexList[i-1], indexList[i]
            newValue = max(-1, min(0, tickerPriceData.at[previousIndex, 'shortExposure'] + tickerPriceData.at[currentIndex, 'deltaExposure']))
            tickerPriceData.at[currentIndex, 'shortExposure'] = newValue
    
    # EXPSOURE & PORTFOLIO VALUE
    tickerPriceData['exposure'] = tickerPriceData['longExposure'] + tickerPriceData['shortExposure']
    tickerPriceData['deltaExposure'] = tickerPriceData['exposure'].diff()
    tickerPriceData['exposure'] = tickerPriceData['exposure'].apply(lambda x: 'Long' if x > 0 else ('Short' if x < 0 else 'Neutral'))
    tickerPriceData['deltaExposure'] = tickerPriceData['deltaExposure'].apply(lambda x: 'Buy' if x > 0 else ('Sell' if x < 0 else 'No Trade'))

### INIT
alpacaEquity, heat = 109, 0.01
selectedPortfolio, lookbackPeriod, tickerExposureDataDict, triggerPrice1, trail = Q12024, 600, {}, 'Close', 21
tradingPlan = pd.DataFrame(selectedPortfolio, columns=['ticker', 'longIn', 'longOut', 'shortIn', 'shortOut', 'bliss', 'hitRatio', 'tpy'])
startDate, endDate = (datetime.today() - timedelta(days=lookbackPeriod)).strftime('%Y-%m-%d'), datetime.today().strftime('%Y-%m-%d')

### DOWNLOAD DATA
tickerExposureDataDict = {}
for _, row in tradingPlan.iterrows():
    ticker, longIn, longOut, shortIn, shortOut, bliss, hitRatio, tpy = row[['ticker', 'longIn', 'longOut', 'shortIn', 'shortOut', 'bliss', 'hitRatio', 'tpy']]

    tickerPriceData = yf.download(ticker, start=startDate, end=endDate)
    mostCurrentPrice = yf.download(ticker, start=(datetime.now() - timedelta(days=1)).strftime('%Y-%m-%d'), interval='1m')['Close'].iloc[-1]
    calculateSystem(tickerPriceData, longIn, longOut, shortIn, shortOut, trail)

    tickerExposureDataDict[ticker] = {
        'tradingPlan': {'longIn': longIn, 'longOut': longOut, 'shortIn': shortIn, 'shortOut': shortOut, 'bliss': bliss, 'hitRatio': hitRatio, 'tpy': tpy},
        'tickerPriceData': tickerPriceData, 'mostCurrentPrice': mostCurrentPrice}

### DASHBOARD
app = dash.Dash(__name__)
app.layout = html.Div(
    style={'background-color': 'white', 'padding': '20px', 'font-family': 'Consolas', 'color': 'black'},
    children=[
        html.H1("alpaca", style={"color": "black", "text-align": "center"}),
        dcc.Dropdown(id='tickerDropdown', options=[{'label': ticker, 'value': ticker} for ticker in tickerExposureDataDict.keys()],
                     value=list(tickerExposureDataDict.keys())[0], style={'background-color': 'white', 'color': 'black'}),
        dcc.Dropdown(id='tracebackDropdown', options=[{'label': 'Market', 'value': 'Market'},
                                                      {'label': 'Long', 'value': 'Long'},
                                                      {'label': 'Short', 'value': 'Short'},
                                                      {'label': 'Trading', 'value': 'Trading'}],
                     value='Market', style={'background-color': 'white', 'color': 'black'}),
        dcc.Graph(id='priceGraph', config={'displayModeBar': False}, style={'height': '400px'}),
        html.Table([
            html.Tr([html.Td('Price', style={'font-weight': 'bold', 'color': 'black'}), html.Td(id='priceValue')]),
            html.Tr([html.Td('Exposure', style={'font-weight': 'bold', 'color': 'black'}), html.Td(id='exposureValue')]),
            html.Tr([html.Td('Long In', style={'font-weight': 'bold', 'color': 'black'}), html.Td(id='longInPrice')]),
            html.Tr([html.Td('Long Out', style={'font-weight': 'bold', 'color': 'black'}), html.Td(id='longOutPrice')]),
            html.Tr([html.Td('Short In', style={'font-weight': 'bold', 'color': 'black'}), html.Td(id='shortInPrice')]),
            html.Tr([html.Td('Short Out', style={'font-weight': 'bold', 'color': 'black'}), html.Td(id='shortOutPrice')]),
            html.Tr([html.Td('% to stop', style={'font-weight': 'bold', 'color': 'black'}), html.Td(id='percentToStop')]),
            html.Tr([html.Td('Last Update', style={'font-weight': 'bold', 'color': 'black'}), html.Td(id='lastUpdate')]),
            html.Tr([html.Td('Alpaca', style={'font-weight': 'bold', 'color': 'black'}), html.Td(alpacaEquity)]),
            html.Tr([html.Td('Size', style={'font-weight': 'bold', 'color': 'black'}), html.Td(id='bruttoEntrySize')])
        ], style={'border': '1px solid black', 'width': '20%'})])
@app.callback(
    [Output('priceGraph', 'figure'), Output('priceValue', 'children'),
     Output('exposureValue', 'children'), Output('longInPrice', 'children'),
     Output('longOutPrice', 'children'), Output('shortInPrice', 'children'),
     Output('shortOutPrice', 'children'), Output('percentToStop', 'children'),
     Output('lastUpdate', 'children'), Output('bruttoEntrySize', 'children')],
    [Input('tickerDropdown', 'value'), Input('tracebackDropdown', 'value')])
def updateGraph(selectedTicker, tracebackFilter):
    tickerData = tickerExposureDataDict[selectedTicker]
    tickerPriceData, tradingPlan = tickerData['tickerPriceData'], tickerData['tradingPlan']
    longIn, longOut, shortIn, shortOut = tradingPlan['longIn'], tradingPlan['longOut'], tradingPlan['shortIn'], tradingPlan['shortOut']
    traces = []

    if tracebackFilter == 'Long':
        traces.extend([
            go.Scatter(x=tickerPriceData.index, y=tickerPriceData['Close'].rolling(window=longIn).max(), mode='lines', name=f'{selectedTicker} {longIn} Long In', line=dict(color='green')),
            go.Scatter(x=tickerPriceData.index, y=tickerPriceData['Close'].rolling(window=longOut).min(), mode='lines', name=f'{selectedTicker} {longOut} Long Out', line=dict(color='red'))])
    elif tracebackFilter == 'Short':
        traces.extend([
            go.Scatter(x=tickerPriceData.index, y=tickerPriceData['Close'].rolling(window=shortIn).min(), mode='lines', name=f'{selectedTicker} {shortIn} Short In', line=dict(color='blue')),
            go.Scatter(x=tickerPriceData.index, y=tickerPriceData['Close'].rolling(window=shortOut).max(), mode='lines', name=f'{selectedTicker} {shortOut} Short Out', line=dict(color='black'))])
    elif tracebackFilter == 'Trading':
        longExposure = np.where(tickerPriceData['exposure'] == 'Long', tickerPriceData['Close'], np.nan)
        shortExposure = np.where(tickerPriceData['exposure'] == 'Short', tickerPriceData['Close'], np.nan)
        traces.extend([
            go.Scatter(x=tickerPriceData.index, y=tickerPriceData['Close'], mode='lines', name='Close', line=dict(color='white')),
            go.Scatter(x=tickerPriceData.index, y=longExposure, mode='lines', name='LongExposure', line=dict(color='green')),
            go.Scatter(x=tickerPriceData.index, y=shortExposure, mode='lines', name='ShortExposure', line=dict(color='red'))])

    exposure = tickerPriceData['exposure'].iloc[-1]
    longInPrice, longOutPrice, shortInPrice, shortOutPrice = 'N/A', 'N/A', 'N/A', 'N/A'
    longInPrice = round(tickerPriceData['longInLevel'].iloc[-1], 3)
    longOutPrice = round(tickerPriceData['longOutLevel'].iloc[-1], 3)
    shortInPrice = round(tickerPriceData['shortInLevel'].iloc[-1], 3)
    shortOutPrice = round(tickerPriceData['shortOutLevel'].iloc[-1], 3)

    percentToStop = 'N/A'
    mostCurrentClose = tickerExposureDataDict[selectedTicker]['mostCurrentPrice']
    if not pd.isna(mostCurrentClose):
        if exposure == 'Long':
            percentToStop = round(((mostCurrentClose - longOutPrice) / mostCurrentClose) * 100, 4)
        elif exposure == 'Short':
            percentToStop = round(((shortOutPrice - mostCurrentClose) / mostCurrentClose) * 100, 4)

    lastUpdate = tickerPriceData.index[-1].strftime('%Y-%m-%d')
    layout = go.Layout(xaxis_rangeslider_visible=False, xaxis={'title': ' ', 'showgrid': False}, yaxis={'title': ' ', 'range': [tickerPriceData['Close'].min(), tickerPriceData['Close'].max()]})
    bruttoEntrySize = '' if percentToStop == 'N/A' else round((heat / percentToStop) * alpacaEquity * 100, 4)

    if tracebackFilter == 'Trading':
        return {'data': traces, 'layout': layout}, round(tickerPriceData['Close'].iloc[-1], 3), exposure, longInPrice, longOutPrice, shortInPrice, shortOutPrice, percentToStop, lastUpdate, bruttoEntrySize
    else:
        priceTrace = go.Candlestick(x=tickerPriceData.index, open=tickerPriceData['Open'], high=tickerPriceData['High'], low=tickerPriceData['Low'], close=tickerPriceData['Close'])
        return {'data': traces + [priceTrace], 'layout': layout}, round(tickerPriceData['Close'].iloc[-1], 3), exposure, longInPrice, longOutPrice, shortInPrice, shortOutPrice, percentToStop, lastUpdate, bruttoEntrySize

if __name__ == '__main__':
    app.run_server(debug=True)