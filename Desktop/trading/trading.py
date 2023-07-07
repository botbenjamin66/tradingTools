import pandas as pd
import numpy as np
import yfinance as yf
import matplotlib.pyplot as plt

#TRADING FRAMEWORK
inputDataInterval = '1wk'
backtestStart = 2015
backtestEnd = 2021

commissions = 0.01
spread = 0.01
slippage = 0.01
interest = 0.0

entryPrice = 'Open' #Close, Open, High, Low
exitPrice = 'Close' #Close, Open, High, Low

results = {}

#TRADE UNIVERSE
tickers = ["^GDAXI", "GBPCHF=X", "GC=F"]
ticker_names = {"^GDAXI": "DAX", "GBPCHF=X": "GBP/CHF", "GC=F": "Gold"}
data_dict = {}

#GET DATA - DATE, OPEN, HIGH, LOW, CLOSE, ADJ CLOSE, VOLUME
for ticker in tickers:
    df = yf.download(ticker, start=str(backtestStart) + "-01-01", end=str(backtestEnd) + "-01-01", interval= inputDataInterval)
    if df.empty:
        df = yf.download(ticker, start="max", end=str(backtestEnd) + "-01-01", interval=inputDataInterval)
    df = df.drop(columns=['Close'])
    df = df.rename(columns={'Adj Close': 'Close'})
    df.insert(0, 'Close', df.pop('Close'))

for x in range(-10, 11, 2):
    longTrailEntry = 10 + x
    longTrailExit = 10 + x
    shortTrailEntry = 10 + x
    shortTrailExit = 10 + x

    df['longEntryBo'] = np.where(df['Close'] > df['Close'].shift(1).rolling(window=longTrailEntry).max(), 1, 0)
    df['longExitBo'] = np.where(df['Close'] < df['Close'].shift(1).rolling(window=longTrailExit).max(), 1, 0)

    df['shortEntryBo'] = np.where(df['Close'] < df['Close'].shift(1).rolling(window=shortTrailEntry).max(), 1, 0)
    df['shortExitBo'] = np.where(df['Close'] > df['Close'].shift(1).rolling(window=longTrailExit).max(), 1, 0)

    # TRADE SIGNALS
    df['longEntrySignal'] = np.where((df['longEntryBo'] == 1), 1, 0)
    df['longExitSignal'] = np.where((df['longExitBo'] == 1), 1, 0)
    df['shortEntrySignal'] = np.where((df['shortEntryBo'] == 1), 1, 0)
    df['shortExitSignal'] = np.where((df['shortExitBo'] == 1), 1, 0)

    #ORGA
    data_dict[ticker_names[ticker]] = df

    #EXPOSURE
    for ticker, df in data_dict.items():
        df['longExposure'] = 0
        df['shortExposure'] = 0
        df['totalExposure'] = 0
        df['longExposure'] = np.where(df['longEntrySignal'].shift() == 1, 1, np.where(df['longExitSignal'].shift() == 1, 0, df['longExposure'].shift()))
        df['shortExposure'] = np.where(df['shortEntrySignal'].shift() == 1, 1, np.where(df['shortExitSignal'].shift() == 1, 0, df['shortExposure'].shift()))
        df['totalExposure'] = df['longExposure'] - df['shortExposure']

    data_dict[ticker] = df

    #RETURNS
    df['longReturns'] = np.where(df['longExposure'] != 0, (df['Close'] - df['Close'].shift()) / df['Close'].shift(), 0)
    df.loc[df['longExposure'].diff() > 0, 'longReturns'] -= (commissions + spread + slippage)
    df.loc[df['longExposure'].diff() < 0, 'longReturns'] -= (interest * len(df[df['longExposure'].diff() != 0].index[-1:]))
    df['shortReturns'] = np.where(df['shortExposure'] != 0, (df['Close'].shift() - df['Close']) / df['Close'].shift(), 0)
    df.loc[df['shortExposure'].diff() > 0, 'shortReturns'] -= (commissions + spread + slippage)
    df.loc[df['shortExposure'].diff() < 0, 'shortReturns'] -= (interest * len(df[df['shortExposure'].diff() != 0].index[-1:]))

    #EQUITY
    df['longEquity'] = (1 + df['longReturns']).cumprod()
    df['shortEquity'] = (1 + df['shortReturns']).cumprod()
    df['totalEquity'] = (1 + (df['longReturns'] + df['shortReturns'])).cumprod()

    #STATS
    testLengthYears = backtestEnd - backtestStart

    cagrLong = df['longEquity'].iloc[-1] ** (1 / (backtestEnd - backtestStart)) - 1
    cagrShort = df['shortEquity'].iloc[-1] ** (1 / (backtestEnd - backtestStart)) - 1
    cagrTotal = df['totalEquity'].iloc[-1] ** (1 / (backtestEnd - backtestStart)) - 1

    maxDrawLong = ((df['longEquity'] - df['longEquity'].cummax()) / df['longEquity'].cummax()).min()
    maxDrawShort = ((df['shortEquity'] - df['shortEquity'].cummax()) / df['shortEquity'].cummax()).min()
    maxDrawTotal = ((df['totalEquity'] - df['totalEquity'].cummax()) / df['totalEquity'].cummax()).min()
    
    blissLong = cagrLong / maxDrawLong  
    blissShort = cagrShort / maxDrawShort
    blissTotal = cagrTotal / maxDrawTotal

    key = (longTrailEntry, longTrailExit, shortTrailEntry, shortTrailExit)
    results[key] = {'CAGR_Long': cagrLong, 'CAGR_Short': cagrShort, 'CAGR_Total': cagrTotal,
                    'Max_Draw_Long': maxDrawLong, 'Max_Draw_Short': maxDrawShort, 'Max_Draw_Total': maxDrawTotal,
                    'Bliss_Long': blissLong, 'Bliss_Short': blissShort, 'Bliss_Total': blissTotal}

results_df = pd.DataFrame(results).T    
# If you want to set the DataFrame column names as the first level of the index:
results_df.index.names = ['longTrailEntry', 'longTrailExit', 'shortTrailEntry', 'shortTrailExit']





'''
#CHARTING
chartingHighlight1 = 'Close'
chartingHighlight2 = 'longEquity'
chartingHighlight3 = 'shortEquity'
chartingHighlight4 = 'totalEquity'

fig, axs = plt.subplots(len(tickers), 5, figsize=(20, 5*len(tickers)))
for i, ticker in enumerate(tickers):
    df = data_dict[ticker_names[ticker]]
    axs[i, 0].plot(df.index, df[chartingHighlight1], color='black', label=chartingHighlight1)
    axs[i, 0].set_title(ticker_names[ticker])
    axs[i, 0].tick_params(axis='x', rotation=45)

    for j in range(1, len(df.index)):
        if df.iloc[j]['longExposure'] > 0:
            color = 'green'
        elif df.iloc[j]['shortExposure'] > 0:
            color = 'red'
        else:
            color = 'blue'
        axs[i, 0].plot(df.index[j-1:j+1], df[chartingHighlight1][j-1:j+1], color=color)

    axs[i, 1].plot(df.index, df[chartingHighlight2], color='black', label=chartingHighlight2)
    axs[i, 1].set_title(chartingHighlight2)
    axs[i, 1].tick_params(axis='x', rotation=45)

    axs[i, 2].plot(df.index, df[chartingHighlight3], color='black', label=chartingHighlight3)
    axs[i, 2].set_title(chartingHighlight3)
    axs[i, 2].tick_params(axis='x', rotation=45)

    axs[i, 3].plot(df.index, df[chartingHighlight4], color='black', label=chartingHighlight4, linestyle='-', marker='')
    axs[i, 3].set_title(chartingHighlight4)
    axs[i, 3].tick_params(axis='x', rotation=45)
    
    axs[i, 4].axis('tight')
    axs[i, 4].axis('off')
    stats = [{'CAGR': cagrLong, 'Max Drawdown': maxDrawLong, 'bliss' : blissLong}, 
             {'CAGR': cagrShort, 'Max Drawdown': maxDrawShort, 'bliss' : blissShort}, 
             {'CAGR': cagrTotal, 'Max Drawdown': maxDrawTotal, 'bliss' : blissTotal}]
    table_data = pd.DataFrame(stats, index=['Long', 'Short', 'Total'])
    axs[i, 4].table(cellText=table_data.values,
                    colLabels=table_data.columns,
                    rowLabels=table_data.index,
                    cellLoc = 'center', loc='center')

plt.subplots_adjust(wspace=0.01)
plt.tight_layout()
plt.show()
'''



