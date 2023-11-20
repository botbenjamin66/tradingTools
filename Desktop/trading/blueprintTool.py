mode      = 'singleBacktest'                                                    # singleBacktest, loopBacktest, featureTesting, corrTesting, pfAnalysis, times&sales, systemOptimizedAI
source    = 'yfinance'
theme     = 'random'
style     = 'trendTotal'

backtestStart, backtestEnd, dataInterval       = 2014, 2019, '1d'
buySize, sellSize, maxLeverage                 = 1, 1, 1
commissions, spread, slippage, interest        = 0.005, 0.005, 0.005, 0.01

from sklearn.preprocessing import PolynomialFeatures
from sklearn.linear_model import LinearRegression
from pandas.tseries.offsets import DateOffset
from scipy.interpolate import griddata
from sklearn.metrics import r2_score
from scipy.optimize import curve_fit
import matplotlib.dates as mdates
import matplotlib.pyplot as plt
import mplfinance as mpf
import yfinance as yf
import seaborn as sns
import networkx as nx
import pandas as pd
import numpy as np
import random
import time

# INITIALIZE SYSTEM
def initTicker():
    if source == "yfinance":

        if theme == 'tesla':
            ticker = ["TSLA"]
        elif theme == 'dax':
            ticker = ["^GDAXI"]
        elif theme == 'btc':
            ticker = ["BTC=F"]
        elif theme == 'equityIndices':
            ticker = ["MWL=F", "^GDAXI", "QQQ"]
        elif theme == 'popStocks':
             ticker = ["NVDA", "TSLA", "AAPL", "AMZN", "MSFT", "PLTR", "AMD", "FB"]
        elif theme == 'random':
            randomizedTickers = ["MUV2.BE", "BABA", "BTC-USD", "GC=F", "EURUSD=X"]
            ticker = [random.choice(randomizedTickers)]
        else:
            ticker = [theme]
            
        return ticker
def initParameter():
    entryExitRatio, parameter1, parameter2, timeFactor = 3, 60, 20, 1
    if dataInterval in ['1wk', '1mo']:
        timeFactor = 5 if dataInterval == '1wk' else 20
    return int(parameter1/timeFactor), int(parameter2/timeFactor/entryExitRatio), int(parameter1/timeFactor), int(parameter2/timeFactor/entryExitRatio)
def annualizationFactor():
    freqMap = {
        '1m': np.sqrt(252 * 24 * 60), '2m': np.sqrt(252 * 24 * 30), '5m': np.sqrt(252 * 24 * 12), '15m': np.sqrt(252 * 24 * 4),
        '30m': np.sqrt(252 * 24 * 2), '60m': np.sqrt(252 * 24), '90m': np.sqrt(252 * 16), '1h': np.sqrt(252 * 24), '1d': np.sqrt(252),
        '5d': np.sqrt(252 / 5), '1wk': np.sqrt(52), '1mo': np.sqrt(12), '3mo': np.sqrt(4), '6mo': np.sqrt(2), '1y': np.sqrt(1)}
    return freqMap.get(dataInterval, np.sqrt(252))

# BASIC CALCULATIONS
def basicData():
    global ticker
    if source == "yfinance":
        if mode == 'concatFeatureTesting':
            dfBasicPrepDict = []
            for ticker in tickers:
                try:
                    dfBasicPrep = yf.download(ticker, start=str(backtestStart) + "-01-01", end=str(backtestEnd) + "-01-01", interval=dataInterval)
                except Exception as e:
                    dfBasicPrep = yf.download(ticker, end=str(backtestEnd) + "-01-01", interval=dataInterval)
                nanPercentage = dfBasicPrep.isnull().sum().sum() / dfBasicPrep.size * 100 if not dfBasicPrep.empty else 0
                if dfBasicPrep.empty or dfBasicPrep.isnull().all().all():
                    print(f"Failed to download data for {ticker}")
                    continue
                
                # NORMALIZE MULTIPLE DATA FRAMES
                colsToNormalize = ['Open', 'High', 'Low', 'Close', 'Volume']
                cutOff = 4

                dfBasicPrep[colsToNormalize] = dfBasicPrep[colsToNormalize].pct_change().fillna(0)
                dfBasicPrep.replace([np.inf, -np.inf], np.nan, inplace=True)

                for col in colsToNormalize:
                    sortedCol = dfBasicPrep[col].sort_values()
                    outliersLow = sortedCol.iloc[:cutOff].values
                    outliersHigh = sortedCol.iloc[-cutOff:].values
                    colMean = dfBasicPrep[col].mean()
                    dfBasicPrep[col].replace(outliersLow, colMean, inplace=True)
                    dfBasicPrep[col].replace(outliersHigh, colMean, inplace=True)
                    dfBasicPrep[col].fillna(colMean, inplace=True)
                dfBasicPrep['Ticker'] = ticker  
                print(f"NaN percentage for {ticker}: {nanPercentage}%")
                dfBasicPrepDict.append(dfBasicPrep)
            dfBasic = pd.concat(dfBasicPrepDict, axis=0)
            
            # DE-NORMALIZE 
            dfBasic[colsToNormalize] += 1
            dfBasic[colsToNormalize] = dfBasic[colsToNormalize].cumprod()
            dfBasic['midPrice'] = dfBasic[['Open', 'Low', 'High', 'Close']].mean(axis=1)

            if len(tickers) > 1:
                dfBasic.reset_index(drop=True, inplace=True)
                freqMap = {'1m': 'T', '2m': '2T', '5m': '5T', '15m': '15T', '30m': '30T', '60m': 'H', '90m': '90T', '1h': 'H', '1d': 'B', '5d': '5B', '1wk': 'W', '1mo': 'M', '3mo': '3M', '6mo': '6M', '1y': 'A'}
                freq = freqMap.get(dataInterval, 'B')
                newIndex = pd.date_range(start='1900-01-01', periods=len(dfBasic), freq=freq)
                dfBasic.set_index(newIndex, inplace=True)
            print(dfBasic)
            return dfBasic
        else:
            try:
                dfBasic = yf.download(ticker, start=str(backtestStart) + "-01-01", end=str(backtestEnd) + "-01-01", interval=dataInterval)
            except Exception as e:
                dfBasic = yf.download(ticker, end=str(backtestEnd) + "-01-01", interval=dataInterval)
            nanPercentage = dfBasic.isnull().sum().sum() / dfBasic.size * 100
            if dfBasic.empty or dfBasic.isnull().all().all(): print(f"Failed to download data for {ticker}"); return None

            dfBasic['Mid'] = (dfBasic['Open'] + dfBasic['Low'] + dfBasic['High'] + dfBasic['Close']) / 4
            dfBasic['marketReturns'] = dfBasic['Close'].pct_change()

            print(f"NaN percentage: {nanPercentage}%")
            return dfBasic
def targetFeatureData():
    dfTargetFeature = dfBasic.copy()
    dfTargetFeature['return1'] = dfTargetFeature['Close'] / dfTargetFeature['Close'].shift(trail1) - 1
    dfTargetFeature['return2'] = dfTargetFeature['Close'] / dfTargetFeature['Close'].shift(trail2) - 1
    dfTargetFeature['logReturn1'] = np.log(dfTargetFeature['Close'].pct_change(trail1) + 1)
    dfTargetFeature['logReturn2'] = np.log(dfTargetFeature['Close'].pct_change(trail2) + 1)
    dfTargetFeature['marketVola1'] = dfTargetFeature['marketReturns'].rolling(window=trail1).std() * np.sqrt(annFactor)
    dfTargetFeature['marketVola2'] = dfTargetFeature['marketReturns'].rolling(window=trail2).std() * np.sqrt(annFactor)
    dfTargetFeature.drop(columns=dfBasic.columns.tolist(), inplace=True)
    return dfTargetFeature
def floatFeatureData():
    dfFloatFeature = dfBasic.copy()

    dfFloatFeature['volume' + str(trail1)]       = dfFloatFeature['Volume'].rolling(window=trail1).mean()
    dfFloatFeature['volume' + str(trail2)]       = dfFloatFeature['Volume'].rolling(window=trail2).mean()
    dfFloatFeature['ema' + str(trail1)]          = dfFloatFeature[triggerPrice].ewm(span=trail1).mean()
    dfFloatFeature['ema' + str(trail2)]          = dfFloatFeature[triggerPrice].ewm(span=trail2).mean()
    dfFloatFeature['er' + str(trail1)]           = dfFloatFeature[triggerPrice].diff(trail1).abs() / dfFloatFeature[triggerPrice].diff().abs().rolling(window=trail1).sum()
    dfFloatFeature['er' + str(trail2)]           = dfFloatFeature[triggerPrice].diff(trail2).abs() / dfFloatFeature[triggerPrice].diff().abs().rolling(window=trail2).sum()
   
    dfFloatFeature['atr' + str(trail1)]          = pd.concat([dfFloatFeature['High'] - dfFloatFeature['Low'], (dfFloatFeature['High'] - dfFloatFeature[triggerPrice]).abs(), (dfFloatFeature['Low'] - dfFloatFeature[triggerPrice]).abs()], axis=1).max(axis=1).rolling(window=trail1).mean()
    dfFloatFeature['atr' + str(trail2)]          = pd.concat([dfFloatFeature['High'] - dfFloatFeature['Low'], (dfFloatFeature['High'] - dfFloatFeature[triggerPrice]).abs(), (dfFloatFeature['Low'] - dfFloatFeature[triggerPrice]).abs()], axis=1).max(axis=1).rolling(window=trail2).mean()
    
    dfFloatFeature['bbUpper'+str(trail1)]        = dfFloatFeature[triggerPrice].rolling(window=trail1).mean() + factor1*dfFloatFeature[triggerPrice].rolling(window=trail1).std()
    dfFloatFeature['bbLower'+str(trail1)]        = dfFloatFeature[triggerPrice].rolling(window=trail1).mean() - factor1*dfFloatFeature[triggerPrice].rolling(window=trail1).std()
    dfFloatFeature['bbUpper'+str(trail2)]        = dfFloatFeature[triggerPrice].rolling(window=trail2).mean() + factor1*dfFloatFeature[triggerPrice].rolling(window=trail2).std()
    dfFloatFeature['bbLower'+str(trail2)]        = dfFloatFeature[triggerPrice].rolling(window=trail2).mean() - factor1*dfFloatFeature[triggerPrice].rolling(window=trail2).std()
    
    dfFloatFeature['macd' + str(trail1) + '-' + str(trail2)]             = dfFloatFeature['ema' + str(trail1)] / dfFloatFeature['ema' + str(trail2)] - 1
    dfFloatFeature['noise' + str(trail1) + '-' + str(trail2)]            = np.log(dfFloatFeature['er' + str(trail1)] / dfFloatFeature['er' + str(trail2)])
    dfFloatFeature['volumedriven' + str(trail1) + '-' + str(trail2)]     = (dfFloatFeature['volume' + str(trail1)] / dfFloatFeature['volume' + str(trail2)]) / dfFloatFeature['er' + str(trail1)].rolling(window=trail1).mean()
    
    dfFloatFeature.drop(columns=dfBasic.columns.tolist(), inplace=True)
    return dfFloatFeature
def boolFeatureData():
    dfBoolFeature = pd.concat([dfBasic, dfFloatFeature], axis=1)
    signalPause = 0
    
    dfBoolFeature['breakout1'] = np.where((dfBoolFeature[triggerPrice].gt(dfBoolFeature[triggerPrice].shift(1).rolling(window=trail1).max())), 1, np.where((dfBoolFeature[triggerPrice].lt(dfBoolFeature[triggerPrice].shift(1).rolling(window=trail1).min())), -1, np.nan))
    dfBoolFeature['breakout2'] = np.where((dfBoolFeature[triggerPrice].gt(dfBoolFeature[triggerPrice].shift(1).rolling(window=trail2).max())), 1, np.where((dfBoolFeature[triggerPrice].lt(dfBoolFeature[triggerPrice].shift(1).rolling(window=trail2).min())), -1, np.nan))
    dfBoolFeature['bollinger1'] = np.where(dfBoolFeature[triggerPrice] > dfBoolFeature['bbUpper'+str(trail1)], 1, np.where(dfBoolFeature[triggerPrice] < dfBoolFeature['bbLower'+str(trail1)], -1, np.nan))
    dfBoolFeature['bollinger2'] = np.where(dfBoolFeature[triggerPrice] > dfBoolFeature['bbUpper'+str(trail2)], 1, np.where(dfBoolFeature[triggerPrice] < dfBoolFeature['bbLower'+str(trail2)], -1, np.nan))
   
    dfBoolFeature['priceTrend']     = np.where((dfBoolFeature[triggerPrice] > dfFloatFeature['ema' + str(trail1)]) & (dfFloatFeature['ema' + str(trail1)] > dfFloatFeature['ema' + str(trail2)]), 1, np.where((dfBoolFeature[triggerPrice] < dfFloatFeature['ema' + str(trail1)]) & (dfFloatFeature['ema' + str(trail1)] < dfFloatFeature['ema' + str(trail2)]), -1, np.nan))
    dfBoolFeature['atrTrend']       = np.where(dfFloatFeature['atr' + str(trail1)] > dfFloatFeature['atr' + str(trail2)], 1, np.where(dfFloatFeature['atr' + str(trail1)] < dfFloatFeature['atr' + str(trail2)], -1, np.nan))
    dfBoolFeature['erTrend']        = np.where(dfFloatFeature['er' + str(trail1)] > dfFloatFeature['er' + str(trail2)], 1, np.where(dfFloatFeature['er' + str(trail1)] < dfFloatFeature['er' + str(trail2)], -1, np.nan))
    dfBoolFeature['volumeTrend']    = np.where((dfBoolFeature['Volume'] > dfFloatFeature['volume' + str(trail1)]) & (dfFloatFeature['volume' + str(trail1)] > dfFloatFeature['volume' + str(trail2)]), 1, np.where((dfBoolFeature['Volume'] < dfFloatFeature['volume' + str(trail1)]) & (dfFloatFeature['volume' + str(trail1)] < dfFloatFeature['volume' + str(trail2)]), -1, np.nan))

    if signalPause != 0:
        for column in dfBoolFeature.columns:
            is_changed = dfBoolFeature[column].diff().abs() > 0
            for i in np.where(is_changed)[0]:
                dfBoolFeature[column].iloc[i+1:i+1+signalPause] = np.nan

    dfBoolFeature.drop(columns=dfBasic.columns.tolist(), inplace=True)
    dfBoolFeature.drop(columns=dfFloatFeature.columns.tolist(), inplace=True)
    return dfBoolFeature
def signalData(longEntry, longExit, shortEntry, shortExit):

    dfSignal = pd.concat([dfBasic, dfFloatFeature, dfBoolFeature], axis=1)

    # BOOLEAN TRADE SIGNALS
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
    if style == 'reversionTotal':
        dfSignal['longEntry'] = dfBasic[triggerPrice].lt(dfBasic[triggerPrice].shift(1).rolling(window=longEntry).min())
        dfSignal['longExit'] = dfBasic[triggerPrice].gt(dfBasic[triggerPrice].shift(1).rolling(window=longExit).max())
        dfSignal['shortEntry'] = dfBasic[triggerPrice].gt(dfBasic[triggerPrice].shift(1).rolling(window=shortEntry).max())
        dfSignal['shortExit'] = dfBasic[triggerPrice].lt(dfBasic[triggerPrice].shift(1).rolling(window=shortExit).min())

    # LONG & SHORT EXPOSURE
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

    dfSignal.drop(columns=dfBasic.columns.tolist(), inplace=True)
    dfSignal.drop(columns=dfFloatFeature.columns.tolist(), inplace=True)
    dfSignal.drop(columns=dfBoolFeature.columns.tolist(), inplace=True)
    return dfSignal
def returnData():
    dfReturn = pd.concat([dfBasic, dfSignal], axis=1)
    costPerTrade = commissions + spread + slippage

    # PERFORMANCE METRICS
    dfReturn['interestCost'] =  abs(dfSignal['exposure']) * interest * (dfSignal.index.to_series().diff().dt.days / 365)
    dfReturn['marketReturns'] = dfBasic['Close'].pct_change()
    dfReturn['percentageReturns'] = dfSignal['exposure'].shift() * (dfBasic[tradePrice]).pct_change()
    dfReturn['percentageReturnsAC'] = dfReturn['percentageReturns'] - abs(np.where(dfSignal['exposure'].diff() != 0, costPerTrade * dfSignal['exposure'], 0)) - abs(dfSignal['exposure']) * interest * (dfSignal.index.to_series().diff().dt.days / 365)
    dfReturn['nominal'] = (1 + dfReturn['percentageReturns']).cumprod() * nominalUSD
    dfReturn['nominalAC'] = (1 + dfReturn['percentageReturnsAC']).cumprod() * nominalUSD
    dfReturn['nominalNakedAC'] = nominalUSD + (nominalUSD * dfReturn['percentageReturnsAC'].cumsum())

    # COST BASIS
    for idx in dfSignal.index:
        curExposure = dfSignal.at[idx, 'exposure']
        prevIdx = dfSignal.index.get_loc(idx) - 1 if dfSignal.index.get_loc(idx) > 0 else None
        prevExposure = dfSignal.at[dfSignal.index[prevIdx], 'exposure'] if prevIdx is not None else np.nan
        curTradePrice = dfBasic.at[idx, tradePrice]

        if curExposure == 0:
            dfReturn.at[idx, 'costBasis'] = 0
        elif prevExposure == 0 and curExposure != 0:
            dfReturn.at[idx, 'costBasis'] = curTradePrice
        elif prevExposure != 0 and abs(curExposure) > abs(prevExposure):
            dfReturn.at[idx, 'costBasis'] = ((prevExposure / curExposure) * dfReturn.at[dfSignal.index[prevIdx], 'costBasis']) + (1 - (prevExposure / curExposure)) * curTradePrice
        elif curExposure * prevExposure < 0:
            dfReturn.at[idx, 'costBasis'] = curTradePrice
        else:
            dfReturn.at[idx, 'costBasis'] = dfReturn.at[dfSignal.index[prevIdx], 'costBasis'] if prevIdx is not None else np.nan
    dfReturn['costBasis'].ffill(inplace=True)

    dfReturn.drop(columns=dfBasic.columns.tolist(), inplace=True)
    dfReturn.drop(columns=dfSignal.columns.tolist(), inplace=True)
    return dfReturn
def statsData():
    dfStats = pd.concat([dfBasic, dfSignal, dfReturn], axis=1)
    deltaDays = (dfBasic.index[-1] - dfBasic.index[0]).days
    years, trDaysYear = (deltaDays / 365.25), 252

    # TRADE RESULTS
    dfStats['longAbsGain']                     = np.where((dfSignal['exposure'] == 0) & (dfSignal['exposure'].shift() > 0), dfBasic[tradePrice] - dfReturn['costBasis'].shift(), np.nan)
    dfStats['shortAbsGain']                    = np.where((dfSignal['exposure'] == 0) & (dfSignal['exposure'].shift() < 0), -(dfBasic[tradePrice] - dfReturn['costBasis'].shift()), np.nan)
    dfStats['longPercGain']                    = np.where((dfSignal['exposure'] == 0) & (dfSignal['exposure'].shift() > 0), dfStats['longAbsGain'] / dfReturn['costBasis'].shift(), np.nan)
    dfStats['shortPercGain']                   = np.where((dfSignal['exposure'] == 0) & (dfSignal['exposure'].shift() < 0), dfStats['shortAbsGain'] / dfReturn['costBasis'].shift(), np.nan)
 
    dfStats['controlPnl']                      = nominalUSD * (dfStats['longPercGain'].fillna(0) + dfStats['shortPercGain'].fillna(0) + 1).cumprod()
    dfStats['rollingSharpeRatio']              = (dfReturn['percentageReturns'].rolling(window=trail3).mean() / dfReturn['percentageReturns'].rolling(window=trail3).std()) * np.sqrt(annFactor)

    # KEY METRICS
    cagr                                       = ((dfReturn['nominalAC'].iloc[-1] / dfReturn['nominalAC'].iloc[1]) ** (1 / years)) - 1
    drawdown                                   = np.abs((dfReturn['nominalAC'] / dfReturn['nominalAC'].expanding(min_periods=1).max() - 1).min())
    bliss                                      = 0 if drawdown == 0 else max(cagr / drawdown, 0)
    cagrBenchmark                              = ((dfBasic['Close'].iloc[-1] / dfBasic['Close'].iloc[1]) ** (1 / years)) - 1
    drawdownBenchmark                          = np.abs((dfBasic['Close'] / dfBasic['Close'].expanding(min_periods=1).max() - 1).min())
    blissBenchmark                             = max(cagrBenchmark / drawdownBenchmark, 0)

    # TRADE DISTRIBUTION
    winPeriods                                 = dfReturn['percentageReturns'][dfReturn['percentageReturns'] > 0]
    lossPeriods                                = dfReturn['percentageReturns'][dfReturn['percentageReturns'] < 0]

    # TRADE RESULTS
    avgLongGain                                = dfStats['longPercGain'][dfStats['longPercGain'] > 0].mean()
    avgShortGain                               = dfStats['shortPercGain'][dfStats['shortPercGain'] > 0].mean()
    avgLongLoss                                = dfStats['longPercGain'][dfStats['longPercGain'] < 0].mean()
    avgShortLoss                               = dfStats['shortPercGain'][dfStats['shortPercGain'] < 0].mean()
    profitableLongTrades                       = dfStats['longPercGain'][dfStats['longPercGain'] > 0].sum()
    profitableShortTrades                      = dfStats['shortPercGain'][dfStats['shortPercGain'] > 0].sum()
    unprofitableLongTrades                     = dfStats['longPercGain'][dfStats['longPercGain'] < 0].sum()
    unprofitableShortTrades                    = dfStats['shortPercGain'][dfStats['shortPercGain'] < 0].sum()
    avgGain                                    = ((profitableLongTrades * avgLongGain) + (profitableShortTrades * avgShortGain)) / (profitableLongTrades + profitableShortTrades)
    avgLoss                                    = ((unprofitableLongTrades * avgLongLoss) + (unprofitableShortTrades * avgShortLoss)) / (unprofitableLongTrades + unprofitableShortTrades)

    # HIT RATIO
    winningTrades                              = (dfStats['longAbsGain'] > 0).sum() + (dfStats['shortAbsGain'] > 0).sum()
    totalTrades                                = dfStats['longAbsGain'].count() + dfStats['shortAbsGain'].count()
    hitRatio                                   = winningTrades / (totalTrades + 1e-10)

    # OTHER 
    expValue                                   = (avgGain * hitRatio) + (avgLoss * (1 - hitRatio))
    tradesPerYear                              = totalTrades / years
    annTurnover                                = dfSignal['exposure'].diff().loc[lambda x: x > 0].sum() / ((dfBasic.index[-1] - dfBasic.index[0]).days / 365.25)
    longVSshortTrades                          = (dfStats['longPercGain'] != 0).sum() / (dfStats['shortPercGain'] != 0).sum()
    marketVola                                 = dfReturn['marketReturns'].std() * np.sqrt(trDaysYear)
    systemVola                                 = dfReturn['percentageReturns'].std() * np.sqrt(trDaysYear)

    systemMetrics = {'cagr': cagr, 'drawdown': drawdown, 'bliss': bliss, 'cagrBenchmark': cagrBenchmark, 'drawdownBenchmark': drawdownBenchmark, 'blissBenchmark': blissBenchmark, 'winPeriods': winPeriods, 'lossPeriods': lossPeriods, 'avgLongGain': avgLongGain, 'avgShortGain': avgShortGain, 'avgLongLoss': avgLongLoss, 'avgShortLoss': avgShortLoss, 'avgGain': avgGain, 'avgLoss': avgLoss, 'longVSshortTrades': longVSshortTrades, 'winningTrades': winningTrades, 'totalTrades': totalTrades, 'hitRatio': hitRatio, 'expValue': expValue, 'tradesPerYear': tradesPerYear, 'annTurnover': annTurnover, 'marketVola': marketVola, 'systemVola': systemVola}

    dfStats.drop(columns=dfBasic.columns.tolist(), inplace=True)
    dfStats.drop(columns=dfSignal.columns.tolist(), inplace=True)
    dfStats.drop(columns=dfReturn.columns.tolist(), inplace=True)
    return dfStats, systemMetrics

# STORE RESULTS
def storeTicker():
    global dictSingle
    dictSingle[ticker] = {'cagr': systemMetrics['cagr'], 'drawdown': systemMetrics['drawdown'], 'bliss': systemMetrics['bliss'],
        'tradesPerYear': systemMetrics['tradesPerYear'], 'annTurnover': systemMetrics['annTurnover'], 'hitRatio': systemMetrics['hitRatio'],
        'expValue': systemMetrics['expValue'], 'systemVola': systemMetrics['systemVola'], 'avgGain': systemMetrics['avgGain'], 'avgLoss': systemMetrics['avgLoss']}
    return dictSingle
def storeTickerParameterLoop():
    global dictParameterLoop
    if 'combinations' not in dictParameterLoop:
        dictParameterLoop['combinations'] = []
    dictParameterLoop['combinations'].append({
        'longEntry': a,
        'longExit': b,
        'shortEntry': c,
        'shortExit': d,
        'cagr': systemMetrics['cagr'],
        'drawdown': systemMetrics['drawdown'],
        'bliss': systemMetrics['bliss'],
        'hitRatio': systemMetrics['hitRatio'],
        'expValue': systemMetrics['expValue']
    })
    return dictParameterLoop
def storeTickerBest():
    criterion='bliss'
    global dictSingleBest
    if 'dictSingleBest' not in globals() or systemMetrics.get(criterion, 0) > dictSingleBest.get(criterion, -float('inf')):
        dictSingleBest = {
            'ticker': ticker,
            'longEntry': a,
            'longExit': b,
            'shortEntry': c,
            'shortExit': d,
            'cagr': systemMetrics['cagr'],
            'drawdown': systemMetrics['drawdown'],
            'bliss': systemMetrics['bliss'],
            'hitRatio': systemMetrics['hitRatio'],
            'expValue': systemMetrics['expValue'] }

# PLOT SYSTEM BACKTEST
def plotBasic():
    mpf.plot(dfBasic, type='candle', volume=True, style='blueskies')
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
    ax[3].plot(dfSignal.index, np.where((dfReturn['costBasis'] != 0) & (dfSignal['exposure'] > 0), np.abs(dfReturn['costBasis']), np.nan), color='green', linestyle='--', linewidth=1.0, label='Long Entry Level')
    ax[3].plot(dfSignal.index, np.where((dfReturn['costBasis'] != 0) & (dfSignal['exposure'] < 0), np.abs(dfReturn['costBasis']), np.nan), color='red', linestyle='--', linewidth=1.0, label='Short Entry Level')
    ax[3].plot(dfBasic.index, np.where(dfSignal['exposure'] > 0, dfBasic['Close'], np.nan), color='green', linewidth=1.0, label='Long Exposure')
    ax[3].plot(dfBasic.index, np.where(dfSignal['exposure'] < 0, dfBasic['Close'], np.nan), color='red', linewidth=1.0, label='Short Exposure')
    ax[3].legend()
    ax[3].set_title('Entry Levels and Exposure')
    
    stdDev = 0.5 * dfBasic['Close'].std()
    longValidIdx = dfStats.index[dfStats['longPercGain'].notna()]
    shortValidIdx = dfStats.index[dfStats['shortPercGain'].notna()]
    scatterLong = ax[3].scatter(longValidIdx, dfBasic.loc[longValidIdx, 'Close'] + stdDev, color='green', marker='o', label='Long PnL')
    scatterShort = ax[3].scatter(shortValidIdx, dfBasic.loc[shortValidIdx, 'Close'] - stdDev, color='red', marker='x', label='Short PnL')
    for i in longValidIdx:
        txt = dfStats.loc[i, 'longPercGain']
        ax[3].annotate(f"{txt*100:.2f}%", (i, dfBasic.loc[i, 'Close'] + stdDev), textcoords="offset points", xytext=(0,10), ha='center', fontsize=10, color='green')
    for i in shortValidIdx:
        txt = dfStats.loc[i, 'shortPercGain']
        ax[3].annotate(f"{txt*100:.2f}%", (i, dfBasic.loc[i, 'Close'] - stdDev), textcoords="offset points", xytext=(0,-15), ha='center', fontsize=10, color='red')

    plt.subplots_adjust(left=0.085, bottom=0.055, right=0.9, top=0.95, hspace=0.69)
    plt.tight_layout()
    plt.show()
def plotReturn():
    fig, ax = plt.subplots(2, 1, figsize=(10, 8))
    ax[0].plot(dfReturn.index, 100 * dfReturn['percentageReturnsAC'], label='System Period Return AC (%)', color='orange', linewidth = 1)
    ax[0].plot(dfReturn.index, 100 * dfReturn['percentageReturns'], label='System Period Return (%)', color='navy', linewidth = 1)
    ax[0].set_ylabel('System Period Return (%)')
    ax[0].set_title('System Period Returns')
    ax[0].legend()
    for label,color in zip(['nominal','nominalAC','nominalNakedAC','controlPnl'],['b','g','r','m']):
        data = dfReturn[label] if label in dfReturn else dfStats[label]
        ax[1].plot(data, label=label, color=color)
    ax[1].set_title('Metrics')
    ax[1].legend()

    plt.tight_layout()
    plt.show()
def plotTable():
    filteredMetrics = {k: v for k, v in systemMetrics.items() if k not in ['winPeriods', 'lossPeriods']}
    df = pd.DataFrame(list(filteredMetrics.items()), columns=['Metric', 'Value'])
    fig, ax = plt.subplots(figsize=(5, 8))
    ax.axis('tight')
    ax.axis('off')
    table = ax.table(cellText=df.values, colLabels=df.columns, loc='center', cellLoc='center')
    table.auto_set_font_size(False)
    table.set_fontsize(10)
    table.scale(1.5, 1.5)
    plt.subplots_adjust(left=0.2, top=0.8)
    plt.show()

# PLOT LOOP BACKTEST
def plotTickerLoop3D():
    criterion='cagr'
    keys = ('longEntry', 'longExit', criterion) if style in ['trendLong', 'reversionLong'] else ('shortEntry', 'shortExit', criterion)
    entryVals, exitVals, criterionVals = zip(*[(d[keys[0]], d[keys[1]], d[keys[2]] * 100) for d in dictParameterLoop.get('combinations', [])])
    gridX, gridY = np.mgrid[min(entryVals):max(entryVals):100j, min(exitVals):max(exitVals):100j]
    gridZ = griddata((entryVals, exitVals), criterionVals, (gridX, gridY), method='cubic')
    ax = plt.figure().add_subplot(111, projection='3d')
    ax.plot_surface(gridX, gridY, gridZ, cmap='viridis', linewidth=0, antialiased=True)
    ax.contourf(gridX, gridY, gridZ, zdir='z', offset=np.min(gridZ), cmap='viridis', alpha=0.9)
    ax.set_xlabel('Exit'); ax.set_ylabel('Entry'); ax.set_zlabel(f'{criterion} (%)'); ax.set_title(f'for {style}')
    plt.show()

# PLOT FEATURE TESTING
def plotFloatFeature():
    fn = dfFloatFeature.columns[14]
    
    fig, ax1 = plt.subplots()
    fig.patch.set_facecolor('grey')
    ax1.set_facecolor('lightgrey')
    ax1.plot(dfBasic.index, dfBasic['Close'], 'navy')
    ax1.set_ylabel('Close Price', color='navy')
    ax1.set_xlabel('Date')
    ax1.xaxis.set_major_locator(mdates.AutoDateLocator())
    ax1.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m-%d'))
    fig.autofmt_xdate()
    ax2 = ax1.twinx()
    ax2.set_facecolor('none')
    ax2.plot(dfFloatFeature.index, dfFloatFeature[fn], 'orange')
    ax2.set_ylabel(fn, color='orange')
    fig.tight_layout()
    plt.show()
def plotCorrMatrix():
    correlationMatrix = dfFeatureTest.corr()
    reducedCorrelationMatrix = correlationMatrix.loc[dfTargetFeature.columns, dfFloatFeature.columns]
    sns.heatmap(reducedCorrelationMatrix, annot=True, cmap='tab10', fmt='.0%', vmin=-0.75, vmax=0.75,
                annot_kws={"style":"italic","weight":"bold", "size": 7},
                cbar_kws={'label':'Correlation (%)', 'orientation':'vertical'},
                linewidths=.8, linecolor='black')
    plt.xticks(fontsize=8); plt.yticks(fontsize=8)
    plt.subplots_adjust(bottom=0.25)
    plt.show()
def plotCorr2D():
    xAxis, yAxis = dfFeatureTest.columns[15], dfFeatureTest.columns[0]
    
    fig, ax = plt.subplots()
    fig.set_facecolor('grey')
    ax.set_facecolor('white')
    for spine in ax.spines.values(): spine.set_color('gray')
    x, y = dfFeatureTest[xAxis], dfFeatureTest[yAxis]
    ax.scatter(x, y, color='red', s=20, alpha=0.5, label='Data Points')
    X, poly = x.to_numpy()[:, np.newaxis], PolynomialFeatures(2)
    model = LinearRegression().fit(poly.fit_transform(X), y)
    xR = np.linspace(min(x), max(x), 300)
    ax.plot(xR, model.predict(poly.transform(xR[:, np.newaxis])), c='purple', lw=2, label='Polynomial Fit')
    ax.set(xlabel=xAxis, ylabel=yAxis)
    ax.tick_params(axis='both', colors='black')
    plt.legend()
    plt.show()
def plotCorr3D():
    colX, colY, colZ = dfFeatureTest.columns[14], dfFeatureTest.columns[15], dfFeatureTest.columns[0]
    x, y, z = dfFeatureTest[colX], dfFeatureTest[colY], dfFeatureTest[colZ]

    fig = plt.figure()
    ax = fig.add_subplot(111, projection='3d')
    ax.scatter(x, y, z, c='b', marker='o', alpha=0.5)

    ax.set_xlabel(colX)
    ax.set_ylabel(colY)
    ax.set_zlabel(colZ)
    plt.show()
def plotCorrScatter():
    fig, axes = plt.subplots(3, 3, figsize=(15, 15))
    axes = axes.ravel()
    colIndices = [3, 6, 7, 8, 9, 10, 11, 12, 13]
    colNames = dfFeatureTest.columns[colIndices]
    for idx, colName in enumerate(colNames):
        x, y = dfFeatureTest[colName], dfFeatureTest[dfFeatureTest.columns[0]]
        mask = np.isfinite(x) & np.isfinite(y)
        x, y = x[mask], y[mask]
        try:
            coeff, _ = curve_fit(lambda x, a, b: a * x + b, x, y)
            yfit = np.poly1d(coeff)
            r2 = r2_score(y, yfit(x))
            axes[idx].scatter(x, y)
            axes[idx].plot(x, yfit(x), 'r')
            axes[idx].set_title(f"{colName} vs {dfFeatureTest.columns[0]}")
            axes[idx].set_xlabel(colName)
            axes[idx].set_ylabel(dfFeatureTest.columns[0])
            axes[idx].text(0.05, 0.9, f"r² = {r2:.2f}", ha='left', va='top', transform=axes[idx].transAxes, bbox=dict(facecolor='white', alpha=0.9, edgecolor='blue'))
        except Exception as e:
            print(f"An error occurred: {e}")
    plt.subplots_adjust(hspace=0.4)
    plt.show()
def plotCorrBool():
    colX, colY = 2, 21
    cols = dfFeatureTest.columns
    boolCol, targetCol = dfFeatureTest[cols[colX]], dfFeatureTest[cols[colY]]
    
    fig, axes = plt.subplots(1, 3, figsize=(18, 6))
    fig.set_facecolor('grey')
    sns.boxplot(x=boolCol, y=targetCol, ax=axes[0])
    axes[0].set_title('Box Plot')
    axes[0].set(xlabel=cols[colX], ylabel=cols[colY])
    sns.violinplot(x=boolCol, y=targetCol, ax=axes[1])
    axes[1].set_title('Violin Plot')
    axes[1].set(xlabel=cols[colX], ylabel=cols[colY])
    sns.stripplot(x=boolCol, y=targetCol, jitter=0.1, alpha=0.5, ax=axes[2])
    axes[2].set_title('Jitter Plot')
    axes[2].set(xlabel=cols[colX], ylabel=cols[colY])
    plt.show()
def plotBool():
    boolRow = dfBoolFeature.iloc[:, 3]
    fig, ax = plt.subplots(3, 1, figsize=(10, 15))
    
    ax1, ax2 = ax[0], ax[0].twinx()
    ax1.plot(dfBasic['Close'], 'b', label='Closes')
    ax1.set_xlabel('Time')
    ax1.set_ylabel('Closes', color='b')
    ax1.tick_params('y', colors='b')
    
    ax2.plot(boolRow.dropna(), 'g', label=boolRow.name)
    ax2.set_ylabel(boolRow.name, color='g')
    ax2.tick_params('y', colors='g')
    
    ax1.legend(loc='upper left')
    ax2.legend(loc='upper right')
    
    plt.tight_layout()
    plt.show()

if __name__ == "__main__":

    nominalUSD, tickers, annFactor                                            = 1000, initTicker(), annualizationFactor()
    trail1, trail2, trail3, factor1                                           = 22, 77, 200, 2
    triggerPrice, tradePrice                                                  = 'Close',  'Open'
    dictSingle, dictParameterLoop, dictSingleBest, dictTickers                = {}, {}, {}, {}
    longEntry, longExit, shortEntry, shortExit                                = initParameter()

    for ticker in tickers:

        if mode == 'control':
            dfBasic                                          = basicData()
            print(dfBasic)
        if mode == 'singleBacktest':
            dfBasic                                                           = basicData()
            dfTargetFeature                                                   = targetFeatureData()
            dfFloatFeature                                                    = floatFeatureData()
            dfBoolFeature                                                     = boolFeatureData()
            dfSignal                                                          = signalData(longEntry, longExit, shortEntry, shortExit)
            dfReturn                                                          = returnData()
            dfStats, systemMetrics                                            = statsData()

            storeTicker()

            plotBasic()
            plotSignal()
            plotReturn()
            plotTable()
        if mode == 'loopBacktest':
            startTime = time.time()
            dfBasic                                                               = basicData()
            for a in longEntry:
                for b in longExit:
                    for c in shortEntry:
                        for d in shortExit:
                            dfSignal = signalData(a, b, c, d)
                            dfReturn = returnData()
                            dfStats, systemMetrics = statsData()

                            storeTickerParameterLoop()
                            storeTickerBest()

                            #print(dictParameterLoop)
            elapsedTime = time.time() - startTime
            print(f"Time elapsed: {elapsedTime:.2f} seconds")
            
            plotTickerLoop3D()
            
            #print(dictSingleBest)
        if mode in ('featureTesting', 'concatFeatureTesting'):
            dfBasic                                          = basicData()
            dfTargetFeature                                  = targetFeatureData()
            dfFloatFeature                                   = floatFeatureData()
            dfBoolFeature                                    = boolFeatureData()
            dfFeatureTest                                    = pd.concat([dfTargetFeature.shift(-trail1), dfFloatFeature.pct_change(), dfBoolFeature], axis=1).dropna()

            cutOff = 1
            dfFeatureTest[dfFeatureTest.apply(lambda x: x.isin(x.nlargest(cutOff)), axis=0)] = np.nan
            #dfFeatureTest[dfFeatureTest.apply(lambda x: x.isin(x.nsmallest(cutOff)), axis=0)] = np.nan
            dfFeatureTest.replace([np.inf, -np.inf], np.nan, inplace=True)
            dfFeatureTest.ffill(inplace=True)

            #print(dfFeatureTest)
            #print([(col,idx)for idx,col in enumerate(dfTargetFeature.columns)])
            #print([(col,idx)for idx,col in enumerate(dfFloatFeature.columns)])
            #print([(col,idx)for idx,col in enumerate(dfBoolFeature.columns)])
            #print([(col,idx)for idx,col in enumerate(dfFeatureTest.columns)])

            plotFloatFeature()
            plotCorrMatrix()
            plotCorr3D()
            plotCorrScatter()
            plotCorrBool()
            plotBool()
