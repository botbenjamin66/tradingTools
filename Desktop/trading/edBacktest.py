theme = 'dax'

mode = 'systemSingle'
style = 'trendLong'

backtestStart, backtestEnd, dataInterval = 2005, 2009, '1d'
buySize, sellSize, maxLeverage = 0.5, 1, 2
commissions, spread, slippage, interest = 0.01, 0.02, 0.0, 0.0

from scipy.interpolate import griddata
from scipy.stats import linregress
import matplotlib.pyplot as plt
import mplfinance as mpf
import yfinance as yf
import seaborn as sns
import pandas as pd
import numpy as np
import random

def initTicker():
    if theme == 'equity':
        ticker = ["MWL=F", "^GDAXI"]
    elif theme == 'btc':
        ticker = ["BTC=F"]
    elif theme == 'dax':
        ticker = ["^GDAXI"]
    elif theme == 'random':
        randomizedTickers = ["MWL=F", "^GDAXI"]
        ticker = [random.choice(randomizedTickers)]
    else:
        ticker = [theme]
    return ticker
def initParameter():
    if mode == 'systemLoop':
        return list(range(40, 101, 10)), list(range(40, 101, 10)), list(range(60, 71, 10)), list(range(60, 71, 10))
    else:
        return 60, 20, 60, 20

def basicData():
    try:
        dfBasic = yf.download(ticker, start=str(backtestStart) + "-01-01", end=str(backtestEnd) + "-01-01", interval=dataInterval)
    except Exception as e:
        dfBasic = yf.download(ticker, end=str(backtestEnd) + "-01-01", interval=dataInterval)
    nanPercentage = dfBasic.isnull().sum().sum() / dfBasic.size * 100
    
    if dfBasic.empty or dfBasic.isnull().all().all():
        print(f"Failed to download data for {ticker}")
        return None
    
    dfBasic['midPrice'] = (dfBasic['Open'] + dfBasic['Low'] + dfBasic['High'] + dfBasic['Close']) / 4
    print(f"NaN percentage: {nanPercentage}%")
    
    # dfBasic = dfBasic.drop(columns=['Close'])
    # dfBasic = dfBasic.rename(columns={'Adj Close': 'Close'})
    
    return dfBasic
def featureData():
    dfFeature = dfBasic.copy()
    dfFeature['marketReturns'] = dfFeature['Close'].pct_change()
    dfFeature['volume' + str(trail1)] = dfFeature['Volume'].rolling(window=trail1).mean()
    dfFeature['volume' + str(trail2)] = dfFeature['Volume'].rolling(window=trail2).mean()
    dfFeature['ema' + str(trail1)] = dfFeature['Close'].ewm(span=trail1).mean()
    dfFeature['ema' + str(trail2)] = dfFeature['Close'].ewm(span=trail2).mean()
    dfFeature['er' + str(trail1)] = dfFeature['Close'].diff(trail1).abs() / dfFeature['Close'].diff().abs().rolling(window=trail1).sum()
    dfFeature['er' + str(trail2)] = dfFeature['Close'].diff(trail2).abs() / dfFeature['Close'].diff().abs().rolling(window=trail2).sum()
    dfFeature['atr' + str(trail1)] = pd.concat([dfFeature['High'] - dfFeature['Low'], (dfFeature['High'] - dfFeature['Close']).abs(), (dfFeature['Low'] - dfFeature['Close']).abs()], axis=1).max(axis=1).rolling(window=trail1).mean()
    dfFeature['atr' + str(trail2)] = pd.concat([dfFeature['High'] - dfFeature['Low'], (dfFeature['High'] - dfFeature['Close']).abs(), (dfFeature['Low'] - dfFeature['Close']).abs()], axis=1).max(axis=1).rolling(window=trail2).mean()
    dfFeature[f'bo_{trail1}_{trail2}'] = dfFeature['Close'].rolling(window=trail2).apply(lambda x: sum([(val > max(x[max(0, i-trail1):i]) or val < min(x[max(0, i-trail1):i])) for i, val in enumerate(x) if i >= trail1]) if len(x) >= trail1 else np.nan)
    dfFeature['macd' + str(trail1) + '-' + str(trail2)] = dfFeature['ema' + str(trail1)] / dfFeature['ema' + str(trail2)] - 1
    dfFeature['chill' + str(trail1) + '-' + str(trail2)] = dfFeature['atr' + str(trail1)] / dfFeature[f'bo_{trail1}_{trail2}']
    dfFeature['noise' + str(trail1) + '-' + str(trail2)] = dfFeature['er' + str(trail1)] - dfFeature['er' + str(trail2)]
    dfFeature['volumedriven' + str(trail1) + '-' + str(trail2)] = (dfFeature['volume' + str(trail1)] / dfFeature['volume' + str(trail2)]) / dfFeature['er' + str(trail1)].rolling(window=trail1).mean()
    dfFeature['rocm' + str(trail1)] = dfFeature['Close'].pct_change().rolling(window=trail1).mean()
    dfFeature['vama' + str(trail1)] = dfFeature['Close'].rolling(window=trail1).mean() * (dfFeature['atr' + str(trail1)] / dfFeature['atr' + str(trail1)].rolling(window=trail1).mean())
    dfFeature['vp' + str(trail1)] = dfFeature['Volume'] / dfFeature['Close']
    dfFeature['cvm' + str(trail1) + '-' + str(trail2)] = (dfFeature['Close'] * dfFeature['Volume']) - dfFeature['Close'].shift(1) * dfFeature['Volume'].shift(1)
    dfFeature['lpo' + str(trail1)] = (dfFeature['Close'] / dfFeature['Open']).apply(lambda x: 0 if x <= 0 else np.log(x))
    dfFeature['cvs' + str(trail1)] = dfFeature['Close'] - np.sqrt(dfFeature['High'] * dfFeature['Low'])
    dfFeature.drop(columns=dfBasic.columns.tolist(), inplace=True)
    return dfFeature
def signalData(longEntry, longExit, shortEntry, shortExit):
    dfSignal = pd.concat([dfBasic, dfFeature], axis=1)

    if style == 'trendLong':
        dfSignal['longEntry'] = dfBasic[triggerPrice].gt(dfBasic[triggerPrice].shift(1).rolling(window=longEntry).max())
        dfSignal['longExit'] = dfBasic[triggerPrice].lt(dfBasic[triggerPrice].shift(1).rolling(window=longExit).min())
        dfSignal['shortEntry'] = False
        dfSignal['shortExit'] = False
    if style == 'trendShort':
        dfSignal['longEntry'] = False
        dfSignal['longExit'] = False
        dfSignal['shortEntry'] = dfBasic[triggerPrice].lt(dfBasic[triggerPrice].shift(1).rolling(window=shortEntry).min())
        dfSignal['shortExit'] = dfBasic[triggerPrice].gt(dfBasic[triggerPrice].shift(1).rolling(window=shortExit).max())
    if style == 'trendTotal':
        dfSignal['longEntry'] = dfBasic[triggerPrice].gt(dfBasic[triggerPrice].shift(1).rolling(window=longEntry).max())
        dfSignal['longExit'] = dfBasic[triggerPrice].lt(dfBasic[triggerPrice].shift(1).rolling(window=longExit).min())
        dfSignal['shortEntry'] = dfBasic[triggerPrice].lt(dfBasic[triggerPrice].shift(1).rolling(window=shortEntry).min())
        dfSignal['shortExit'] = dfBasic[triggerPrice].gt(dfBasic[triggerPrice].shift(1).rolling(window=shortExit).max())
    if style == 'reversion':
        dfSignal['longEntry'] = dfBasic[triggerPrice].lt(dfBasic[triggerPrice].shift(1).rolling(window=longEntry).min())
        dfSignal['longExit'] = dfBasic[triggerPrice].gt(dfBasic[triggerPrice].shift(1).rolling(window=longExit).max())
        dfSignal['shortEntry'] = dfBasic[triggerPrice].gt(dfBasic[triggerPrice].shift(1).rolling(window=shortEntry).max())
        dfSignal['shortExit'] = dfBasic[triggerPrice].lt(dfBasic[triggerPrice].shift(1).rolling(window=shortExit).min())

    if not (dfSignal['longEntry'].any() or dfSignal['longExit'].any()):
        dfSignal['longExposure'] = 0
    else:
        conditions = [dfSignal['longEntry'], dfSignal['longExit']]
        choices = [buySize, -sellSize]
        dfSignal['deltaExposure'] = np.select(conditions, choices, 0)
        dfSignal['longExposure'] = dfSignal['deltaExposure'].cumsum()
        indexList = dfSignal.index.tolist()
        for i in range(1, len(dfSignal)):
            previousIndex, currentIndex = indexList[i-1], indexList[i]
            newValue = min(maxLeverage, max(0, dfSignal.at[previousIndex, 'longExposure'] + dfSignal.at[currentIndex, 'deltaExposure']))
            dfSignal.at[currentIndex, 'longExposure'] = newValue
    if not (dfSignal['shortEntry'].any() or dfSignal['shortExit'].any()):
        dfSignal['shortExposure'] = 0
    else:
        conditions = [dfSignal['shortEntry'], dfSignal['shortExit']]
        choices = [-buySize, sellSize]
        dfSignal['deltaExposure'] = np.select(conditions, choices, 0)
        dfSignal['shortExposure'] = dfSignal['deltaExposure'].cumsum()
        indexList = dfSignal.index.tolist()
        for i in range(1, len(dfSignal)):
            previousIndex, currentIndex = indexList[i-1], indexList[i]
            newValue = max(-maxLeverage, min(0, dfSignal.at[previousIndex, 'shortExposure'] + dfSignal.at[currentIndex, 'deltaExposure']))
            dfSignal.at[currentIndex, 'shortExposure'] = newValue

    dfSignal['exposure'] = dfSignal['longExposure'] + dfSignal['shortExposure']
    dfSignal['deltaExposure'] = dfSignal['exposure'].diff()

    dfSignal['costBasisLong'] = np.nan
    dfSignal['costBasisShort'] = np.nan

    indexList = dfSignal.index.tolist()
    for i in range(1, len(indexList)):
        prevIdx, currIdx = indexList[i-1], indexList[i]
        deltaExposure = dfSignal.at[currIdx, 'deltaExposure']
        currExposure = dfSignal.at[currIdx, 'exposure']
        tradeP = dfBasic.at[currIdx, tradePrice]

        if currExposure > 0:
            prevExposure = dfSignal.at[prevIdx, 'longExposure']
            prevCostBasis = dfSignal.at[prevIdx, 'costBasisLong']
            newExposure = dfSignal.at[currIdx, 'longExposure']
            if np.isnan(prevCostBasis): prevCostBasis = 0
            dfSignal.at[currIdx, 'costBasisLong'] = ((prevCostBasis * prevExposure) + (tradeP * deltaExposure)) / currExposure if newExposure != prevExposure and deltaExposure > 0 else prevCostBasis
        elif currExposure < 0:
            prevExposure = dfSignal.at[prevIdx, 'shortExposure']
            prevCostBasis = dfSignal.at[prevIdx, 'costBasisShort']
            newExposure = dfSignal.at[currIdx, 'shortExposure']
            if np.isnan(prevCostBasis): prevCostBasis = 0
            dfSignal.at[currIdx, 'costBasisShort'] = ((prevCostBasis * prevExposure) + (tradeP * deltaExposure)) / currExposure if newExposure != prevExposure and deltaExposure < 0 else prevCostBasis

    dfSignal['costBasisLong'].ffill(inplace=True)
    dfSignal['costBasisShort'].ffill(inplace=True)
    dfSignal['costBasis'] = np.where(dfSignal['exposure'] > 0, dfSignal['costBasisLong'], np.where(dfSignal['exposure'] < 0, dfSignal['costBasisShort'], 0))
    dfSignal['costBasis'] = dfSignal['costBasis'].replace({0: np.nan}).ffill()

    conditions = [dfSignal['exposure'] > 0, dfSignal['exposure'] < 0]
    choices = [dfBasic[tradePrice].rolling(window=longExit).min(), dfBasic[tradePrice].rolling(window=shortExit).max()]
    dfSignal['exitLevel'] = np.select(conditions, choices, np.nan)
    
    dfSignal.drop(columns=dfBasic.columns.tolist() + dfFeature.columns.tolist(), inplace=True)
    return dfSignal
def returnData():
    dfReturn = pd.concat([dfBasic, dfSignal], axis=1)
    costPerTrade = commissions + spread + slippage
    
    dfReturn['eqIntervalReturns'] = dfSignal['exposure'].shift() * (dfBasic[tradePrice]).pct_change()
    dfReturn['eqIntervalReturnsAC'] = dfReturn['eqIntervalReturns'] - abs(np.where(dfSignal['exposure'].diff() != 0, costPerTrade * dfSignal['exposure'], 0)) - abs(dfSignal['exposure']) * interest * (dfSignal.index.to_series().diff().dt.days / 365)
    dfReturn['eqCurve'] = (1 + dfReturn['eqIntervalReturns']).cumprod()
    dfReturn['eqCurveAC'] = (1 + dfReturn['eqIntervalReturnsAC']).cumprod()
    dfReturn['interestCost'] =  abs(dfSignal['exposure']) * interest * (dfSignal.index.to_series().diff().dt.days / 365)

    dfReturn['nominalUSD'] = nominalUSD
    dfReturn['eqDollarReturn'] = dfReturn['nominalUSD'] * dfReturn['eqIntervalReturns']
    dfReturn['eqDollarReturnAC'] = dfReturn['eqDollarReturn'] - abs(np.where(dfSignal['exposure'].diff() != 0, costPerTrade * dfReturn['nominalUSD'] * dfSignal['exposure'], 0)) - abs(dfSignal['exposure']) * interest * (dfSignal.index.to_series().diff().dt.days / 365) * dfReturn['nominalUSD']
    dfReturn['nominalCurveAC'] = (1 + dfReturn['eqDollarReturnAC'] / dfReturn['nominalUSD']).cumprod() * dfReturn['nominalUSD']
    
    dfReturn['eqCurveACNoReinvest'] = dfReturn['eqIntervalReturnsAC'].cumsum()

    dfReturn.drop(columns=dfBasic.columns.tolist(), inplace=True)
    dfReturn.drop(columns=dfSignal.columns.tolist(), inplace=True)
    return dfReturn
def statsData():
    dfStats = pd.concat([dfBasic, dfSignal, dfReturn], axis=1)
    deltaDays = (dfBasic.index[-1] - dfBasic.index[0]).days
    years, trDaysYear = (deltaDays / 365.25), 252

    dfStats['heat']                        = (1 - (dfSignal['exitLevel'] / dfBasic[tradePrice])) * dfSignal['exposure']
    dfStats['rollSystemVolatility']        = dfReturn['eqIntervalReturns'].rolling(window=trail3).std() * np.sqrt(trDaysYear)
    dfStats['rollCagrAC']                  = dfReturn['eqCurveAC'].rolling(window=trail3).apply(lambda window: (window.iloc[-1] / window.iloc[0]) ** (1 / (len(window) / trDaysYear)) - 1)
    dfStats['rollDrawdown']                = abs((dfReturn['eqCurve'] / (dfReturn['eqCurve'].rolling(window=trail3).max()) - 1))

    dfStats['longAbsGain']                 = np.where((dfSignal['exposure'] == 0) & (dfSignal['exposure'].shift() > 0), dfBasic[tradePrice] - dfSignal['costBasis'].shift(), 0)
    dfStats['shortAbsGain']                = np.where((dfSignal['exposure'] == 0) & (dfSignal['exposure'].shift() < 0), -(dfBasic[tradePrice] + dfSignal['costBasis'].shift()), 0)
    dfStats['longPercGain']                = np.where((dfSignal['exposure'] == 0) & (dfSignal['exposure'].shift() > 0), dfStats['longAbsGain'] / dfSignal['costBasis'].shift() * 100, 0)
    dfStats['shortPercGain']               = np.where((dfSignal['exposure'] == 0) & (dfSignal['exposure'].shift() < 0), -(abs(dfStats['shortAbsGain']) / dfSignal['costBasis'].shift()) * 100, 0)
    dfStats['accPnlLong']                  = dfStats['longAbsGain'].cumsum()
    dfStats['accPnlShort']                 = dfStats['shortAbsGain'].cumsum()

    dfStats['avgLongGain']                 = dfStats['longAbsGain'][dfStats['longAbsGain'] > 0].mean()
    dfStats['avgLongLoss']                 = dfStats['longAbsGain'][dfStats['longAbsGain'] < 0].mean()
    dfStats['avgShortGain']                = dfStats['shortAbsGain'][dfStats['shortAbsGain'] > 0].mean()
    dfStats['avgShortLoss']                = dfStats['shortAbsGain'][dfStats['shortAbsGain'] < 0].mean()
    dfStats['totalAvgGain']                = dfStats[['longAbsGain', 'shortAbsGain']].apply(lambda x: x[x > 0]).mean().mean()
    dfStats['totalAvgLoss']                = dfStats[['longAbsGain', 'shortAbsGain']].apply(lambda x: x[x < 0]).mean().mean()

    dfStats['hitRatioTotal']               = ((dfStats['longPercGain'] > 0) + (dfStats['shortPercGain'] > 0)).rolling(window=trail3).sum() / ((dfStats['longPercGain'] != 0) + (dfStats['shortPercGain'] != 0)).rolling(window=trail3).sum()

    dfStats['totalAbsExpectancyValue']     = (dfStats['longAbsGain'] + dfStats['shortAbsGain']).rolling(window=trail3).sum() / dfSignal['exposure'].abs().rolling(window=trail3).sum()
    dfStats['totalDollarExpectancyValue']  = (dfStats['longAbsGain'] + dfStats['shortAbsGain']).rolling(window=trail3).sum() * dfReturn['nominalUSD'] / dfSignal['exposure'].abs().rolling(window=trail3).sum()

    dfStats['winPeriods']                  = dfReturn['eqIntervalReturns'][dfReturn['eqIntervalReturns'] > 0]
    dfStats['lossPeriods']                 = dfReturn['eqIntervalReturns'][dfReturn['eqIntervalReturns'] < 0]

    dfStats['totalTrades']                 = dfSignal['exposure'].diff().ne(0).astype(int).cumsum()
    dfStats['rollAnnTurnover']             = dfSignal['exposure'].diff().abs().rolling(window=trail3).sum() / (trail3 / trDaysYear)

    dfStats['winRateDaily']                = dfReturn['eqIntervalReturns'].rolling(window=trail3).apply(lambda x: (x > 0).sum()) / (dfReturn['eqIntervalReturns'].rolling(window=trail3).apply(lambda x: (x > 0).sum()) + dfReturn['eqIntervalReturns'].rolling(window=trail3).apply(lambda x: (x < 0).sum()))
    dfStats['sharpeRatio']                 = (dfReturn['eqIntervalReturns'].rolling(window=trail3).mean() / dfReturn['eqIntervalReturns'].rolling(window=trail3).std()) * np.sqrt(252)

    avgGain          = dfStats[['longAbsGain', 'shortAbsGain']].apply(lambda x: x[x > 0]).mean().mean()
    avgLoss          = dfStats[['longAbsGain', 'shortAbsGain']].apply(lambda x: x[x < 0]).mean().mean()
    hitRatio         = ((dfStats['longAbsGain'] > 0).sum() + (dfStats['shortAbsGain'].ne(0)).sum()) / (dfStats['longAbsGain'].ne(0).sum() + dfStats['shortAbsGain'].ne(0).sum() + (1e-10))
    expValue         = (avgGain * hitRatio) + (avgLoss * (1 - hitRatio))

    cagr             = (dfReturn['eqCurveAC'].iloc[-1]) ** (1 / years) - 1
    maxDrawdown      = np.abs((dfReturn['eqCurveAC'] / dfReturn['eqCurveAC'].expanding(min_periods=1).max() - 1).min())
    bliss            = max(cagr / maxDrawdown, 0)
    tradesPerYear    = dfStats['totalTrades'].iloc[-1] / years
    annTurnover      = dfSignal['exposure'].abs().sum() / ((dfBasic.index[-1] - dfBasic.index[0]).days / 365.25)
    systemVola       = dfReturn['eqIntervalReturns'].std() * np.sqrt(trDaysYear)

    dfStats.drop(columns=dfBasic.columns.tolist(), inplace=True)
    dfStats.drop(columns=dfSignal.columns.tolist(), inplace=True)
    dfStats.drop(columns=dfReturn.columns.tolist(), inplace=True)
    return dfStats, cagr, maxDrawdown, bliss, tradesPerYear, annTurnover, hitRatio, expValue, systemVola

def storeTicker():
    global dictTicker
    dictTicker[ticker] = {'cagr': cagr, 'maxDrawdown': maxDrawdown, 'bliss': bliss, 'tradesPerYear': tradesPerYear,
                          'annTurnover': annTurnover, 'hitRatio': hitRatio, 'expValue': expValue, 'systemVolatility': systemVola}
    return dictTicker
def storeTickerParameterLoop():
    global dictTickerParameterLoop
    if 'combinations' not in dictTickerParameterLoop:
        dictTickerParameterLoop['combinations'] = []
    dictTickerParameterLoop['combinations'].append({'longEntry': a, 'longExit': b, 'shortEntry': c, 'shortExit': d, 'cagr': cagr, 'maxDrawdown': maxDrawdown, 'bliss': bliss})
    return dictTickerParameterLoop
def storeTickerBest(criterion="bliss"):
    global dictTickerBest
    if 'dictTickerBest' not in globals() or globals().get(criterion, 0) > dictTickerBest.get(criterion, -float('inf')):
        dictTickerBest = {'ticker': ticker, 'longEntry': a, 'longExit': b, 'shortEntry': c, 'shortExit': d, 'cagr': cagr, 'maxDrawdown': maxDrawdown, 'bliss': bliss}

def plotBasic():
    mpf.plot(dfBasic, type='candle', volume=True, style='blueskies')
def plotFeature1():
    plt.figure(figsize=(11, 18))
    plt.subplot(5, 1, 1)
    plt.plot(dfBasic['Close'], label='Close Price')
    plt.plot(dfFeature['ema' + str(trail1)], label=f'EMA {trail1}')
    plt.plot(dfFeature['ema' + str(trail2)], label=f'EMA {trail2}')
    plt.title('Price and Moving Averages')
    plt.legend()

    plt.subplot(5, 1, 2)
    plt.plot(dfFeature['marketReturns'], label='Daily Returns')
    plt.title('Daily Returns')
    plt.legend()

    plt.subplot(5, 1, 3)
    plt.plot(dfFeature['volume' + str(trail1)], label=f'Volume {trail1}')
    plt.plot(dfFeature['volume' + str(trail2)], label=f'Volume {trail2}')
    plt.title('Volume')
    plt.legend()

    plt.subplot(5, 1, 4)
    plt.plot(dfFeature['er' + str(trail1)], label=f'ER {trail1}')
    plt.plot(dfFeature['er' + str(trail2)], label=f'ER {trail2}')
    plt.title('Efficiency Ratio')
    plt.legend()

    plt.subplot(5, 1, 5)
    plt.plot(dfFeature['atr' + str(trail1)], label=f'ATR {trail1}')
    plt.plot(dfFeature['atr' + str(trail2)], label=f'ATR {trail2}')
    plt.title('Average True Range')
    plt.legend()

    plt.subplots_adjust(left=0.085, bottom=0.055, right=0.9, top=0.95, hspace=0.69)
    plt.show()
def plotFeature2():
    fig, axes = plt.subplots(nrows=5, ncols=1, figsize=(8, 8))
    axes[0].plot(dfBasic.index, dfBasic['Close'], label='Close', color='blue')
    axes[0].plot(dfFeature.index, dfFeature['ema' + str(trail2)], label=f'EMA{trail2}', color='green', linestyle='--')
    axes[0].legend()
    axes[1].plot(dfFeature.index, dfFeature['chill' + str(trail1) + '-' + str(trail2)], label=f'Chill{trail1}-{trail2}', color='purple')
    axes[1].legend()
    axes[2].plot(dfFeature.index, dfFeature['noise' + str(trail1) + '-' + str(trail2)], label=f'Noise{trail1}-{trail2}', color='orange')
    axes[2].legend()
    axes[3].plot(dfFeature.index, dfFeature['macd' + str(trail1) + '-' + str(trail2)], label=f'MACD{trail1}-{trail2}', color='cyan')
    axes[3].legend()
    axes[4].plot(dfFeature.index, dfFeature['volumedriven' + str(trail1) + '-' + str(trail2)], label=f'Volume Driven{trail1}-{trail2}', color='magenta')
    axes[4].legend()
    plt.tight_layout()
    plt.show()
def plotSignal():
    fig, ax = plt.subplots(nrows=4, ncols=1, figsize=(10, 15))
    xmin, xmax = min(dfBasic.index.min(), dfSignal.index.min()), max(dfBasic.index.max(), dfSignal.index.max())
    for a in ax:
        a.set_xlim(xmin, xmax)

    ax[0].plot(dfBasic.index, dfBasic['Close'], color='blue', label='Close')
    ax[0].scatter(dfSignal[dfSignal['longEntry'] == 1].index, dfBasic.loc[dfSignal[dfSignal['longEntry'] == 1].index, 'Close'], color='green', marker='^', label='Long Entry')
    ax[0].scatter(dfSignal[dfSignal['longExit'] == 1].index, dfBasic.loc[dfSignal[dfSignal['longExit'] == 1].index, 'Close'], color='red', marker='v', label='Long Exit')
    ax[0].legend()
    ax[0].set_title('Long Entry and Exit Signals')

    ax[1].plot(dfBasic.index, dfBasic['Close'], color='blue', label='Close')
    ax[1].scatter(dfSignal[dfSignal['shortEntry'] == 1].index, dfBasic.loc[dfSignal[dfSignal['shortEntry'] == 1].index, 'Close'], color='orange', marker='v', label='Short Entry')
    ax[1].scatter(dfSignal[dfSignal['shortExit'] == 1].index, dfBasic.loc[dfSignal[dfSignal['shortExit'] == 1].index, 'Close'], color='purple', marker='^', label='Short Exit')
    ax[1].legend()
    ax[1].set_title('Short Entry and Exit Signals')

    ax[2].plot(dfSignal.index, dfSignal['exposure'], color='purple', label='Exposure')
    ax[2].legend()
    ax[2].set_title('Exposure Over Time')

    ax[3].plot(dfBasic.index, dfBasic['Close'], color='grey', linewidth=1.5, label='Close')
    ax[3].plot(dfSignal.index, np.where((dfSignal['costBasis'] != 0) & (dfSignal['exposure'] > 0), np.abs(dfSignal['costBasis']), np.nan), color='green', linestyle='--', linewidth=1.0, label='Long Entry Level')
    ax[3].plot(dfSignal.index, np.where((dfSignal['costBasis'] != 0) & (dfSignal['exposure'] < 0), np.abs(dfSignal['costBasis']), np.nan), color='red', linestyle='--', linewidth=1.0, label='Short Entry Level')
    ax[3].plot(dfBasic.index, np.where(dfSignal['exposure'] > 0, dfBasic['Close'], np.nan), color='green', linewidth=1.0, label='Long Exposure')
    ax[3].plot(dfBasic.index, np.where(dfSignal['exposure'] < 0, dfBasic['Close'], np.nan), color='red', linewidth=1.0, label='Short Exposure')
    ax[3].legend()
    ax[3].set_title('Entry Levels and Exposure')

    plt.subplots_adjust(left=0.085, bottom=0.055, right=0.9, top=0.95, hspace=0.69)
    plt.tight_layout()
    plt.show()
def plotReturn():
    fig, (ax1, ax2, ax3) = plt.subplots(3, 1, figsize=(10, 12), sharex=True)
    
    ax1.plot(dfBasic.index, dfBasic['Close'], label='Closes')
    ax1.set_ylabel('Closes')
    ax1.set_title('Closing Prices')
    ax1.legend()
    
    ax2.plot(dfReturn.index, 100 * dfReturn['eqIntervalReturnsAC'], label='System Period Return AC (%)', color='red')
    ax2.plot(dfReturn.index, 100 * dfReturn['eqIntervalReturns'], label='System Period Return (%)', color='blue')
    ax2.set_ylabel('System Period Return (%)')
    ax2.set_title('System Period Returns')
    ax2.legend()
    
    ax3.plot(dfReturn.index, 100 * dfReturn['eqCurve'], label='Equity Curve (%)', color='green')
    ax3.plot(dfReturn.index, 100 * dfReturn['eqCurveAC'], label='Equity Curve After Costs (%)', color='orange')
    ax3.set_xlabel('Date')
    ax3.set_ylabel('Equity (%)')
    ax3.set_title('Equity Curve')
    ax3.legend()
    
    plt.show()
def plotStats1():
    fig, ax = plt.subplots(nrows=4, ncols=1, figsize=(10, 24))

    ax[0].plot(dfStats.index, dfStats['rollAnnTurnover'] * 100, color='blue', label='Annual Turnover (%)')
    ax[0].set_ylabel('Annual Turnover (%)')
    ax[0].legend(loc='upper left')
    ax0_twin = ax[0].twinx()
    ax0_twin.plot(dfStats.index, dfStats['heat'], color='red', label='Heat')
    ax0_twin.set_ylabel('Heat')
    ax0_twin.legend(loc='upper right')

    sns.histplot(dfReturn['eqIntervalReturns'][dfReturn['eqIntervalReturns'] > 0], bins=20, color='green', kde=True, ax=ax[1], label='Winning Periods')
    sns.histplot(dfReturn['eqIntervalReturns'][dfReturn['eqIntervalReturns'] < 0], bins=20, color='red', kde=True, ax=ax[1], label='Losing Periods')
    ax[1].set_xlabel('Return')
    ax[1].set_ylabel('Frequency')
    ax[1].legend()

    ax[2].plot(dfStats.index, dfStats['winRateDaily'] * 100, color='purple', label='Rolling Win Rate (%)')
    ax[2].set_xlabel('Date')
    ax[2].set_ylabel('Win Rate (%)')
    ax[2].legend()
    ax2_twin = ax[2].twinx()
    ax2_twin.plot(dfStats.index, dfStats['rollDrawdown'] * 100, color='orange', label='Roll Max Drawdown (%)')
    ax2_twin.set_ylabel('Max Drawdown (%)')
    ax2_twin.legend(loc='lower left')

    ax[3].plot(dfStats.index, dfStats['sharpeRatio'], color='teal', label='Sharpe Ratio', lw=2)
    ax[3].set_xlabel('Date')
    ax[3].set_ylabel('Ratio')
    ax[3].legend()
    ax[3].set_title('Sharpe Ratio')

    sns.set_style("whitegrid")
    sns.despine()
    plt.tight_layout(h_pad=0.79)
    plt.show()
def plotStats2():
    fig, axes = plt.subplots(nrows=4, ncols=1, figsize=(12, 18))

    axes[0].plot(dfStats['rollCagrAC'] * 100, color='blue', label='Rolling CAGR (%)')
    axes[0].set_title('Rolling CAGR Over Time')
    axes[0].set_ylabel('Rolling CAGR (%)')
    axes[0].legend()
    
    axes[1].plot(dfStats['longAbsGain'][dfStats['longAbsGain'] != 0], color='green', label='Long Absolute Gains', marker="x")
    axes[1].plot(dfStats['shortAbsGain'][dfStats['shortAbsGain'] != 0], color='red', label='Short Absolute Gains', marker="o")
    axes[1].set_title('Long and Short Absolute Gains Over Time')
    axes[1].set_ylabel('Absolute Gains')
    axes[1].legend()

    axes[2].plot(dfStats['longPercGain'][dfStats['longPercGain'] != 0], color='green', label='Long Percentage Gains (%)', marker="x")
    axes[2].plot(dfStats['shortPercGain'][dfStats['shortPercGain'] != 0], color='red', label='Short Percentage Gains (%)', marker="o")
    axes[2].set_title('Long and Short Percentage Gains Over Time')
    axes[2].set_ylabel('Percentage Gains (%)')
    axes[2].legend()

    rows = ['CAGR', 'Max Drawdown', 'Bliss']
    data = [[f"{cagr * 100:.1f}%"], [f"{maxDrawdown * 100:.1f}%"], [f"{bliss:.2f}"]]
    table = axes[3].table(cellText=data, rowLabels=rows, cellLoc='center', loc='center')
    table.auto_set_font_size(False)
    table.set_fontsize(10)
    table.scale(1, 1.5)
    axes[3].axis('off')

    plt.tight_layout()
    plt.show()
def plotStats3():
    fig, axes = plt.subplots(3, 3, figsize=(15, 15))
    
    dfStats['heat'].plot(ax=axes[0, 0], title='Heat', color='red')
    dfStats['rollSystemVolatility'].plot(ax=axes[0, 1], title='Rolling System Volatility', color='blue')
    dfStats['rollCagrAC'].plot(ax=axes[0, 2], title='Rolling CAGR AC', color='green')
    dfStats['rollDrawdown'].plot(ax=axes[1, 0], title='Rolling Drawdown', color='purple')
    dfStats['totalAbsExpectancyValue'].plot(ax=axes[1, 1], title='Total Absolute Expectancy Value', color='orange')
    dfStats['totalDollarExpectancyValue'].plot(ax=axes[1, 2], title='Total Dollar Expectancy Value', color='brown')
    dfStats['winRateDaily'].plot(ax=axes[2, 0], title='Win Rate Daily', color='pink')
    dfStats['sharpeRatio'].plot(ax=axes[2, 1], title='Sharpe Ratio', color='grey')

    axes[2, 2].text(0.1, 0.8, f'CAGR: {cagr:.2%}')
    axes[2, 2].text(0.1, 0.6, f'Max Drawdown: {maxDrawdown:.2%}')
    axes[2, 2].text(0.1, 0.4, f'Bliss: {bliss:.2f}')
    axes[2, 2].axis('off')

    plt.tight_layout()
    plt.show()
def plotTickerLoop3D(criterion='maxDrawdown'):
    keys = ('longEntry', 'longExit', criterion) if style in ['trendLong', 'reversionLong'] else ('shortEntry', 'shortExit', criterion)
    entryVals, exitVals, criterionVals = zip(*[(d[keys[0]], d[keys[1]], d[keys[2]] * 100) for d in dictTickerParameterLoop.get('combinations', [])])
    gridX, gridY = np.mgrid[min(entryVals):max(entryVals):100j, min(exitVals):max(exitVals):100j]
    gridZ = griddata((entryVals, exitVals), criterionVals, (gridX, gridY), method='linear')
    
    ax = plt.figure().add_subplot(111, projection='3d')
    ax.plot_surface(gridX, gridY, gridZ, cmap='viridis', linewidth=0, antialiased=True)
    ax.contourf(gridX, gridY, gridZ, zdir='z', offset=np.min(gridZ), cmap='viridis', alpha=0.5)
    
    ax.set_xlabel('Exit'); ax.set_ylabel('Entry'); ax.set_zlabel(f'{criterion} (%)'); ax.set_title(f'for {style}')
    plt.show()
def plotCorrMatrix():
        correlationMatrix = dfTesting.corr()
        reducedCorrelationMatrix = correlationMatrix.iloc[:2]
        reducedCorrelationMatrix = reducedCorrelationMatrix.iloc[:, 2:]
        plt.figure(figsize=(15, 10))
        sns.heatmap(reducedCorrelationMatrix, annot=True, cmap='magma', fmt='.0%', vmin=-1, vmax=1,
                    annot_kws={"style": "italic", "weight": "bold"}, cbar_kws={'label': 'Correlation (%)'})
        plt.show()
def plotScatterPlots():
    selectedColumns = ['marketReturns', 'volume22', 'volume77', 'ema22', 'ema77', 'er22', 'er77', 'atr22', 'atr77']
    fig, axes = plt.subplots(3, 3, figsize=(18, 18), facecolor='lightgrey')
    axes = axes.flatten()

    for i, column in enumerate(selectedColumns):
        sns.regplot(x=column, y='Close', data=dfTesting, ax=axes[i], line_kws={"color": "red"})
        axes[i].set_facecolor('lightgray')
        axes[i].grid(True, linestyle='--')
        
        # Calculate R-squared
        slope, intercept, r_value, p_value, std_err = linregress(dfTesting[column], dfTesting['Close'])
        r_squared = r_value**2
        axes[i].annotate(f"R² = {r_squared:.2f}", xy=(0.7, 0.1), xycoords='axes fraction', fontsize=12, color='blue')

        axes[i].set_title(f'Close vs {column}', fontsize=14, fontweight='bold')
        
    plt.tight_layout()
    plt.show()

if __name__ == "__main__":

    nominalUSD, targetRiskPerTrade, tickers = 1000, 0.02, initTicker()
    trail1, trail2, trail3 = 22, 77, 200
    triggerPrice, tradePrice = 'Close',  'Open'
    dictTicker, dictTickerParameterLoop, dictTickerBest = {}, {}, {}
    longEntry, longExit, shortEntry, shortExit = initParameter()

    for ticker in tickers:

        dfBasic = basicData()
        dfFeature = featureData()

        if mode == 'systemSingle':
            dfSignal = signalData(longEntry, longExit, shortEntry, shortExit)
            dfReturn = returnData()
            dfStats, cagr, maxDrawdown, bliss, tradesPerYear, annTurnover, hitRatio, expValue, systemVola = statsData()

            storeTicker()

            plotBasic()
            plotFeature1()
            plotFeature2()
            plotSignal()
            plotReturn()
            plotStats1()
            plotStats2()
            plotStats3()
        if mode == 'systemLoop':
            for a in longEntry:
                for b in longExit:
                    for c in shortEntry:
                        for d in shortExit:
                            dfSignal = signalData(a, b, c, d)
                            dfReturn = returnData()
                            dfStats, cagr, maxDrawdown, bliss, tradesPerYear, annTurnover, hitRatio, expValue, systemVola = statsData()

                            storeTickerParameterLoop()
                            storeTickerBest()

                            #print(dictTickerParameterLoop)
            plotTickerLoop3D()
            #print(dictTickerBest)
        if mode == 'featureTesting':
            #plt.plot(dfBasic[['Close', 'Adj Close']])
            #plt.legend(['Close', 'Adj Close'])
            #plt.show()

            colsToDiff = list(dfBasic) + [col for col in dfFeature if col != 'marketReturns']
            dfTesting = pd.concat([dfBasic, dfFeature], axis=1)
            dfTesting[colsToDiff] = dfTesting[colsToDiff].diff().dropna()
            dfTesting = dfTesting.drop(columns=['Open', 'High', 'Low', 'Adj Close', 'Volume', 'midPrice'])
            plotScatterPlots()
            plotCorrMatrix()

############################################################################################################################################

# cost basis & exitLevel
# days , weeks , month adjustments
# start using classes
# position sizing options (targetRisk, intervallHeatAdjustment, targetVola)
# short term reversion & long term trend    
# flexible loop (open or close, trend or reversion,...)  

############################################################################################################################################
#signal processing

#time                     open             low            high             close           mid 

#instant

#same interval

#next interval