import pandas as pd
import numpy as np
import yfinance as yf
import matplotlib.pyplot as plt

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

def downloadData(ticker, backtestStart, endDate, interval):
    df = yf.download(ticker, start=backtestStart, end=backtestEnd, interval=inputDataInterval)
    if df.empty:
        df = yf.download(ticker, start="max", end=backtestEnd, interval=inputDataInterval)
    df = df.drop(columns=['Close'])
    df = df.rename(columns={'Adj Close': 'Close'})
    df.insert(0, 'Close', df.pop('Close'))
    return df

def boSignals(df, longTrailEntry, longTrailExit, shortTrailEntry):
    df['longEntryBo'] = np.where(df['Close'] > df['Close'].shift(1).rolling(window=longTrailEntry).max(), 1, 0)
    df['longExitBo'] = np.where(df['Close'] < df['Close'].shift(1).rolling(window=longTrailExit).max(), 1, 0)
    df['shortEntryBo'] = np.where(df['Close'] < df['Close'].shift(1).rolling(window=shortTrailEntry).max(), 1, 0)
    df['shortExitBo'] = np.where(df['Close'] > df['Close'].shift(1).rolling(window=longTrailExit).max(), 1, 0)
    return df

def tradeSignals(df):
    df['longEntrySignal'] = np.where(df['longEntryBo'] == 1, 1, 0)
    df['longExitSignal'] = np.where(df['longExitBo'] == 1, 1, 0)
    df['shortEntrySignal'] = np.where(df['shortEntryBo'] == 1, 1, 0)
    df['shortExitSignal'] = np.where(df['shortExitBo'] == 1, 1, 0)
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

    cagrLong = df['longEquity'].iloc[-1] ** (1 / testLengthYears) - 1
    cagrShort = df['shortEquity'].iloc[-1] ** (1 / testLengthYears) - 1
    cagrTotal = df['totalEquity'].iloc[-1] ** (1 / testLengthYears) - 1
    maxDrawLong = ((df['longEquity'] - df['longEquity'].cummax()) / df['longEquity'].cummax()).min()
    maxDrawShort = ((df['shortEquity'] - df['shortEquity'].cummax()) / df['shortEquity'].cummax()).min()
    maxDrawTotal = ((df['totalEquity'] - df['totalEquity'].cummax()) / df['totalEquity'].cummax()).min()
    blissLong = cagrLong / maxDrawLong  
    blissShort = cagrShort / maxDrawShort
    blissTotal = cagrTotal / maxDrawTotal

    return {
        'cagrLong': cagrLong,
        'cagrShort': cagrShort,
        'cagrTotal': cagrTotal,
        'maxDrawLong': maxDrawLong,
        'maxDrawShort': maxDrawShort,
        'maxDrawTotal': maxDrawTotal,
        'blissLong': blissLong,
        'blissShort': blissShort,
        'blissTotal': blissTotal
    }
    
#TRADING FRAMEWORK
inputDataInterval = '1wk'
backtestStart, backtestEnd = 2015, 2020
commissions, spread, slippage, interest = 0.01, 0.01, 0.01, 0.02
entryPrice, exitPrice = 'Open', 'Close' #Close, Open, High, Low

longTrailEntry = 10
longTrailExit = 4
shortTrailEntry = 10
shortTrailExit = 4

#TRADE UNIVERSE
tickers = ["^GDAXI", "GBPCHF=X", "GC=F"]
ticker_names = {"^GDAXI": "DAX", "GBPCHF=X": "GBP/CHF", "GC=F": "Gold"}
data_dict = {}
results = {}    

for ticker
    for x in trendSystem
     make stats 
      store in df/dic=results
    make 4D chart
 next ticker