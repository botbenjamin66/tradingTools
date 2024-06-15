# ENVIROMENT
mode                                          = 'classicBacktest'

# BACKTESTING ENVIRONMENT
acid                                          = 'ed'
trail1, trail2, factor1                       = 190, 20, 2
nominalFX, buySize, sellSize, maxLeverage     = 100, 1, 1, 1
backtestStart, backtestEnd, dataInterval      = 2008, 2019, '1d'
commissions, spread, skid, slippage, interest = 0.00, 0.00, 0.00, 0.00, 0.00

# IMPORTS
from scipy.interpolate import griddata
from sklearn.metrics import r2_score
from scipy.optimize import curve_fit
import matplotlib.ticker as mticker
import matplotlib.pyplot as plt
import mplfinance as mpf
import yfinance as yf
import seaborn as sns
import pandas as pd
import numpy as np
import time

# INIT
def initTicker():
    if acid == 'btc':
        ticker = ['BTC-USD']
    elif acid == 'gold':
        ticker = ['GC=F']
    elif acid == 'palantir':
        ticker = ['PLTR']
    elif acid == 'm1':
        ticker = ['M12.DE']
    elif acid == 'eth':
        ticker = ['ETH-USD']
    else:
        ticker = [acid]
    return ticker
def initParameter():
    if mode == 'paraloopBacktest':
        longEntry, longExit, shortEntry, shortExit = range(20, 220, 40), range(5, 105, 20), range(20, 100, 40), range(5, 45, 20)
        return longEntry, longExit, shortEntry, shortExit
    else:
        longEntry, longExit, shortEntry, shortExit = trail1, trail2, trail1, trail2
        return longEntry, longExit, shortEntry, shortExit

# TOOLS
def annualizationFactor():
    freqMap = {
        '1m': np.sqrt(252 * 24 * 60), '2m': np.sqrt(252 * 24 * 30), '5m': np.sqrt(252 * 24 * 12), '15m': np.sqrt(252 * 24 * 4),
        '30m': np.sqrt(252 * 24 * 2), '60m': np.sqrt(252 * 24), '90m': np.sqrt(252 * 16), '1h': np.sqrt(252 * 24), '1d': np.sqrt(252),
        '5d': np.sqrt(252 / 5), '1wk': np.sqrt(52), '1mo': np.sqrt(12), '3mo': np.sqrt(4), '6mo': np.sqrt(2), '1y': np.sqrt(1)}
    return freqMap.get(dataInterval, np.sqrt(252))
def concatYfinance():
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

# DATA
def basicData():
    global ticker
    if acid == "ed":
        dfBasic = pd.read_csv('/Users/benjaminsuermann/Desktop/trading/edGoldData.csv', sep = ';')
        dfBasic['Date'] = pd.to_datetime(dfBasic['Date'], format='%d.%m.%y')
        dfBasic = dfBasic.set_index('Date')
        #dfBasic = dfBasic.iloc[:500]
        dfBasic['marketReturns'] = dfBasic[triggerPrice].pct_change()
        return dfBasic
    else:
        try:
            dfBasic = yf.download(ticker, start=str(backtestStart) + "-05-01", end=str(backtestEnd) + "-05-01", interval=dataInterval)
        except Exception as e:
            dfBasic = yf.download(ticker, end=str(backtestEnd) + "-01-01", interval=dataInterval)
        nanPercentage = dfBasic.isnull().sum().sum() / dfBasic.size * 100
        if dfBasic.empty or dfBasic.isnull().all().all(): print(f"Failed to download data for {ticker}"); return None

        # KICK OUT WEEKENDS
        dfBasic = dfBasic[dfBasic.index.weekday < 5].copy(deep=True)
        dfBasic['marketReturns'] = dfBasic[triggerPrice].pct_change()

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
   
    dfFloatFeature['upperBb'] = dfFloatFeature['Close'].rolling(window=trail1).mean() + (dfFloatFeature['Close'].rolling(window=trail1).std() * factor1)
    dfFloatFeature['lowerBb'] = dfFloatFeature['Close'].rolling(window=trail1).mean() - (dfFloatFeature['Close'].rolling(window=trail1).std() * factor1)

    dfFloatFeature['tr'] = pd.concat([dfFloatFeature['High'] - dfFloatFeature['Low'], (dfFloatFeature['High'] - dfFloatFeature[triggerPrice]).abs(), (dfFloatFeature['Low'] - dfFloatFeature[triggerPrice]).abs()], axis=1).max(axis=1)
    dfFloatFeature['atr' + str(trail1)] = dfFloatFeature['tr'].rolling(window=trail1).mean()
    dfFloatFeature['atr' + str(trail2)] = dfFloatFeature['tr'].rolling(window=trail2).mean()

    dfFloatFeature['macd' + str(trail1) + '-' + str(trail2)]             = dfFloatFeature['ema' + str(trail1)] / dfFloatFeature['ema' + str(trail2)] - 1
    dfFloatFeature['noise' + str(trail1) + '-' + str(trail2)] = np.log((dfFloatFeature['er' + str(trail1)] + 1e-6) / (dfFloatFeature['er' + str(trail2)] + 1e-6))
    dfFloatFeature['volumedriven' + str(trail1) + '-' + str(trail2)]     = (dfFloatFeature['volume' + str(trail1)] / dfFloatFeature['volume' + str(trail2)]) / dfFloatFeature['er' + str(trail1)].rolling(window=trail1).mean()
    
    dfFloatFeature.drop(columns=dfBasic.columns.tolist(), inplace=True)
    return dfFloatFeature
def boolFeatureData():
    signalPause                     = 0
    dfBoolFeature                   = pd.concat([dfBasic, dfFloatFeature], axis=1)
    
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
def tradingData(longEntry, longExit, shortEntry, shortExit):
    dfTrading = pd.concat([dfBasic, dfFloatFeature, dfBoolFeature], axis=1)

    # SIGNALS
    dfTrading['longEntry']  = dfBasic[triggerPrice].gt(dfBasic[triggerPrice].shift(1).rolling(window=longEntry).max())
    dfTrading['longExit']   = dfBasic[triggerPrice].lt(dfBasic[triggerPrice].shift(1).rolling(window=longExit).min())
    dfTrading['shortEntry'] = dfBasic[triggerPrice].lt(dfBasic[triggerPrice].shift(1).rolling(window=shortEntry).min())
    dfTrading['shortExit']  = dfBasic[triggerPrice].gt(dfBasic[triggerPrice].shift(1).rolling(window=shortExit).max())

    # EXPOSURE
    if not (dfTrading['longEntry'].any() or dfTrading['longExit'].any()):
        dfTrading['longExposure'] = 0
    else:
        dfTrading['deltaExposure'] = np.where(dfTrading['longEntry'], buySize, np.where(dfTrading['longExit'], -sellSize, 0))
        dfTrading['longExposure'] = dfTrading['deltaExposure'].cumsum()
        indexList = dfTrading.index.tolist()
        for i in range(1, len(dfTrading)):
            previousIndex, currentIndex = indexList[i-1], indexList[i]
            newValue = min(maxLeverage, max(0, dfTrading.at[previousIndex, 'longExposure'] + dfTrading.at[currentIndex, 'deltaExposure']))
            dfTrading.at[currentIndex, 'longExposure'] = newValue
    if not (dfTrading['shortEntry'].any() or dfTrading['shortExit'].any()):
        dfTrading['shortExposure'] = 0
    else:
        conditions = [dfTrading['shortEntry'], dfTrading['shortExit']]
        choices = [-buySize, sellSize]
        dfTrading['deltaExposure'] = np.select(conditions, choices, 0)
        dfTrading['shortExposure'] = dfTrading['deltaExposure'].cumsum()
        indexList = dfTrading.index.tolist()
        for i in range(1, len(dfTrading)):
            previousIndex, currentIndex = indexList[i-1], indexList[i]
            newValue = max(-maxLeverage, min(0, dfTrading.at[previousIndex, 'shortExposure'] + dfTrading.at[currentIndex, 'deltaExposure']))
            dfTrading.at[currentIndex, 'shortExposure'] = newValue

    dfTrading['exposure'] = dfTrading['longExposure'] + dfTrading['shortExposure']
    dfTrading['deltaExposure'] = dfTrading['exposure'].diff()

    dfTrading.drop(columns=dfBasic.columns.tolist(), inplace=True)
    dfTrading.drop(columns=dfFloatFeature.columns.tolist(), inplace=True)
    dfTrading.drop(columns=dfBoolFeature.columns.tolist(), inplace=True)
    return dfTrading
def returnData():
    dfReturn = pd.concat([dfBasic, dfTrading], axis=1)
    fees = commissions + spread + slippage
    deltaDays = (dfBasic.index[-1] - dfBasic.index[0]).days
    years, trDaysYear = (deltaDays / 365.25), 252

    # COSTS
    dfReturn['pfReturnsBrutto'] = dfTrading['exposure'].shift() * dfBasic[triggerPrice].pct_change()
    dfReturn['interestCost'] = abs(dfTrading['exposure']) * interest * (dfTrading.index.to_series().diff().dt.days / 365)
    dfReturn['transactionCost'] = abs(dfTrading['deltaExposure']) * fees
    dfReturn['riskfreeCost'] = interest * (dfTrading.index.to_series().diff().dt.days / 365)

    # SKID
    dfReturn['tradePriceBuy'] = dfBasic[['Open', 'Low']].max(axis=1) + skid * (dfBasic['High'] - dfBasic[['Open', 'Low']].max(axis=1))
    dfReturn['tradePriceSell'] = dfBasic[['Open', 'High']].min(axis=1) - skid * (dfBasic[['Open', 'High']].min(axis=1) - dfBasic['Low'])
    dfReturn['skidTradePrice'] = np.where(dfTrading['deltaExposure'] > 0, dfReturn['tradePriceBuy'], np.where(dfTrading['deltaExposure'] < 0, dfReturn['tradePriceSell'], np.nan))

    # COST BASIS
    dfReturn['costBasis'] = np.where(dfTrading['exposure'] == 0, 0, np.nan)
    dfReturn['costBasis'] = np.where((dfTrading['exposure'] != 0) & (dfTrading['exposure'].shift() == 0), dfReturn['skidTradePrice'], dfReturn['costBasis'])
    dfReturn['costBasis'] = np.where((dfTrading['exposure'] != 0) & (np.abs(dfTrading['exposure']) > np.abs(dfTrading['exposure'].shift())), ((dfTrading['exposure'].shift() / dfTrading['exposure']) * dfReturn['costBasis'].shift()) + (1 - (dfTrading['exposure'].shift() / dfTrading['exposure'])) * dfReturn['skidTradePrice'], dfReturn['costBasis'])
    dfReturn['costBasis'] = np.where((dfTrading['exposure'] != 0) & (dfTrading['exposure'].shift() * dfTrading['exposure'] < 0), dfReturn['skidTradePrice'], dfReturn['costBasis'])
    dfReturn['costBasis'].ffill(inplace=True)

    # RETURNS LONG VS. SHORT
    dfReturn['longReturnsAbs'], dfReturn['shortReturnsAbs'] = np.nan, np.nan
    dfReturn['longReturnsAbs'] = np.where((dfTrading['exposure'].shift() > 0) & (dfTrading['exposure'] <= 0), dfBasic[triggerPrice] - dfReturn['costBasis'].shift(), np.nan)
    dfReturn['shortReturnsAbs'] = np.where((dfTrading['exposure'].shift() < 0) & (dfTrading['exposure'] >= 0), (dfBasic[triggerPrice] - dfReturn['costBasis'].shift()) * (-1), np.nan)
    dfReturn['longReturnsPerc'] = np.where(~np.isnan(dfReturn['longReturnsAbs']), dfReturn['longReturnsAbs'] / dfReturn['costBasis'].shift(), np.nan)
    dfReturn['shortReturnsPerc'] = np.where(~np.isnan(dfReturn['shortReturnsAbs']), dfReturn['shortReturnsAbs'] / dfReturn['costBasis'].shift(), np.nan)

    # PERFORMANCE
    dfReturn['pfReturnsNetto'] = dfReturn['pfReturnsBrutto'] - dfReturn['interestCost'] - dfReturn['transactionCost'] - dfReturn['riskfreeCost']
    dfReturn['longTradeResults'] = np.where(~np.isnan(dfReturn['longReturnsAbs']), dfReturn['longReturnsAbs'] / dfReturn['costBasis'].shift(), np.nan)
    dfReturn['shortTradeResults'] = np.where(~np.isnan(dfReturn['shortReturnsAbs']), dfReturn['shortReturnsAbs'] / dfReturn['costBasis'].shift(), np.nan)

    dfReturn['longshortTradeResults'] = nominalFX * ((dfReturn['longTradeResults'].fillna(0) + dfReturn['shortTradeResults'].fillna(0)).cumsum() + 1)
    dfReturn['nominalFXCompounded'] = nominalFX * (1 + dfReturn['pfReturnsNetto']).cumprod()
    dfReturn['nominalFX'] = np.maximum(0.001, nominalFX + (nominalFX * dfReturn['pfReturnsNetto'].cumsum()))

    dfReturn.drop(columns=dfBasic.columns.tolist(), inplace=True)
    dfReturn.drop(columns=dfTrading.columns.tolist(), inplace=True)
    return dfReturn
def statsData():
    dfStats                 = pd.concat([dfBasic, dfTrading, dfReturn], axis=1)
    deltaDays               = (dfBasic.index[-1] - dfBasic.index[0]).days
    years, trDaysYear       = (deltaDays / 365.25), 252

    # KEY METRICS
    cagr                    = ((dfReturn['nominalFX'].iloc[-1] / dfReturn['nominalFX'].iloc[1]) ** (1 / years)) - 1
    drawdown                = np.abs((dfReturn['nominalFX'] / dfReturn['nominalFX'].expanding(min_periods=1).max() - 1).min())
    bliss                   = max(cagr / drawdown, 0)
    cagrAcid                = ((dfBasic['Close'].iloc[-1] / dfBasic['Close'].iloc[0]) ** (1 / years)) - 1
    drawdownAcid            = np.abs((dfBasic['Close'] / dfBasic['Close'].expanding(min_periods=1).max() - 1).min())
    blissAcid               = max(cagrAcid / drawdownAcid, 0)
    kiss                    = bliss - blissAcid

    # TRADE RESULTS
    avgLongGain             = dfReturn['longReturnsPerc'][dfReturn['longReturnsPerc'] > 0].mean() if not np.isnan(dfReturn['longReturnsPerc'][dfReturn['longReturnsPerc'] > 0].mean()) else 0
    avgShortGain            = dfReturn['shortReturnsPerc'][dfReturn['shortReturnsPerc'] > 0].mean() if not np.isnan(dfReturn['shortReturnsPerc'][dfReturn['shortReturnsPerc'] > 0].mean()) else 0
    avgLongLoss             = dfReturn['longReturnsPerc'][dfReturn['longReturnsPerc'] < 0].mean() if not np.isnan(dfReturn['longReturnsPerc'][dfReturn['longReturnsPerc'] < 0].mean()) else 0
    avgShortLoss            = dfReturn['shortReturnsPerc'][dfReturn['shortReturnsPerc'] < 0].mean() if not np.isnan(dfReturn['shortReturnsPerc'][dfReturn['shortReturnsPerc'] < 0].mean()) else 0
    profitableLongTrades    = dfReturn['longReturnsPerc'][dfReturn['longReturnsPerc'] > 0].sum()
    profitableShortTrades   = dfReturn['shortReturnsPerc'][dfReturn['shortReturnsPerc'] > 0].sum()
    unprofitableLongTrades  = dfReturn['longReturnsPerc'][dfReturn['longReturnsPerc'] < 0].sum()
    unprofitableShortTrades = dfReturn['shortReturnsPerc'][dfReturn['shortReturnsPerc'] < 0].sum()

    totalProfitableTrades   = (profitableLongTrades if not np.isnan(profitableLongTrades) else 0) + (profitableShortTrades if not np.isnan(profitableShortTrades) else 0)
    avgPercGain             = ((profitableLongTrades if not np.isnan(profitableLongTrades) else 0) * avgLongGain + (profitableShortTrades if not np.isnan(profitableShortTrades) else 0) * avgShortGain) / totalProfitableTrades if totalProfitableTrades > 0 else 0
    totalUnprofitableTrades = (unprofitableLongTrades if not np.isnan(unprofitableLongTrades) else 0) + (unprofitableShortTrades if not np.isnan(unprofitableShortTrades) else 0)
    avgPercLoss             = ((unprofitableLongTrades if not np.isnan(unprofitableLongTrades) else 0) * avgLongLoss + (unprofitableShortTrades if not np.isnan(unprofitableShortTrades) else 0) * avgShortLoss) / totalUnprofitableTrades if totalUnprofitableTrades > 0 else 0

    # HIT RATIO
    winningTrades           = (dfStats['longReturnsAbs'] > 0).sum() + (dfStats['shortReturnsAbs'] > 0).sum()
    totalTrades             = dfStats['longReturnsAbs'].count() + dfStats['shortReturnsAbs'].count()
    hitRatio                = winningTrades / (totalTrades + 1e-10)

    # OTHER
    expValue                = (avgPercGain * hitRatio) - (abs(avgPercLoss) * (1 - hitRatio))
    tradesPerYear           = totalTrades / years
    annTurnover             = dfTrading['exposure'].diff().loc[lambda x: x > 0].sum() / ((dfBasic.index[-1] - dfBasic.index[0]).days / 365.25)
    longVSshortTrades       = (dfReturn['longReturnsPerc'] != 0).sum() / (dfReturn['shortReturnsPerc'] != 0).sum()
    marketVola              = dfBasic['marketReturns'].std() * np.sqrt(trDaysYear)
    systemVola              = dfReturn['pfReturnsNetto'].std() * np.sqrt(trDaysYear)
    kelly                   = (expValue / (avgPercGain - (1 - hitRatio) * avgPercLoss + 1e-6)) * (1 / tradesPerYear)

    dict1ticker1set         = {'cagr': cagr, 'drawdown': drawdown, 'bliss': bliss, 'cagrAcid': cagrAcid, 'drawdownAcid': drawdownAcid, 'blissAcid': blissAcid, 'kiss': kiss, 'avgLongGain': avgLongGain, 'avgShortGain': avgShortGain, 'avgLongLoss': avgLongLoss, 'avgShortLoss': avgShortLoss, 'avgPercGain': avgPercGain, 'avgPercLoss': avgPercLoss, 'longVSshortTrades': longVSshortTrades, 'winningTrades': winningTrades, 'totalTrades': totalTrades, 'hitRatio': hitRatio, 'expValue': expValue, 'tradesPerYear': tradesPerYear, 'annTurnover': annTurnover, 'marketVola': marketVola, 'systemVola': systemVola, 'kelly': kelly}
    dict1ticker1set         = {k: int(v) if isinstance(v, float) and v.is_integer() else round(v, 3) if isinstance(v, float) else v for k, v in dict1ticker1set.items()}

    dfStats.drop(columns=dfBasic.columns.tolist(), inplace=True)
    dfStats.drop(columns=dfTrading.columns.tolist(), inplace=True)
    dfStats.drop(columns=dfReturn.columns.tolist(), inplace=True)
    return dfStats, dict1ticker1set

# STORE
def store1ticker1set():
    global dict1ticker1set
    dict1ticker1set[ticker] = {'cagr': dict1ticker1set['cagr'], 'drawdown': dict1ticker1set['drawdown'], 'bliss': dict1ticker1set['bliss'],
        'tradesPerYear': dict1ticker1set['tradesPerYear'], 'annTurnover': dict1ticker1set['annTurnover'], 'hitRatio': dict1ticker1set['hitRatio'],
        'expValue': dict1ticker1set['expValue'], 'systemVola': dict1ticker1set['systemVola'], 'avgPercGain': dict1ticker1set['avgPercGain'], 'avgPercLoss': dict1ticker1set['avgPercLoss']}
    return dict1ticker1set
def store1tickerXsets():
    global dict1tickerXsets
    if 'combinations' not in dict1tickerXsets:
        dict1tickerXsets['combinations'] = []
    dict1tickerXsets['combinations'].append({
        'longEntry': a,
        'longExit': b,
        'shortEntry': c,
        'shortExit': d,
        'cagr': dict1ticker1set['cagr'],
        'drawdown': dict1ticker1set['drawdown'],
        'bliss': dict1ticker1set['bliss'],
        'hitRatio': dict1ticker1set['hitRatio'],
        'expValue': dict1ticker1set['expValue'],})
    return dict1tickerXsets
def store1ticker1set():
    criterion='bliss'
    global dict1ticker1bestSet
    if 'dict1ticker1bestSet' not in globals() or dict1ticker1set.get(criterion, 0) > dict1ticker1bestSet.get(criterion, -float('inf')):
        dict1ticker1bestSet = {
            'ticker': ticker,
            'longEntry': a,
            'longExit': b,
            'shortEntry': c,
            'shortExit': d,
            'bliss': dict1ticker1set['bliss']}

# PLOT
def plotBasic():
    mpf.plot(dfBasic, type='candle', style='charles', title=f'{ticker} from {dfBasic.index[0].strftime("%Y-%m-%d")} to {dfBasic.index[-1].strftime("%Y-%m-%d")}')
def plotSignal():
    fig, axes = plt.subplots(nrows=2, ncols=1, figsize=(10, 15))
    xmin, xmax = min(dfBasic.index.min(), dfTrading.index.min()), max(dfBasic.index.max(), dfTrading.index.max())

    axes[0].plot(dfBasic.index, dfBasic['Close'], color='black')

    axes[0].scatter(dfTrading[(dfTrading['longEntry'] == 1) & (dfTrading['deltaExposure'] > 0)].index, dfBasic[(dfTrading['longEntry'] == 1) & (dfTrading['deltaExposure'] > 0)]['Close'], color='green', marker='*', s=100)
    axes[0].scatter(dfTrading[(dfTrading['longExit'] == 1) & (dfTrading['deltaExposure'] < 0)].index, dfBasic[(dfTrading['longExit'] == 1) & (dfTrading['deltaExposure'] < 0)]['Close'], color='blue', marker='_', s=100)
    axes[0].set_title('Long Entry and Exit Signals', fontweight='bold')
    axes[0].scatter(dfTrading[(dfTrading['shortEntry'] == 1) & (dfTrading['deltaExposure'] < 0)].index, dfBasic.loc[(dfTrading[(dfTrading['shortEntry'] == 1) & (dfTrading['deltaExposure'] != 0)].index), 'Close'], color='red', marker='*', s=100)
    axes[0].scatter(dfTrading[(dfTrading['shortExit'] == 1) & (dfTrading['deltaExposure'] != 0) & (dfTrading['shortEntry'] == 0)].index, dfBasic.loc[(dfTrading[(dfTrading['shortExit'] == 1) & (dfTrading['deltaExposure'] != 0)].index), 'Close'], color='navy', marker='_', s=100)
    axes[0].set_title('Short Entry and Exit Signals', fontweight='bold')

    ax2 = axes[1].twinx()
    ax2.plot(dfTrading.index, dfTrading['exposure'], color='navy', alpha=0.3, linewidth=2)
    ax2.set_ylabel('Exposure', fontweight='bold')
    ax2.set_ylim([-maxLeverage, maxLeverage])
    ax2.set_yticks(list(range(-maxLeverage-1, maxLeverage+2, min(buySize, sellSize))))

    axes[1].plot(dfBasic.index, dfBasic['Close'], color='black', linewidth=1.5)
    axes[1].plot(dfTrading.index, np.where((dfReturn['costBasis'] != 0) & (dfTrading['exposure'] > 0), np.abs(dfReturn['costBasis']), np.nan), color='green', linestyle='--', linewidth=1.0)
    axes[1].plot(dfTrading.index, np.where((dfReturn['costBasis'] != 0) & (dfTrading['exposure'] < 0), np.abs(dfReturn['costBasis']), np.nan), color='red', linestyle='--', linewidth=1.0)
    axes[1].plot(dfBasic.index, np.where(dfTrading['exposure'] > 0, dfBasic['Close'], np.nan), color='green', linewidth=1.0)
    axes[1].plot(dfBasic.index, np.where(dfTrading['exposure'] < 0, dfBasic['Close'], np.nan), color='red', linewidth=1.0)
    axes[1].set_title('Entry Levels', fontweight='bold')

    longValidIdx = dfStats.index[(dfReturn['longReturnsPerc'] < 0) | (dfReturn['longReturnsPerc'] > 0)]
    shortValidIdx = dfStats.index[(dfReturn['shortReturnsPerc'] < 0) | (dfReturn['shortReturnsPerc'] > 0)]
    [axes[1].annotate(f"{dfReturn.loc[i, 'longReturnsPerc']*100:.2f}%", (i, dfBasic.loc[i, 'Close'] * 1.05), textcoords="offset points", xytext=(0, 20), ha='center', fontsize=10, color='green') for i in longValidIdx]
    [axes[1].annotate(f"{dfReturn.loc[i, 'shortReturnsPerc']*100:.2f}%", (i, dfBasic.loc[i, 'Close'] * 0.95), textcoords="offset points", xytext=(0, -20), ha='center', fontsize=10, color='red') for i in shortValidIdx]

    for ax in fig.get_axes():
        for spine in ax.spines.values():
            spine.set_edgecolor('purple')
            spine.set_linewidth(0.5)

    for ax in fig.get_axes():
        ax.set_xticks(ax.get_xticks())
        ax.set_xticklabels(ax.get_xticklabels(), fontweight='bold')
        ax.set_yticks(ax.get_yticks())
        ax.set_yticklabels(ax.get_yticklabels(), fontweight='bold')

    for ax in [ax2]:
        ax.set_yticklabels(ax.get_yticklabels(), fontweight='bold')

    plt.subplots_adjust(hspace=0.75)
    plt.show()
def plotReturn():
    sns.set(style="white")
    fig, axes = plt.subplots(figsize=(10, 10))
    axes.plot(dfReturn.index, dfReturn['longshortTradeResults'], label='long & short cumsum trade results', color='navy')
    axes.plot(dfReturn.index, dfReturn['nominalFX'], label='nominal uncompounded', color='black')
    axes.plot(dfReturn.index, dfReturn['nominalFXCompounded'], label='nominal compounded', color='purple')

    for ax in fig.get_axes():
        for spine in ax.spines.values():
            spine.set_edgecolor('purple')
            spine.set_linewidth(0.5)

        for label in ax.get_xticklabels():
            label.set_fontweight('bold')
        for label in ax.get_yticklabels():
            label.set_fontweight('bold')

    lines1, labels1 = axes.get_legend_handles_labels()
    axes.legend(lines1, labels1, loc="upper left", prop={'weight':'bold'})
    plt.tight_layout()
    plt.show()
def plotHistogram():
    sns.set(style="white")
    fig, ax = plt.subplots(1, 1, figsize=(5, 6))
    dataPortfolio = dfReturn['pfReturnsBrutto'][dfReturn['pfReturnsBrutto'] != 0]
    dataMarket = dfBasic['marketReturns']
    maxRange = max(dataPortfolio.max(), dataMarket.max())
    minRange = min(dataPortfolio.min(), dataMarket.min())
    bins = 80
    ax.hist(dataPortfolio, bins=bins, range=(minRange, maxRange), color='navy', alpha=0.9, label='Portfolio Brutto Returns')
    ax.hist(dataMarket, bins=bins, range=(minRange, maxRange), color='purple', alpha=0.3, label='Market Returns')
    ax.set_title('Portfolio and Market Returns', fontweight='bold')
    ax.xaxis.set_major_formatter(mticker.ScalarFormatter())
    ax.yaxis.set_major_formatter(mticker.ScalarFormatter())
    [label.set_fontweight('bold') for label in ax.get_xticklabels()]
    [label.set_fontweight('bold') for label in ax.get_yticklabels()]
    ax.legend()
    plt.show()
def plotTable():
    filteredMetrics = {k: v for k, v in dict1ticker1set.items() if k not in ['winPeriods', 'lossPeriods']}
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
def plotTickerLoop3D():
    criteria = ['cagr', 'drawdown', 'bliss', 'hitRatio', 'expValue']
    fig = plt.figure(figsize=(15, 5))
    for idx, criterion in enumerate(criteria):
        keys = ('longEntry', 'longExit', criterion)
        entryVals, exitVals, criterionVals = zip(*[(d[keys[0]], d[keys[1]], d[keys[2]]) for d in dict1tickerXsets.get('combinations', [])])
        gridX, gridY = np.mgrid[min(entryVals):max(entryVals):10j, min(exitVals):max(exitVals):10j]
        gridZ = griddata((entryVals, exitVals), criterionVals, (gridX, gridY), method='linear')
        ax = fig.add_subplot(1, len(criteria), idx+1, projection='3d')
        ax.plot_surface(gridX, gridY, gridZ, cmap='magma', linewidth=0, antialiased=True)
        ax.set_xlabel('Entry', fontweight='bold')
        ax.set_ylabel('Exit', fontweight='bold')
        ax.set_zlabel(criterion, fontweight='bold')
        ax.invert_xaxis()
        ax.set_xticks(ax.get_xticks())
        ax.set_yticks(ax.get_yticks())
        ax.set_zticks(ax.get_zticks())
        ax.set_xticklabels(ax.get_xticklabels(), fontweight='bold', fontsize=6)
        ax.set_yticklabels(ax.get_yticklabels(), fontweight='bold', fontsize=6)
        ax.set_zticklabels(ax.get_zticklabels(), fontweight='bold', fontsize=6)
        plt.subplots_adjust(wspace=0.6)
    plt.show()
def plotCorrMatrix():
    correlationMatrix = dfFeatureTest.corr()
    reducedCorrelationMatrix = correlationMatrix.loc[dfTargetFeature.columns, dfFloatFeature.columns]
    sns.heatmap(reducedCorrelationMatrix, annot=True, cmap=['grey', 'purple', 'navy'], fmt='.0%', vmin=-0.75, vmax=0.75,
                annot_kws={"style": "italic", "weight": "bold", "size": 7},
                cbar_kws={'label': 'Correlation (%)', 'orientation': 'vertical'},
                linewidths=.8, linecolor='black')
    plt.xticks(fontsize=8)
    plt.yticks(fontsize=8)
    plt.subplots_adjust(bottom=0.25)
    plt.show()
def plotCorrScatter():
    fig, axes = plt.subplots(3, 3, figsize=(15, 15))
    axes = axes.ravel()
    colIndices = [1, 2, 3, 4, 5, 6, 7, 8, 9]
    colNames = dfFeatureTest.columns[colIndices]
    for idx, colName in enumerate(colNames):
        x, y = dfFeatureTest[colName], dfFeatureTest[dfFeatureTest.columns[0]]
        mask = np.isfinite(x) & np.isfinite(y)
        x, y = x[mask], y[mask]
        try:
            coeff, _ = curve_fit(lambda x, a, b: a * x + b, x, y)
            yfit = np.poly1d(coeff)
            r2 = r2_score(y, yfit(x))
            axes[idx].scatter(x, y, color='grey')
            axes[idx].plot(x, yfit(x), 'purple')
            axes[idx].set_title(f"{colName} vs {dfFeatureTest.columns[0]}", fontsize=8)
            axes[idx].set_xlabel(colName, fontsize=8)
            axes[idx].set_ylabel(dfFeatureTest.columns[0], fontsize=8)
            axes[idx].text(0.05, 0.9, f"r² = {r2:.2f}", ha='left', va='top', transform=axes[idx].transAxes,
                           bbox=dict(facecolor='white', alpha=0.9, edgecolor='navy'))
        except Exception as e:
            print(f"An error occurred: {e}")
    plt.subplots_adjust(hspace=0.4)
    plt.show()

# MAIN
if __name__ == "__main__":

     if mode in ('classicBacktest', 'paraloopBacktest', 'featureTesting', 'concatFeatureTesting'):
        tickers, annFactor                                                      = initTicker(), annualizationFactor()
        longEntry, longExit, shortEntry, shortExit                              = initParameter()
        triggerPrice1, triggerPrice                                             = 'Close', 'Close'
        dict1ticker1set, dict1tickerXsets, dict1ticker1bestSet, dictXticker1set = {}, {}, {}, {}

        for ticker in tickers:
            print(ticker)

            if mode == 'classicBacktest':
                dfBasic                                                          = basicData()
                dfTargetFeature                                                  = targetFeatureData()
                dfFloatFeature                                                   = floatFeatureData()
                dfBoolFeature                                                    = boolFeatureData()
                dfTrading                                                        = tradingData(longEntry, longExit, shortEntry, shortExit)
                dfReturn                                                         = returnData()
                dfStats, dict1ticker1set                                         = statsData()

                #plotBasic()
                #plotSignal()
                #plotReturn()
                #plotHistogram()
                plotTable()
            if mode == 'paraloopBacktest':
                startTime = time.time()
                dfBasic                                                           = basicData()
                dfTargetFeature                                                   = targetFeatureData()
                dfFloatFeature                                                    = floatFeatureData()
                dfBoolFeature                                                     = boolFeatureData()
                longEntry, longExit, shortEntry, shortExit                        = initParameter()
                for a in longEntry:
                    for b in longExit:
                        for c in shortEntry:
                            for d in shortExit:
                                dfTrading = tradingData(a, b, c, d)
                                dfReturn = returnData()
                                dfStats, dict1ticker1set = statsData()

                                store1tickerXsets()
                elapsedTime = time.time() - startTime
                print(f"Time elapsed: {elapsedTime:.2f} seconds")
                
                plotTickerLoop3D()
                #print(dict1ticker1bestSet)
            if mode in ('featureTesting', 'concatFeatureTesting'):
                dfBasic                                          = basicData()
                dfTargetFeature                                  = targetFeatureData()
                dfFloatFeature                                   = floatFeatureData()
                dfBoolFeature                                    = boolFeatureData()
                dfFeatureTest                                    = pd.concat([dfTargetFeature.shift(-trail1), dfFloatFeature.pct_change(), dfBoolFeature], axis=1).dropna()

                cutOff = 0
                dfFeatureTest[dfFeatureTest.apply(lambda x: x.isin(x.nlargest(cutOff)), axis=0)] = np.nan
                dfFeatureTest[dfFeatureTest.apply(lambda x: x.isin(x.nsmallest(cutOff)), axis=0)] = np.nan
                dfFeatureTest.replace([np.inf, -np.inf], np.nan, inplace=True)
                dfFeatureTest.ffill(inplace=True)

                print(dfFeatureTest)
                print([(col,idx)for idx,col in enumerate(dfTargetFeature.columns)])
                print([(col,idx)for idx,col in enumerate(dfFloatFeature.columns)])
                print([(col,idx)for idx,col in enumerate(dfBoolFeature.columns)])
                print([(col,idx)for idx,col in enumerate(dfFeatureTest.columns)])

                plotCorrMatrix()
                plotCorrScatter()