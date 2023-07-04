import pandas as pd
import numpy as np
import yfinance as yf
import matplotlib.pyplot as plt

#TRADE UNIVERSE
tickers = ["^GDAXI", "GBPCHF=X", "GOLD"]
ticker_names = {"^GDAXI": "DAX", "GBPCHF=X": "GBP/CHF", "GOLD": "Gold"}
data_dict = {}

#TRADING FRAMEWORK
inputDataInterval = "1wk" #1d, 1wk, 1mo
backtestStart = 2014
backtestEnd = 2019
forwardtestStart = 2011
forwardtestEnd = 2020

trailStEntry = 2
trailStExit = 2
trailLtEntry = 10
trailLtExit = 10

comissions = 0.01
spread = 0.01
slippage = 0.01
interest = 0.00

entryPrice = "Open" #Close, Open, High, Low
exitPrice = "Open" #Close, Open, High, Low

#DF1 - DATE, OPEN, HIGH, LOW, CLOSE, ADJ CLOSE, VOLUME
for ticker in tickers:
    df = yf.download(ticker, start=str(backtestStart) + "-01-01", end=str(backtestEnd) + "-01-01", interval= inputDataInterval)
    if df.empty:
        df = yf.download(ticker, start="max", end=str(backtestEnd) + "-01-01", interval=inputDataInterval)
    df = df.drop(columns=['Close'])
    df = df.rename(columns={'Adj Close': 'Close'})
    df.insert(0, 'Close', df.pop('Close'))

    df['longEntryBoLt'] = np.where(df['Close'] > df['Close'].shift(1).rolling(window=trailLtEntry).max(), 1, 0)
    df['longExitBoLt'] = np.where(df['Close'] < df['Close'].shift(1).rolling(window=trailLtExit).max(), 1, 0)
    df['shortEntryBoLt'] = np.where(df['Close'] < df['Close'].shift(1).rolling(window=trailLtEntry).max(), 1, 0)
    df['shortExitBoLt'] = np.where(df['Close'] > df['Close'].shift(1).rolling(window=trailLtExit).max(), 1, 0)

    df['longEntryBoSt'] = np.where(df['Close'] > df['Close'].shift(1).rolling(window=trailStEntry).max(), 1, 0)
    df['longExitBoSt'] = np.where(df['Close'] < df['Close'].shift(1).rolling(window=trailStExit).max(), 1, 0)
    df['shortEntryBoSt'] = np.where(df['Close'] < df['Close'].shift(1).rolling(window=trailLtEntry).max(), 1, 0)
    df['shortExitBoSt'] = np.where(df['Close'] > df['Close'].shift(1).rolling(window=trailLtExit).max(), 1, 0)

    df['volumeSpike'] = np.where(df['Volume'] > df['Volume'].shift(1).rolling(window=trailStExit).max(), 1, 0)
    df['volumeVoodoo'] = np.where(df['Volume'] < df['Volume'].shift(1).rolling(window=trailStExit).min(), 1, 0)

    # TRADE SIGNALS
    df['longEntrySignal'] = np.where((df['longEntryBoSt'] == 1) & (df['longEntryBoLt'] == 1), 1, 0)
    df['longExitSignal'] = np.where((df['longExitBoSt'] == 1) & (df['longExitBoLt'] == 1), 1, 0)
    df['shortEntrySignal'] = np.where((df['shortEntryBoSt'] == 1) & (df['shortEntryBoLt'] == 1), 1, 0)
    df['shortExitSignal'] = np.where((df['shortExitBoSt'] == 1) & (df['shortExitBoLt'] == 1), 1, 0)

    #ORGA
    data_dict[ticker_names[ticker]] = df

    for ticker, df in data_dict.items():
        df['longExposure'] = 0
        df['shortExposure'] = 0
        df['totalExposure'] = 0
        df['longExposure'] = np.where(df['longEntrySignal'] == 1, 1, np.where(df['longExitSignal'] == 1, 0, df['longExposure'].shift()))
        df['shortExposure'] = np.where(df['shortEntrySignal'] == 1, 1, np.where(df['shortExitSignal'] == 1, 0, df['shortExposure'].shift()))
        df['totalExposure'] = df['longExposure'] - df['shortExposure']

    data_dict[ticker] = df

    #EQUITY
    df['longExposureChange'] = df['longExposure'].diff()
    lastLongTrade = df['longExposureChange'] != 0
    df['longReturns'] = (df['Close'] - df['Close'].shift().where(lastLongTrade)) / df['Close']

    print(df['longReturns'])

    #PERFORMANCE SHEET (HEATMAP + STATS)

#CHARTING
chartingHighlight1 = 'Close'
chartingHighlight2 = 'longExposure'
chartingHighlight3 = 'shortExposure'
chartingHighlight4 = 'longReturns'

fig, axs = plt.subplots(len(tickers), 4, figsize=(16, 5*len(tickers)))
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

    axs[i, 3].plot(df.index, df[chartingHighlight4], color='black', label=chartingHighlight4)
    axs[i, 3].set_title(chartingHighlight4)
    axs[i, 3].tick_params(axis='x', rotation=45)

    plt.subplots_adjust(wspace=0.01)

plt.tight_layout()
plt.show()

#OPTIMIZATION

#FORWARD TEST

#FINAL ANALYSIS PAPER (HEATMAP & STATS)