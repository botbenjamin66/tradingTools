import pandas as pd
import numpy as np
import matplotlib.pyplot as plt

def fedCycle():
    return None
def qqq21ema177maMACD():
    return None
def aroundFullMoon():
    return None
def mDeltaM1EU():
    return None
def sdaxAtr22to77():
    return None
def btcReturnAvg():
    return None
def stocksNettedEu():
    return None
def naaimReturnAvg():
    return None

def df1():
    path = "/Users/benjaminsuermann/Desktop/macrovisionData/treasuries1990-2023.csv"
    df1 = pd.read_csv(path)
    df1['∂2yr'] = df1['TYLD-TCMR-2Yr-A'].diff()
    print("df1:", df1.columns)
    df1.set_index('date', inplace=True)
    df1 = df1['∂2yr']
    return df1
    path1 = "/Users/benjaminsuermann/Downloads/Brent Oil Futures Historical Data 1989-05.csv"
    path2 = "/Users/benjaminsuermann/Downloads/Brent Oil Futures Historical Data 2004-23.csv"
    df20 = pd.read_csv(path1)
    df21 = pd.read_csv(path2)
    df2 = pd.concat([df20, df21]).drop_duplicates()
    print("df2:", df2.columns)
    df2.set_index('Date', inplace=True)
    df2['∂oil'] = df2['Price'].diff()
    df2 = df2['∂oil']
    return df2
def btcReturnAvg():
    df3 = pd.read_csv("/Users/benjaminsuermann/Downloads/BTC_USD Bitfinex Historical Data.csv")
    df3.set_index('Date', inplace=True)
    df3['∂btc'] = df3['Price'].diff().fillna(0)
    df3 = df3['∂btc']
    plt.plot(df3)
    plt.show()
    return df3
