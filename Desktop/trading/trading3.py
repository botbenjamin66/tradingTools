import matplotlib.gridspec as gridspec
import matplotlib.pyplot as plt
import yfinance as yf
import seaborn as sns
import pandas as pd
import numpy as np

direction = 'long'
systemApproach = 'trend'

#FUNCTIONS
def createDf():
    columns = ['Date', 'Close', 'longEntryBo', 'longExitBo', 'shortEntryBo', 'shortExitBo',
               'longEntrySignal', 'longExitSignal', 'shortEntrySignal', 'shortExitSignal',
               'longExposure', 'shortExposure', 'totalExposure', 'longReturns', 'shortReturns',
               'longEquity', 'shortEquity', 'totalEquity']
    df = pd.DataFrame(columns=columns)
    df[['longEntryBo', 'longExitBo', 'shortEntryBo', 'shortExitBo',
        'longEntrySignal', 'longExitSignal', 'shortEntrySignal', 'shortExitSignal',
        'longExposure', 'shortExposure', 'totalExposure']] = 0.0
    return df

def downloadDataYf(ticker, backtestStart, endDate, interval):
    df = yf.download(ticker, start=str(backtestStart) + "-01-01", end=str(backtestEnd) + "-01-01", interval= inputDataInterval)
    if df.empty:
        df = yf.download(ticker, start="max", end=str(backtestEnd) + "-01-01", interval=inputDataInterval)
    df = df.drop(columns=['Close'])
    df = df.rename(columns={'Adj Close': 'Close'})
    df.insert(0, 'Close', df.pop('Close'))
    return df

def boSignals(df, trailEntry, trailExit):
    df['longEntryBo'] = np.where(df['Close'] > df['Close'].shift(1).rolling(window=trailEntry).max(), 1, 0)
    df['longExitBo'] = np.where(df['Close'] < df['Close'].shift(1).rolling(window=trailExit).max(), 1, 0)
    df['shortEntryBo'] = np.where(df['Close'] < df['Close'].shift(1).rolling(window=trailEntry).max(), 1, 0)
    df['shortExitBo'] = np.where(df['Close'] > df['Close'].shift(1).rolling(window=trailExit).max(), 1, 0)
    return df

def tradeSignals(df, systemApproach):
    if systemApproach == 'trend':
        df['longEntrySignal'] = np.where(df['longEntryBo'] == 1, 1, 0)
        df['longExitSignal'] = np.where(df['longExitBo'] == 1, 1, 0)
        df['shortEntrySignal'] = np.where(df['shortEntryBo'] == 1, 1, 0)
        df['shortExitSignal'] = np.where(df['shortExitBo'] == 1, 1, 0)
    elif systemApproach == 'reversion':
        df['longEntrySignal'] = np.where(df['longEntryBo'] == 0, 1, 0)
        df['longExitSignal'] = np.where(df['longExitBo'] == 0, 1, 0)
        df['shortEntrySignal'] = np.where(df['shortEntryBo'] == 0, 1, 0)
        df['shortExitSignal'] = np.where(df['shortExitBo'] == 0, 1, 0)
    return df

def exp(df):
    df['longExposure'] = 0
    df['shortExposure'] = 0
    df['totalExposure'] = 0
    df['longExposure'] = np.where(df['longEntrySignal'].shift() == 1, 1, np.where(df['longExitSignal'].shift() == 1, 0, df['longExposure'].shift()))
    df['shortExposure'] = np.where(df['shortEntrySignal'].shift() == 1, 1, np.where(df['shortExitSignal'].shift() == 1, 0, df['shortExposure'].shift()))
    df['totalExposure'] = df['longExposure'] - df['shortExposure']
    return df

def returns(df, commissions, spread, slippage, interest):
    df['longReturns'] = np.where(df['longExposure'] != 0, (df['Close'] - df['Close'].shift()) / df['Close'].shift(), 0)
    df.loc[df['longExposure'].diff() > 0, 'longReturns'] -= (commissions + spread + slippage)
    df.loc[df['longExposure'].diff() < 0, 'longReturns'] -= (interest * len(df[df['longExposure'].diff() != 0].index[-1:]))
    df['shortReturns'] = np.where(df['shortExposure'] != 0, (df['Close'].shift() - df['Close']) / df['Close'].shift(), 0)
    df.loc[df['shortExposure'].diff() > 0, 'shortReturns'] -= (commissions + spread + slippage)
    df.loc[df['shortExposure'].diff() < 0, 'shortReturns'] -= (interest * len(df[df['shortExposure'].diff() != 0].index[-1:]))
    return df

def equity(df):
    df['longEquity'] = (1 + df['longReturns']).cumprod()
    df['shortEquity'] = (1 + df['shortReturns']).cumprod()
    df['totalEquity'] = (1 + (df['longReturns'] + df['shortReturns'])).cumprod()
    return df

def stats(df, backtestStart, backtestEnd):
    testLengthYears = backtestEnd - backtestStart

    if direction == 'long':
        cagr = df['longEquity'].iloc[-1] ** (1 / testLengthYears) - 1
        maxDraw = ((df['longEquity'] - df['longEquity'].cummax()) / df['longEquity'].cummax()).min()
        bliss = cagr / maxDraw if cagr >= 0 else 0
        winRatio = len(df[df['longReturns'] > 0]) / len(df[df['longReturns'] != 0])
        avgWin = df[df['longReturns'] > 0]['longReturns'].mean()
        avgLoss = df[df['longReturns'] < 0]['longReturns'].mean()
        tradesPerYear = len(df[df['longReturns'] != 0]) / testLengthYears
        avgHoldingInInterval = (df['longExposure'] == 1).sum() / len(df[df['longExposure'].diff() != 0])
    elif direction == 'short':
        cagr = df['shortEquity'].iloc[-1] ** (1 / testLengthYears) - 1
        maxDraw = ((df['shortEquity'] - df['shortEquity'].cummax()) / df['shortEquity'].cummax()).min()
        bliss = cagr / maxDraw if cagr >= 0 else 0
        winRatio = len(df[df['shortReturns'] > 0]) / len(df[df['shortReturns'] != 0])
        avgWin = df[df['shortReturns'] > 0]['shortReturns'].mean()
        avgLoss = df[df['shortReturns'] < 0]['shortReturns'].mean()
        tradesPerYear = len(df[df['shortReturns'] != 0]) / testLengthYears
        avgHoldingInInterval = (df['shortExposure'] == 1).sum() / len(df[df['shortExposure'].diff() != 0])
    else:  # direction == 'total'
        cagr = df['totalEquity'].iloc[-1] ** (1 / testLengthYears) - 1
        maxDraw = ((df['totalEquity'] - df['totalEquity'].cummax()) / df['totalEquity'].cummax()).min()
        bliss = cagr / maxDraw if cagr >= 0 else 0
        winRatio = (len(df[df['longReturns'] > 0]) + len(df[df['shortReturns'] > 0])) / (len(df[df['longReturns'] != 0]) + len(df[df['shortReturns'] != 0]))
        avgWin = df[(df['longReturns'] > 0) | (df['shortReturns'] > 0)]['longReturns'].mean()
        avgLoss = df[(df['longReturns'] < 0) | (df['shortReturns'] < 0)]['longReturns'].mean()
        tradesPerYear = (len(df[df['longReturns'] != 0]) + len(df[df['shortReturns'] != 0])) / testLengthYears
        avgHoldingInInterval = ((df['longExposure'] == 1) | (df['shortExposure'] == 1)).sum() / len(df[df['longExposure'].diff() != 0])
    return {
        'cagr': cagr,
        'maxDraw': maxDraw,
        'bliss': bliss,
        'winRatio': winRatio,
        'avgWin': avgWin,
        'avgLoss': avgLoss,
        'tradesPerYear': tradesPerYear,
        'avgHoldingInInterval': avgHoldingInInterval}

#TRADING FRAMEWORK
direction = 'long'
inputDataInterval = '1wk'
backtestStart, backtestEnd = 2017, 2024
commissions, spread, slippage, interest = 0.01, 0.01, 0.01, 0.02
entryPrice, exitPrice = 'Open', 'Close' #Close, Open, High, Low

#TRADE UNIVERSE
tickers = ["^GDAXI"]
ticker_names = {"^GDAXI": "DAX"}
priceData = {}
results = {}
heatmap_values = []

# SYSTEM PARAMETERS
aValues = range(10, 61, 10)
bValues = range(10, 61, 10)

# CALCULATION
for ticker in tickers:
    priceData[ticker] = downloadDataYf(ticker, backtestStart, backtestEnd, inputDataInterval)

    results[ticker] = {}
    dictOfResults = {}
    for a in aValues:
        for b in bValues: 
            df = priceData[ticker].copy()

            trailEntry = a
            trailExit = b

            df = boSignals(df, trailEntry, trailExit)
            df = tradeSignals(df, systemApproach)
            df = exp(df)
            df = returns(df, commissions, spread, slippage, interest)
            df = equity(df)
            parameterStats = stats(df, backtestStart, backtestEnd)
            dictOfResults[(a, b)] = parameterStats
    results[ticker]['parameterStats'] = dictOfResults
    results[ticker]['ticker_name'] = ticker_names[ticker] 

        
# PLOT
heatmapVariables = ['cagr', 'maxDraw', 'bliss']
thirdDimension = 'winRatio'

for ticker in tickers:
    fig = plt.figure(figsize=(20, 10))
    gs = gridspec.GridSpec(2, 3, height_ratios=[2, 1])
    
    ax_index = 0
    for variable in heatmapVariables:
        data = []
        for key, value in results[ticker]['parameterStats'].items():
            a, b = key
            data.append([a, b, value[variable]])
        
        df_heatmap = pd.DataFrame(data, columns=['a', 'b', variable])
        df_heatmap = df_heatmap.pivot("a", "b", variable)

        if ax_index == 0:
            ax = plt.subplot(gs[ax_index], projection='3d')
            x = np.array(df_heatmap.columns)
            y = np.array(df_heatmap.index)
            X, Y = np.meshgrid(x, y)
            Z = np.array(df_heatmap)
            ax.plot_surface(X, Y, Z, cmap='plasma', edgecolor='none')
            ax.set_xlabel('b')
            ax.set_ylabel('a')
            ax.set_zlabel(variable)
        else:
            ax = plt.subplot(gs[ax_index])
            sns.heatmap(df_heatmap, annot=True, fmt=".2f", cmap='plasma', linewidths=.5, ax=ax)
            ax.invert_yaxis()
            ax.set_title(f"{variable} - {results[ticker]['ticker_name']}")
        
        ax_index += 1

    ax2 = plt.subplot(gs[3:])  # Add subplot that spans all columns
    ax2.set_ylabel('currency')
    priceData[ticker]['Close'].plot(ax=ax2)
    ax2.set_title('Closing Prices')
    
    plt.suptitle(f'{direction}', fontsize=16)
    plt.tight_layout()
    plt.show()
