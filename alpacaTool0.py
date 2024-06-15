# kelly, abs return cashflow based, trail1 days not rows
# last 10 unique isin, get data, plot chart, plot info, plot trades

# IMPORTS
from matplotlib.dates import DateFormatter
from dash import dcc, html, Input, Output
from plotly.subplots import make_subplots
from scipy.stats import linregress
import plotly.graph_objects as go
import matplotlib.dates as mdates
import matplotlib.pyplot as plt
import plotly.express as px
import yfinance as yf
import pandas as pd
import numpy as np
import dash

# GLOBAL
startDate, endDate = pd.to_datetime('01.05.2021', format='%d.%m.%Y'), pd.to_datetime('today')
trail1 = 50

# DATA
def addSdax(wikiDf, startDate):
    sdax = yf.Ticker("^SDAXI").history(start=startDate)[['Close']].round(1)
    sdax.index = sdax.index.date
    sdax.rename(columns={'Close': 'sdax'}, inplace=True)
    wikiDf = (wikiDf.merge(sdax, left_index=True, right_index=True, how='left')[['sdax'] + [col for col in wikiDf.columns if col != 'sdax']])
    wikiDf['sdax'].fillna(method='ffill', inplace=True)
    return wikiDf
def createWikiDf():
    accountStatementPath = "/Users/benjaminsuermann/Downloads/WF000ARRCC-AccountStatement-20240531205432.csv"
    priceDataPath = "/Users/benjaminsuermann/Downloads/WF000ARRCC-PriceData-20240531205434.csv"

    # PRICE DATA
    wikiPrice = pd.read_csv(priceDataPath, sep=';', decimal=',', thousands='.', engine='python', encoding='latin1', skiprows=5)
    wikiPrice.drop(wikiPrice.columns[1], axis=1, inplace=True)
    wikiPrice['date'] = pd.to_datetime(wikiPrice.iloc[:, 0].str[:10], format='%d.%m.%Y')
    wikiPrice.drop(wikiPrice.columns[0], axis=1, inplace=True)
    wikiPrice.set_index('date', inplace=True)
    wikiPrice = wikiPrice[wikiPrice.index >= startDate]

    # TRANSACTION DATA
    wikiTransactions = pd.read_csv(accountStatementPath, sep=';', decimal=',', thousands='.', engine='python', encoding='latin1', skiprows=5)
    wikiTransactions['date'] = pd.to_datetime(wikiTransactions.iloc[:, 0].str[:10], format='%d.%m.%Y')
    wikiTransactions['time'] = wikiTransactions.iloc[:, 0].str[10:].str.strip()
    wikiTransactions.set_index('date', inplace=True)
    wikiTransactions = wikiTransactions[wikiTransactions.index >= startDate]
    wikiTransactions.drop(wikiTransactions.columns[0], axis=1, inplace=True)
    wikiTransactions.insert(0, 'time', wikiTransactions.pop('time'))

    # MERGE TRANSACTION AND PRICE DATA
    wikiDf = wikiTransactions.merge(wikiPrice, how='inner', left_index=True, right_index=True)
    wikiDf.index = pd.to_datetime(wikiDf.index)
    wikiDf[wikiPrice.columns] = wikiDf[wikiPrice.columns].ffill()

    # ATR
    trueRange = pd.DataFrame({'hl': wikiDf['High'] - wikiDf['Low'], 'hc': abs(wikiDf['High'] - wikiDf['Close'].shift(1)), 'lc': abs(wikiDf['Low'] - wikiDf['Close'].shift(1))})
    wikiDf['tr'] = trueRange.max(axis=1)
    wikiDf['atr'] = wikiDf['tr'].rolling(int(trail1*0.5)).mean()

    # TRADES PER ISIN
    wikiDf.sort_values(by=['ISIN', 'date', 'time'], inplace=True)
    td = wikiDf
    isNewIsin = (td['ISIN'] != td['ISIN'].shift()).astype(bool)
    wasAccountZero = (td['Anzahlnachher'].shift() == 0).astype(bool)
    resetTrade = isNewIsin | wasAccountZero
    groupKeys = resetTrade.cumsum()
    wikiDf['tradeCounter'] = td.groupby(groupKeys).cumcount() + 1

    # EXPOSURE & COST BASIS
    wikiDf['exposure'] = 1 - ((wikiDf['Cashnachher'] / 1000) / wikiDf['Close'])
    wikiDf['ticketSize'] = abs((wikiDf['ÄnderungCash'] / 1000) / wikiDf['Close'])
    wikiDf.reset_index(drop=False, inplace=True)
    wikiDf['costBasis'] = np.nan
    wikiDf.loc[wikiDf['tradeCounter'] == 1, 'costBasis'] = wikiDf['Preis']
    for i, row in wikiDf.iterrows():
        if row['tradeCounter'] != 1:
            changeAmount = row['ÄnderungAnzahl']
            amountAfter = row['Anzahlnachher']
            if row['ÄnderungAnzahl'] < 0 and amountAfter != 0:
                wikiDf.at[i, 'costBasis'] = (
                    row['Preis'] * (changeAmount / amountAfter) +
                    wikiDf.at[i - 1, 'costBasis'] * (1 - (changeAmount / amountAfter)))
            elif i > 0:
                wikiDf.at[i, 'costBasis'] = wikiDf.at[i - 1, 'costBasis']
         
    # RETURNS
    wikiDf['percReturnTrade'] = np.where(wikiDf['Beschreibung'] == 'Wertpapier-Transaktion(Verkauf)', (wikiDf['Preis'] - wikiDf['costBasis']) / wikiDf['costBasis'], np.nan)
    wikiDf['absReturnTrade'] = wikiDf['percReturnTrade'] * (wikiDf['ticketSize'])

    # HOLDING PERIOD
    wikiDf['daysHeld'] = np.where(wikiDf['tradeCounter'] == 1, 0, np.nan)
    for i in range(len(wikiDf)):
        if wikiDf.at[i, 'tradeCounter'] > 1:
            lastIndex = wikiDf[(wikiDf.index < i) & (wikiDf['tradeCounter'] == 1)].index.max()
            timeInterval = (wikiDf.at[i, 'date'] - wikiDf.at[lastIndex, 'date']).days
            wikiDf.at[i, 'daysHeld'] = timeInterval
    
    # ORGANIZE DF
    wikiDf.set_index('date', inplace=True)
    wikiDf.rename(columns={'Beschreibung': 'transactionType', 
                   'ISIN': 'isin', 
                   'ÄnderungAnzahl': 'tradedContracts', 
                   'Anzahlnachher': 'openContracts', 
                   'Preis': 'tradedPrice', 
                   'ÄnderungCash': 'tradedCash', 
                   'Cashnachher': 'openCash', 
                   'Open': 'open', 
                   'Close': 'alpaca', 
                   'High': 'high', 
                   'Low': 'low'}, inplace=True)
    wikiDf.drop(columns=['Preis(Brutto)'], inplace=True)
    dfNewOrder = ['alpaca', 'exposure', 'high', 'low', 'tr', 'atr', 'transactionType', 'time', 'isin', 
                'tradedPrice', 'tradedContracts', 'tradedCash', 'openContracts', 'openCash', 
                'tradeCounter', 'ticketSize', 'costBasis', 'percReturnTrade', 'absReturnTrade', 
                'daysHeld']
    wikiDf = wikiDf.reindex(columns=dfNewOrder)
    
    # SDAX & RETURNS
    wikiDf = addSdax(wikiDf, startDate)
    wikiReturnsDf = wikiDf[~wikiDf.index.duplicated(keep='first')].copy()
    wikiReturnsDf['alpacaDailyReturns'] = wikiReturnsDf['alpaca'].pct_change()
    wikiReturnsDf['sdaxDailyReturns'] = wikiReturnsDf['sdax'].pct_change()
    wikiReturnsDf[f'alpaca{trail1//10}dReturn'] = wikiReturnsDf['alpacaDailyReturns'].rolling(window=trail1//10).sum()
    wikiReturnsDf[f'sdax{trail1//10}dReturn'] = wikiReturnsDf['sdaxDailyReturns'].rolling(window=trail1//10).sum()
    wikiReturnsDf[f'alpacaVolatility{trail1}d'] = wikiReturnsDf['alpacaDailyReturns'].rolling(window=trail1).std() * np.sqrt(trail1)
    wikiReturnsDf[f'sdaxVolatility{trail1}d'] = wikiReturnsDf['sdaxDailyReturns'].rolling(window=trail1).std() * np.sqrt(trail1)
    wikiDf = wikiDf.merge(wikiReturnsDf[['alpacaDailyReturns', 'sdaxDailyReturns', f'alpacaVolatility{trail1}d', f'sdaxVolatility{trail1}d', f'alpaca{trail1//10}dReturn', f'sdax{trail1//10}dReturn']], how='left', left_index=True, right_index=True)
    newColumns = ['alpacaDailyReturns', 'sdaxDailyReturns', f'alpacaVolatility{trail1}d', f'sdaxVolatility{trail1}d', f'alpaca{trail1//10}dReturn', f'sdax{trail1//10}dReturn']
    wikiDf[newColumns] = wikiDf[newColumns].ffill()

    # STATS
    wikiStatsDf = wikiDf.dropna(subset=['percReturnTrade']).copy()
    wikiStatsDf['trTicketSize'] = wikiStatsDf['ticketSize'].rolling(window=trail1).mean()
    wikiStatsDf['trHitRatio'] = wikiStatsDf['percReturnTrade'].rolling(window=trail1).apply(lambda x: (x > 0).sum() / len(x) * 100, raw=True)

    wikiStatsDf['trAvgReturnPerc'] = wikiStatsDf['percReturnTrade'].rolling(window=trail1).mean()
    wikiStatsDf['trAvgWinPerc'] = wikiStatsDf['percReturnTrade'].rolling(window=trail1).apply(lambda x: np.mean(x[x > 0]), raw=True)
    wikiStatsDf['trAvgLossPerc'] = wikiStatsDf['percReturnTrade'].rolling(window=trail1).apply(lambda x: np.mean(x[x < 0]), raw=True)
    wikiStatsDf['trExpValuePerc'] =  (wikiStatsDf['trAvgWinPerc'] * wikiStatsDf['trHitRatio'] / 100 - wikiStatsDf['trAvgLossPerc'] * (1 - wikiStatsDf['trHitRatio'] / 100)).rolling(window=trail1).mean()
    wikiStatsDf['trAvgReturnAbs'] = wikiStatsDf['absReturnTrade'].rolling(window=trail1).mean()
    wikiStatsDf['trAvgWinAbs'] = wikiStatsDf['absReturnTrade'].rolling(window=trail1).apply(lambda x: np.mean(x[x > 0]), raw=True)
    wikiStatsDf['trAvgLossAbs'] = wikiStatsDf['absReturnTrade'].rolling(window=trail1).apply(lambda x: np.mean(x[x < 0]), raw=True)
    wikiStatsDf['trExpValueAbs'] =  (wikiStatsDf['trAvgWinAbs'] * wikiStatsDf['trHitRatio'] / 100 - wikiStatsDf['trAvgLossAbs'] * (1 - wikiStatsDf['trHitRatio'] / 100)).rolling(window=trail1).mean()
    wikiStatsDf['trAvgRiskReturnPerc'] = wikiStatsDf['trAvgWinPerc'] / wikiStatsDf['trAvgLossPerc']
    wikiStatsDf['trAvgRiskReturnAbs'] = wikiStatsDf['trAvgWinAbs'] / wikiStatsDf['trAvgLossAbs']
    wikiStatsDf['trKelly'] = wikiStatsDf['trHitRatio'] - (1 - wikiStatsDf['trHitRatio']) / wikiStatsDf['trAvgRiskReturnPerc']
    
    # trades per day
    # transaction cost
    # fix fee cost
    
    wikiDf = wikiDf.merge(wikiStatsDf[['trTicketSize', 'trHitRatio', 'trAvgReturnPerc', 'trAvgWinPerc', 'trAvgLossPerc', 'trExpValuePerc', 'trAvgReturnAbs', 'trAvgWinAbs', 'trAvgLossAbs', 'trExpValueAbs', 'trAvgRiskReturnPerc', 'trAvgRiskReturnAbs', 'trKelly']], how='left', left_index=True, right_index=True)
    newColumns = ['trTicketSize', 'trHitRatio', 'trAvgReturnPerc', 'trAvgWinPerc', 'trAvgLossPerc', 'trExpValuePerc', 'trAvgReturnAbs', 'trAvgWinAbs', 'trAvgLossAbs', 'trExpValueAbs', 'trAvgRiskReturnPerc', 'trAvgRiskReturnAbs', 'trKelly']
    wikiDf[newColumns] = wikiDf[newColumns].ffill()
    return wikiDf

def dashStats():
    wikiDf=createWikiDf()
    dropdownOptions=[{'label':col,'value':col}for col in wikiDf.columns if col not in['alpaca', 'sdax', 'high', 'low', 'exposure', 'isin', 'ticketSize', 'atr', 'tr', 'tradedPrice', 'transactionType', 'percReturnTrade', 'tradedContracts', 'daysHeld', 'tradeCounter', 'tradedCash', 'openContracts', 'openCash', 'costBasis', 'alpacaDailyReturns', 'sdaxDailyReturns', f'alpacaVolatility{trail1}d', f'sdaxVolatility{trail1}d', f'alpaca{trail1//10}dReturn', f'sdax{trail1//10}dReturn']]
    dropdownOptions.extend([{'label': 'performance', 'value': 'performance'}, {'label': 'risk', 'value': 'risk'}, {'label': 'range', 'value': 'range'}, {'label': 'vola', 'value': 'vola'}, {'label': 'returns', 'value': 'returns'}, {'label': 'sitting', 'value': 'sitting'}, {'label': 'correlation', 'value': 'correlation'}])

    app=dash.Dash(__name__)
    app.layout=html.Div([
        html.Div([dcc.Dropdown(id='dropdown',options=dropdownOptions, multi=False,
                value=wikiDf.columns[0],)],style={'width':'50%','margin':'auto', 'background-color': 'lila'}),dcc.Graph(id='graph'),])

    @app.callback(Output('graph', 'figure'), [Input('dropdown', 'value')])
    def updateGraph(selectedColumn):
        if selectedColumn   == 'performance':
            alpacaReturns = (wikiDf['alpaca'] / wikiDf['alpaca'].iloc[0] - 1) * 100
            sdaxReturns = (wikiDf['sdax'] / wikiDf['sdax'].iloc[0] - 1) * 100
            return {'data': [{'x': wikiDf.index, 'y': alpacaReturns, 'mode': 'lines', 'name': 'alpaca'}, {'x': wikiDf.index, 'y': sdaxReturns, 'mode': 'lines', 'name': 'sdax'}],
                'layout': {'hovermode': 'closest'}}
        elif selectedColumn == 'risk':
            return {'data': [{'x': wikiDf.index, 'y': wikiDf['exposure'].rolling(window=trail1).mean(), 'mode': 'lines', 'name': f'exposure{trail1}d'},
                    {'x': wikiDf.index, 'y': wikiDf['atr'], 'mode': 'lines', 'name': f'atr{trail1}d', 'yaxis': 'y2'}],
                'layout': {'hovermode': 'closest', 'yaxis2': {'title': 'Low', 'overlaying': 'y', 'side': 'right'}}}
        elif selectedColumn == 'range':
            return {'data': [{'x': wikiDf.index, 'y': wikiDf['high'], 'mode': 'lines', 'name': 'High'},
                            {'x': wikiDf.index, 'y': wikiDf['low'], 'mode': 'lines', 'name': 'Low'}],'layout': {'hovermode': 'closest'}}
        elif selectedColumn == 'vola':
            return {'data': [{'x': wikiDf.index, 'y': wikiDf[f'alpacaVolatility{trail1}d'], 'mode': 'lines', 'name': 'alpaca'},
                            {'x': wikiDf.index, 'y': wikiDf[f'sdaxVolatility{trail1}d'], 'mode': 'lines', 'name': 'sdax'}],'layout': {'hovermode': 'closest'}}
        elif selectedColumn == 'returns':
            return {'data': [
                    {'x': wikiDf.index, 'y': wikiDf['alpacaDailyReturns'], 'mode': 'markers', 'marker': {'color': 'navy', 'symbol': 'circle', 'size': 7}, 'name': 'alpaca'},
                    {'x': wikiDf.index, 'y': wikiDf['sdaxDailyReturns'], 'mode': 'markers', 'marker': {'color': 'violet', 'symbol': 'circle', 'size': 7}, 'name': 'sdax'},
                    {'x': wikiDf.index, 'y': wikiDf[f'alpaca{trail1//10}dReturn'], 'mode': 'lines', 'line': {'color': 'navy', 'width': 2}, 'name': 'alpaca'},
                    {'x': wikiDf.index, 'y': wikiDf[f'sdax{trail1//10}dReturn'], 'mode': 'lines', 'line': {'color': 'violet', 'width': 2}, 'name': 'sdax'}],
                    'layout': {'hovermode': 'closest'}}
        elif selectedColumn == 'time':
            if not pd.api.types.is_datetime64_any_dtype(wikiDf['time']):
                wikiDf['time'] = pd.to_datetime(wikiDf['time'])
            buysDf = wikiDf[wikiDf['transactionType'] == 'Wertpapier-Transaktion(Kauf)']
            sellsDf = wikiDf[wikiDf['transactionType'] == 'Wertpapier-Transaktion(Verkauf)']
            buysDf = buysDf.sort_values(by='time')
            sellsDf = sellsDf.sort_values(by='time')
            buysHist = go.Histogram(x=buysDf['time'], name='Buys')
            sellsHist = go.Histogram(x=sellsDf['time'], name='Sells')
            fig = make_subplots(rows=2, cols=1, shared_xaxes=True, subplot_titles=('Buys', 'Sells'))
            fig.add_trace(buysHist, row=1, col=1)
            fig.add_trace(sellsHist, row=2, col=1)
            return fig
        elif selectedColumn == 'sitting':
            histData = wikiDf['daysHeld']
            hist = go.Histogram(x=histData, histnorm='probability density', nbinsx=30, name='daysHeld')
            bins = np.histogram_bin_edges(histData, bins=30)
            print(f"Bins: {bins}")
            wikiDf['daysHeldBin'] = pd.cut(wikiDf['daysHeld'], bins=bins, labels=False, include_lowest=True)
            print(f"Binned Data:\n{wikiDf[['daysHeld', 'daysHeldBin']].head()}")
            binAverages = wikiDf.groupby('daysHeldBin')['percReturnTrade'].mean()
            binAverages = binAverages.dropna()
            print(f"Bin Averages:\n{binAverages}")
            binCenters = (bins[:-1] + bins[1:]) / 2
            print(f"Bin Centers: {binCenters}")
            binCenters = binCenters[binAverages.index]
            line = go.Scatter(x=binCenters, y=binAverages, mode='lines+markers', name='avgPnl', line=dict(color='black'))
            fig = make_subplots(specs=[[{"secondary_y": True}]])
            fig.add_trace(hist, secondary_y=False)
            fig.add_trace(line, secondary_y=True)
            fig.update_layout(hovermode='closest', yaxis_ticksuffix='%', yaxis_tickvals=[0.001, 0.01, 0.12], yaxis_ticktext=['0.1%', '1%', '12%'])
            return fig
        elif selectedColumn in ['absReturnTrade']:
            hist_data = wikiDf[selectedColumn]
            fig = go.Figure(data=go.Histogram(x=hist_data, histnorm='probability density'))
            if selectedColumn != 'transactionType':
                fig.update_layout(yaxis_type='log')
            fig.update_layout(hovermode='closest')
            return fig
        elif selectedColumn == 'correlation':
            return {
                'data': [{'x': wikiDf['alpacaDailyReturns'],'y': wikiDf['sdaxDailyReturns'], 'mode': 'markers',
                        'marker': {'color': 'navy', 'symbol': 'circle', 'size': 4}, 'name': 'alpaca vs sdax'}],
                'layout': {'xaxis': {'title': 'Alpaca Daily Returns'}, 'yaxis': {'title': 'SDAX Daily Returns'}}}
        else:
            return {'data':[{'x':wikiDf.index,'y':wikiDf[selectedColumn],'mode':'lines','name':selectedColumn}],
                'layout':{'xaxis':{'title':'Date'}}}
    app.run_server(debug=True)
def dashTrades():
    wikiDf = createWikiDf()
    
    wikiDf = wikiDf[(wikiDf.index[-1] - pd.Timedelta(days=trail1)):]
    isins = wikiDf['isin'].unique()
    
    for isin in isins:
        try:
            ticker = yf.Ticker(isin)
            hist_data = ticker.history(start=(wikiDf.index[-1] - pd.Timedelta(days=trail1*2)), end=None, interval="1d", actions=False, auto_adjust=True, back_adjust=False)
            stock_name = ticker.info['longName']
            #print(f"Stock: {stock_name}")
            print(hist_data)
            print("=" * 50)
        except ValueError as ve:
            print(f"ValueError fetching data for ISIN {isin}: {str(ve)}")
        except KeyError as ke:
            print(f"KeyError fetching data for ISIN {isin}: {str(ke)}")
        except Exception as e:
            print(f"Error fetching data for ISIN {isin}: {str(e)}")


###
#dashStats()
dashTrades()