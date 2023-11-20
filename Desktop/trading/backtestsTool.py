import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from createTool import dataFactory

# SETTINGS
tickers = ["SGL.DE", "AIXA.DE"]
startDate, endDate, interval = "2021-01-01", "2023-01-01", "1d"

trail, triggerPrice, tradePrice = 10, 'Close', 'Open'
signalParams = {'longEntry': 20, 'longExit': 10, 'shortEntry': 20, 'shortExit': 10}
tradeCosts = {'commissions': 0.001, 'spread': 0.001, 'slippage': 0.001, 'interest': 0.02, 'nominalUSD': 100}
buySize, sellSize, maxLeverage = 1, 1, 1

factory = dataFactory()
dataObjects = {}

# SIGNAL FUNCTIONS
def signalTrendLong(df, triggerPrice, longEntry, longExit):
    df['longEntry'] = df[triggerPrice].gt(df[triggerPrice].shift(1).rolling(window=longEntry).max())
    df['longExit'] = df[triggerPrice].lt(df[triggerPrice].shift(1).rolling(window=longExit).min())
    df['shortEntry'] = False
    df['shortExit'] = False
def signalTrendShort(df, triggerPrice, shortEntry, shortExit):
    df['longEntry'] = False
    df['longExit'] = False
    df['shortEntry'] = df[triggerPrice].lt(df[triggerPrice].shift(1).rolling(window=shortEntry).min())
    df['shortExit'] = df[triggerPrice].gt(df[triggerPrice].shift(1).rolling(window=shortExit).max())
def signalTrendTotal(df, triggerPrice, longEntry, longExit, shortEntry, shortExit):
    df['longEntry'] = df[triggerPrice].gt(df[triggerPrice].shift(1).rolling(window=longEntry).max())
    df['longExit'] = df[triggerPrice].lt(df[triggerPrice].shift(1).rolling(window=longExit).min())
    df['shortEntry'] = df[triggerPrice].lt(df[triggerPrice].shift(1).rolling(window=shortEntry).min())
    df['shortExit'] = df[triggerPrice].gt(df[triggerPrice].shift(1).rolling(window=shortExit).max())
def signalReversionTotal(df, triggerPrice, longEntry, longExit, shortEntry, shortExit):
    df['longEntry'] = df[triggerPrice].lt(df[triggerPrice].shift(1).rolling(window=longEntry).min())
    df['longExit'] = df[triggerPrice].gt(df[triggerPrice].shift(1).rolling(window=longExit).max())
    df['shortEntry'] = df[triggerPrice].gt(df[triggerPrice].shift(1).rolling(window=shortEntry).max())
    df['shortExit'] = df[triggerPrice].lt(df[triggerPrice].shift(1).rolling(window=shortExit).min())

# DATA OBJECTS
for ticker in tickers:
    dataObject = factory.createData("yfinance", ticker, startDate, endDate, interval)
    data = dataObject.fetchData()
    dataObjects[ticker] = data

# FEATURES
for ticker, df in dataObjects.items():
    df['volume' + str(trail)] = df['Volume'].rolling(window=trail).mean()
    df['ema' + str(trail)] = df[triggerPrice].ewm(span=trail).mean()
    df['er' + str(trail)] = df[triggerPrice].diff(trail).abs() / df[triggerPrice].diff().abs().rolling(window=trail).sum()

# SIGNALS
for ticker, df in dataObjects.items():
    signalTrendTotal(df, triggerPrice, **signalParams)

# EXPOSURE
for ticker, df in dataObjects.items():
    if not (df['longEntry'].any() or df['longExit'].any()):
        df['longExposure'] = 0
    else:
        conditions = [df['longEntry'], df['longExit']]
        choices = [buySize, -sellSize]
        df['deltaExposure'] = np.select(conditions, choices, 0)
        df['longExposure'] = df['deltaExposure'].cumsum()
        for i in range(1, len(df)):
            previousIndex = df.index[i - 1]
            currentIndex = df.index[i]
            newValue = min(maxLeverage, max(0, df.at[previousIndex, 'longExposure'] + df.at[currentIndex, 'deltaExposure']))
            df.at[currentIndex, 'longExposure'] = newValue

    if not (df['shortEntry'].any() or df['shortExit'].any()):
        df['shortExposure'] = 0
    else:
        conditions = [df['shortEntry'], df['shortExit']]
        choices = [-buySize, sellSize]
        df['deltaExposure'] = np.select(conditions, choices, 0)
        df['shortExposure'] = df['deltaExposure'].cumsum()
        for i in range(1, len(df)):
            previousIndex = df.index[i - 1]
            currentIndex = df.index[i]
            newValue = max(-maxLeverage, min(0, df.at[previousIndex, 'shortExposure'] + df.at[currentIndex, 'deltaExposure']))
            df.at[currentIndex, 'shortExposure'] = newValue

    df['exposure'] = df['longExposure'] + df['shortExposure']
    df['deltaExposure'] = df['exposure'].diff()

# RETURNS
for ticker, df in dataObjects.items():
    costPerTrade = tradeCosts['commissions'] + tradeCosts['spread'] + tradeCosts['slippage']

    # PERFORMANCE METRICS
    df['interestCost'] = abs(df['exposure']) * tradeCosts['interest'] * (df.index.to_series().diff().dt.days / 365)
    df['marketReturns'] = df[triggerPrice].pct_change()
    df['percentageReturns'] = df['exposure'].shift() * df[tradePrice].pct_change()
    df['percentageReturnsAC'] = df['percentageReturns'] - abs(np.where(df['exposure'].diff() != 0, costPerTrade * df['exposure'], 0)) - abs(df['exposure']) * tradeCosts['interest'] * (df.index.to_series().diff().dt.days / 365)
    df['nominal'] = (1 + df['percentageReturns']).cumprod() * tradeCosts['nominalUSD']
    df['nominalAC'] = (1 + df['percentageReturnsAC']).cumprod() * tradeCosts['nominalUSD']
    df['nominalNakedAC'] = tradeCosts['nominalUSD'] + (tradeCosts['nominalUSD'] * df['percentageReturnsAC'].cumsum())

    # COST BASIS
    for i in range(len(df)):
        curExposure = df.iloc[i]['exposure']
        prevExposure = df.iloc[i-1]['exposure'] if i > 0 else np.nan
        curTradePrice = df.iloc[i][tradePrice]

        if curExposure == 0:
            df.at[df.index[i], 'costBasis'] = 0
        elif prevExposure == 0 and curExposure != 0:
            df.at[df.index[i], 'costBasis'] = curTradePrice
        elif prevExposure != 0 and abs(curExposure) > abs(prevExposure):
            prevCostBasis = df.at[df.index[i-1], 'costBasis']
            df.at[df.index[i], 'costBasis'] = ((prevExposure / curExposure) * prevCostBasis) + (1 - (prevExposure / curExposure)) * curTradePrice
        elif curExposure * prevExposure < 0:
            df.at[df.index[i], 'costBasis'] = curTradePrice
        else:
            df.at[df.index[i], 'costBasis'] = df.at[df.index[i-1], 'costBasis'] if i > 0 else np.nan
        df['costBasis'].ffill(inplace=True)

# STATS
for ticker, df in dataObjects.items():
    deltaDays = (df.index[-1] - df.index[0]).days
    years, trDaysYear = (deltaDays / 365.25), 252

    # TRADE RESULTS
    df['longAbsGain'] = np.where((df['exposure'] == 0) & (df['exposure'].shift() > 0), df[tradePrice] - df['costBasis'].shift(), np.nan)
    df['shortAbsGain'] = np.where((df['exposure'] == 0) & (df['exposure'].shift() < 0), -(df[tradePrice] - df['costBasis'].shift()), np.nan)
    df['longPercGain'] = np.where((df['exposure'] == 0) & (df['exposure'].shift() > 0), df['longAbsGain'] / df['costBasis'].shift(), np.nan)
    df['shortPercGain'] = np.where((df['exposure'] == 0) & (df['exposure'].shift() < 0), df['shortAbsGain'] / df['costBasis'].shift(), np.nan)
    df['controlPnl'] = tradeCosts['nominalUSD'] * (df['longPercGain'].fillna(0) + df['shortPercGain'].fillna(0) + 1).cumprod()

    # KEY METRICS
    cagr = ((df['nominalAC'].iloc[-1] / df['nominalAC'].iloc[1]) ** (1 / years)) - 1
    drawdown = np.abs((df['nominalAC'] / df['nominalAC'].expanding(min_periods=1).max() - 1).min())
    bliss = 0 if drawdown == 0 else max(cagr / drawdown, 0)
    cagrBenchmark = ((df[triggerPrice].iloc[-1] / df[triggerPrice].iloc[1]) ** (1 / years)) - 1
    drawdownBenchmark = np.abs((df[triggerPrice] / df[triggerPrice].expanding(min_periods=1).max() - 1).min())
    blissBenchmark = max(cagrBenchmark / drawdownBenchmark, 0)

    # TRADE DISTRIBUTION
    winPeriods = df['percentageReturns'][df['percentageReturns'] > 0]
    lossPeriods = df['percentageReturns'][df['percentageReturns'] < 0]

    # TRADE RESULTS
    avgLongGain = df['longPercGain'][df['longPercGain'] > 0].mean()
    avgShortGain = df['shortPercGain'][df['shortPercGain'] > 0].mean()
    avgLongLoss = df['longPercGain'][df['longPercGain'] < 0].mean()
    avgShortLoss = df['shortPercGain'][df['shortPercGain'] < 0].mean()
    profitableLongTrades = df['longPercGain'][df['longPercGain'] > 0].sum()
    profitableShortTrades = df['shortPercGain'][df['shortPercGain'] > 0].sum()
    unprofitableLongTrades = df['longPercGain'][df['longPercGain'] < 0].sum()
    unprofitableShortTrades = df['shortPercGain'][df['shortPercGain'] < 0].sum()
    avgGain = ((profitableLongTrades * avgLongGain) + (profitableShortTrades * avgShortGain)) / (profitableLongTrades + profitableShortTrades)
    avgLoss = ((unprofitableLongTrades * avgLongLoss) + (unprofitableShortTrades * avgShortLoss)) / (unprofitableLongTrades + unprofitableShortTrades)

    # HIT RATIO
    winningTrades = (df['longAbsGain'] > 0).sum() + (df['shortAbsGain'] > 0).sum()
    totalTrades = df['longAbsGain'].count() + df['shortAbsGain'].count()
    hitRatio = winningTrades / (totalTrades + 1e-10)

    # OTHER 
    expValue = (avgGain * hitRatio) + (avgLoss * (1 - hitRatio))
    tradesPerYear = totalTrades / years
    annTurnover = df['exposure'].diff().loc[lambda x: x > 0].sum() / ((df.index[-1] - df.index[0]).days / 365.25)
    longVSshortTrades = (df['longPercGain'] != 0).sum() / (df['shortPercGain'] != 0).sum()
    marketVola = df['marketReturns'].std() * np.sqrt(trDaysYear)
    systemVola = df['percentageReturns'].std() * np.sqrt(trDaysYear)

    systemMetrics = {'cagr': cagr, 'drawdown': drawdown, 'bliss': bliss, 'cagrBenchmark': cagrBenchmark, 'drawdownBenchmark': drawdownBenchmark, 'blissBenchmark': blissBenchmark, 'winPeriods': winPeriods, 'lossPeriods': lossPeriods, 'avgLongGain': avgLongGain, 'avgShortGain': avgShortGain, 'avgLongLoss': avgLongLoss, 'avgShortLoss': avgShortLoss, 'avgGain': avgGain, 'avgLoss': avgLoss, 'longVSshortTrades': longVSshortTrades, 'winningTrades': winningTrades, 'totalTrades': totalTrades, 'hitRatio': hitRatio, 'expValue': expValue, 'tradesPerYear': tradesPerYear, 'annTurnover': annTurnover, 'marketVola': marketVola, 'systemVola': systemVola}


def plotSignal(df, dfReturn):
    fig, ax = plt.subplots(nrows=4, ncols=1, figsize=(10, 15))
    xmin, xmax = min(df.index.min(), df.index.min()), max(df.index.max(), df.index.max())
    for a in ax:
        a.set_xlim(xmin, xmax)

    # First subplot - Long Entry and Exit Signals
    ax[0].plot(df.index, df['Close'], color='blue', label='Close')
    ax[0].scatter(df[df['longEntry'] == 1].index, df.loc[df[df['longEntry'] == 1].index, 'Close'], color='green', marker='^', label='Long Entry')
    ax[0].scatter(df[df['longExit'] == 1].index, df.loc[df[df['longExit'] == 1].index, 'Close'], color='red', marker='v', label='Long Exit')
    ax[0].legend()
    ax[0].set_title('Long Entry and Exit Signals')

    # Second subplot - Short Entry and Exit Signals
    ax[1].plot(df.index, df['Close'], color='blue', label='Close')
    ax[1].scatter(df[df['shortEntry'] == 1].index, df.loc[df[df['shortEntry'] == 1].index, 'Close'], color='orange', marker='v', label='Short Entry')
    ax[1].scatter(df[df['shortExit'] == 1].index, df.loc[df[df['shortExit'] == 1].index, 'Close'], color='purple', marker='^', label='Short Exit')
    ax[1].legend()
    ax[1].set_title('Short Entry and Exit Signals')

    # Third subplot - Exposure Over Time
    ax[2].plot(df.index, df['exposure'], color='purple', label='Exposure')
    ax[2].legend()
    ax[2].set_title('Exposure Over Time')

    # Fourth subplot - Entry Levels and Exposure
    ax[3].plot(df.index, df['Close'], color='grey', linewidth=1.5, label='Close')
    ax[3].plot(df.index, np.where((dfReturn['costBasis'] != 0) & (df['exposure'] > 0), np.abs(dfReturn['costBasis']), np.nan), color='green', linestyle='--', linewidth=1.0, label='Long Entry Level')
    ax[3].plot(df.index, np.where((dfReturn['costBasis'] != 0) & (df['exposure'] < 0), np.abs(dfReturn['costBasis']), np.nan), color='red', linestyle='--', linewidth=1.0, label='Short Entry Level')
    ax[3].plot(df.index, np.where(df['exposure'] > 0, df['Close'], np.nan), color='green', linewidth=1.0, label='Long Exposure')
    ax[3].plot(df.index, np.where(df['exposure'] < 0, df['Close'], np.nan), color='red', linewidth=1.0, label='Short Exposure')
    ax[3].legend()
    ax[3].set_title('Entry Levels and Exposure')

    # Adding PnL scatter plots and annotations
    stdDev = 0.5 * df['Close'].std()
    longValidIdx = dfStats.index[dfStats['longPercGain'].notna()]
    shortValidIdx = dfStats.index[dfStats['shortPercGain'].notna()]
    scatterLong = ax[3].scatter(longValidIdx, df.loc[longValidIdx, 'Close'] + stdDev, color='green', marker='o', label='Long PnL')
    scatterShort = ax[3].scatter(shortValidIdx, df.loc[shortValidIdx, 'Close'] - stdDev, color='red', marker='x', label='Short PnL')
    for i in longValidIdx:
        txt = dfStats.loc[i, 'longPercGain']
        ax[3].annotate(f"{txt*100:.2f}%", (i, df.loc[i, 'Close'] + stdDev), textcoords="offset points", xytext=(0,10), ha='center', fontsize=10, color='green')
    for i in shortValidIdx:
        txt = dfStats.loc[i, 'shortPercGain']
        ax[3].annotate(f"{txt*100:.2f}%", (i, df.loc[i, 'Close'] - stdDev), textcoords="offset points", xytext=(0,-15), ha='center', fontsize=10, color='red')

    plt.subplots_adjust(left=0.085, bottom=0.055, right=0.9, top=0.95, hspace=0.69)
    plt.tight_layout()
    plt.show()
def plotReturn(dfReturn, ticker):
    fig, ax = plt.subplots(2, 1, figsize=(10, 8))

    # Plotting returns
    ax[0].plot(dfReturn.index, 100 * dfReturn['percentageReturnsAC'], label='System Period Return AC (%)', color='orange', linewidth=1)
    ax[0].plot(dfReturn.index, 100 * dfReturn['percentageReturns'], label='System Period Return (%)', color='navy', linewidth=1)
    ax[0].set_ylabel('System Period Return (%)')
    ax[0].set_title(f'System Period Returns for {ticker}')
    ax[0].legend()

    # Plotting metrics
    labels_colors = [('nominal', 'b'), ('nominalAC', 'g'), ('nominalNakedAC', 'r')]
    for label, color in labels_colors:
        if label in dfReturn:
            ax[1].plot(dfReturn[label], label=label, color=color)
    ax[1].set_title('Metrics')
    ax[1].legend()

    plt.tight_layout()
    plt.show()

# Select a ticker for plotting
chosen_ticker = "SGL.DE"
if chosen_ticker in dataObjects:
    plotSignal(dataObjects[chosen_ticker], chosen_ticker)  # Plot signals
    plotReturn(dataObjects[chosen_ticker], chosen_ticker)  # Plot returns
else:
    print(f"No data found for {chosen_ticker}")
