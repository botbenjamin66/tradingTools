import matplotlib.pyplot as plt
import plotly.express as px
import mplfinance as mpf
import yfinance as yf
import seaborn as sns
import pandas as pd
import numpy as np
import random

# dfStats, dfStats plot, storing, looping over loopParamter, plot loops, interestCost, returnsVsCostBasis, top5drawdownPeriods, hillshading
# corr(cagrTrail/trWinRatio), exp.value to store

def initTicker(theme = 'btc'):
    if theme == 'equity':
        ticker = ["MWL=F", "^GDAXI"]
    elif theme == 'btc':
        ticker = ["BTC=F"]
    elif theme == 'random':
        randomizedTickers = ["MWL=F", "^GDAXI"]
        ticker = [random.choice(randomizedTickers)]
    else:
        ticker = [theme]
    return ticker

def basicData(backtestStart=2017, backtestEnd=2021, dataInterval='1d'):
    try:
        dfBasic = yf.download(ticker, start=str(backtestStart) + "-01-01", end=str(backtestEnd) + "-01-01", interval=dataInterval)
    except Exception as e:
        dfBasic = yf.download(ticker, end=str(backtestEnd) + "-01-01", interval=dataInterval)
    nanPercentage = dfBasic.isnull().sum().sum() / dfBasic.size * 100
    
    if dfBasic.empty or dfBasic.isnull().all().all():
        print(f"Failed to download data for {ticker}")
        return None
    print(f"NaN percentage: {nanPercentage}%")
    
    # dfBasic = dfBasic.drop(columns=['Close'])
    # dfBasic = dfBasic.rename(columns={'Adj Close': 'Close'})
    
    return dfBasic
def technicalData(dfBasic):
    dfTechnical = dfBasic.copy()
    dfTechnical['dailyReturns'] = dfTechnical['Close'].pct_change()
    dfTechnical['dailyReturnsVariance66'] = dfTechnical['dailyReturns'].rolling(window=66).var()
    dfTechnical['volume5'] = dfTechnical['Volume'].rolling(window=5).mean()
    dfTechnical['volume50'] = dfTechnical['Volume'].rolling(window=50).mean()
    dfTechnical['ema22'] = dfTechnical['Close'].ewm(span=22).mean()
    dfTechnical['ema77'] = dfTechnical['Close'].ewm(span=77).mean()
    dfTechnical['er22'] = dfTechnical['Close'].diff(22).abs() / dfTechnical['Close'].diff().abs().rolling(window=22).sum()
    dfTechnical['er77'] = dfTechnical['Close'].diff(77).abs() / dfTechnical['Close'].diff().abs().rolling(window=77).sum()
    dfTechnical['atr22'] = pd.concat([dfTechnical['High'] - dfTechnical['Low'], (dfTechnical['High'] - dfTechnical['Close']).abs(), (dfTechnical['Low'] - dfTechnical['Close']).abs()], axis=1).max(axis=1).rolling(window=22).mean()
    dfTechnical['atr77'] = pd.concat([dfTechnical['High'] - dfTechnical['Low'], (dfTechnical['High'] - dfTechnical['Close']).abs(), (dfTechnical['Low'] - dfTechnical['Close']).abs()], axis=1).max(axis=1).rolling(window=77).mean()
    dfTechnical['bo7-77'] = dfTechnical['Close'].rolling(window=77).apply(lambda x: sum([(x[-1] < val) | (x[-1] > val) for val in x[:-1][-7:]]))
    dfTechnical['macd'] = dfTechnical['ema22'] / dfTechnical['ema77'] - 1
    dfTechnical['chill'] = dfTechnical['atr22'] / dfTechnical['bo7-77']
    dfTechnical['noise'] = np.log(dfTechnical['er22']) - np.log(dfTechnical['er77'])
    dfTechnical['volumedriven'] = (dfTechnical['volume5'] / dfTechnical['volume50']) / dfTechnical['er22'].rolling(window=5).mean()
    dfTechnical.drop(columns=dfBasic.columns.tolist(), inplace=True)
    return dfTechnical
def signalData(dfBasic, dfTechnical, style = 'ed'):
    if style == 'ed':
        longEntry, longExit, shortEntry, shortExit =33, 9, 33, 9
        dfSignal = pd.concat([dfBasic, dfTechnical], axis=1)

        # signals
        dfSignal['longEntry'] = dfBasic[triggerPrice].gt(dfBasic[triggerPrice].shift(1).rolling(window=longEntry).max())
        dfSignal['longExit'] = dfBasic[triggerPrice].lt(dfBasic[triggerPrice].shift(1).rolling(window=longExit).min())
        dfSignal['shortEntry'] = dfBasic[triggerPrice].lt(dfBasic[triggerPrice].shift(1).rolling(window=shortEntry).min())
        dfSignal['shortExit'] = dfBasic[triggerPrice].gt(dfBasic[triggerPrice].shift(1).rolling(window=shortExit).max())
        
        # exposure
        conditions = [dfSignal['longEntry'], dfSignal['longExit']]
        choices = [1, 0]
        dfSignal['longExposure'] = np.select(conditions, choices, default=np.nan)
        dfSignal['longExposure'] = dfSignal['longExposure'].ffill() 
        conditions = [dfSignal['shortEntry'], dfSignal['shortExit']]
        choices = [-1, 0]
        dfSignal['shortExposure'] = np.select(conditions, choices, default=np.nan)
        dfSignal['shortExposure'] = dfSignal['shortExposure'].ffill()  
        dfSignal['exposure'] = dfSignal['longExposure'] + dfSignal['shortExposure']
        
        # entryLevel        
        dfSignal['exposureDelta'] = dfSignal['exposure'].diff()
        conditions = [(dfSignal['exposureDelta'] != 0) & (dfSignal['exposure'] > 0),
                      (dfSignal['exposureDelta'] != 0) & (dfSignal['exposure'] < 0), dfSignal['exposure'] == 0]
        choices = [dfBasic[tradePrice],-dfBasic[tradePrice],0]
        dfSignal['entryLevel'] = np.select(conditions, choices, default=np.nan)
        dfSignal['entryLevel'] = dfSignal['entryLevel'].ffill()

        # exitLevel
        conditions = [dfSignal['exposure'] > 0, dfSignal['exposure'] < 0]
        choices = [dfBasic[tradePrice].rolling(window=longExit).min(), dfBasic[tradePrice].rolling(window=shortExit).max()]
        dfSignal['exitLevel'] = np.select(conditions, choices, np.nan)
        
        dfSignal.drop(columns=dfBasic.columns.tolist() + dfTechnical.columns.tolist(), inplace=True)
        return dfSignal, longEntry, longExit, shortEntry, shortExit
def returnData(dfBasic, dfSignal, commissions=0.003, spread=0.005, slippage=0.005, interest=0.03):
    dfReturn = pd.concat([dfBasic, dfSignal['dfSignal']], axis=1)
    costPerTrade = commissions + spread + slippage

    dfReturn['eqIntReturn'] = dfSignal['exposure'] * (dfBasic[tradePrice].pct_change())
    dfReturn['eqIntReturnAC'] = dfReturn['eqIntReturn'] - abs(np.where(dfSignal['exposure'].diff() != 0, costPerTrade * dfSignal['exposure'], 0))
    dfReturn['eqCurve'] = (1 + dfReturn['eqIntReturn']).cumprod()
    dfReturn['eqCurveAC'] = (1 + dfReturn['eqIntReturnAC']).cumprod()
    
    dfReturn.drop(columns=dfBasic.columns.tolist(), inplace=True)
    dfReturn.drop(columns=dfSignal.columns.tolist(), inplace=True)
    return dfReturn
def statsData(dfBasic, dfSignal, dfReturn, trDaysYear = 250):
    dfStats = pd.concat([dfBasic, dfSignal, dfReturn], axis=1)
    deltaDays = (dfBasic.index[-1] - dfBasic.index[0]).days
    years = deltaDays / 365

    # dfStats
    dfStats['heat'] = (1 - (dfSignal['exitLevel'] / dfBasic[tradePrice])) * dfSignal['exposure']
    dfStats['cagrTrail'] = dfReturn['eqCurveAC'].rolling(window=100).apply(lambda window: (window.iloc[-1] / window.iloc[0]) ** (1 / (100 / trDaysYear)) - 1)
    dfStats['annTurnover'] = dfSignal['exposure'].diff().abs().rolling(window=100).sum() / (100 / trDaysYear)
    dfStats['maxDrawdown'] = (dfReturn['eqCurve'] / (dfReturn['eqCurve'].rolling(window=150).max()) - 1)

    dfStats['longReturn'] = np.where((dfSignal['exposure'].shift() > 0) & (dfSignal['exposure'] == 0), (dfBasic[tradePrice] - dfSignal['entryLevel'].shift()) / dfSignal['entryLevel'].shift(), np.nan)
    dfStats['shortReturn'] = np.where((dfSignal['exposure'].shift() < 0) & (dfSignal['exposure'] == 0), -(dfBasic[tradePrice] - dfSignal['entryLevel'].shift()) / dfSignal['entryLevel'].shift(), np.nan)

    dfStats['winDays'] = dfReturn['eqIntReturn'][dfReturn['eqIntReturn'] > 0]
    dfStats['lossDays'] = dfReturn['eqIntReturn'][dfReturn['eqIntReturn'] < 0]

    dfStats['totalTrades'] = dfSignal['exposure'].diff().ne(0).sum()

    dfStats['winRateDaily77'] = dfReturn['eqIntReturn'].rolling(window=77).apply(lambda x: (x > 0).sum()) / (dfReturn['eqIntReturn'].rolling(window=77).apply(lambda x: (x > 0).sum()) + dfReturn['eqIntReturn'].rolling(window=77).apply(lambda x: (x < 0).sum()))
    dfStats['sharpeRatio'] = (dfReturn['eqIntReturn'].rolling(window=77).mean() / dfReturn['eqIntReturn'].rolling(window=77).std()) * np.sqrt(252)
    dfStats['sortinoRatio'] = (dfReturn['eqIntReturn'].mean() / dfReturn['eqIntReturn'][dfReturn['eqIntReturn'] < 0].std()) * np.sqrt(252)

    # dictStats
    cagr = (dfReturn['eqCurveAC'].iloc[-1]) ** (1 / years) - 1
    maxDraw = np.abs((dfReturn['eqCurveAC'] / dfReturn['eqCurveAC'].expanding(min_periods=1).max() - 1).min())
    bliss = max(cagr / maxDraw, 0)

    dfStats.drop(columns=dfBasic.columns.tolist(), inplace=True)
    dfStats.drop(columns=dfSignal.columns.tolist(), inplace=True)
    dfStats.drop(columns=dfReturn.columns.tolist(), inplace=True)
    return dfStats, cagr, maxDraw, bliss

def dataControlBasic():
    mpf.plot(dfBasic, type='candle', volume=True, style='blueskies')
def dataControlTechnical1():
    plt.figure(figsize=(11, 18))
    plt.subplot(5, 1, 1)
    plt.plot(dfBasic['Close'], label='Close Price')
    plt.plot(dfTechnical['ema22'], label='EMA 22')
    plt.plot(dfTechnical['ema77'], label='MA 99')
    plt.title('Price and Moving Averages')
    plt.legend()
    plt.subplot(5, 1, 2)
    plt.plot(dfTechnical['dailyReturns'], label='Daily Returns')
    plt.title('Daily Returns')
    plt.legend()
    plt.subplot(5, 1, 3)
    plt.plot(dfTechnical['volume5'], label='Volume 5')
    plt.plot(dfTechnical['volume50'], label='Volume 50')
    plt.title('Volume')
    plt.legend()
    plt.subplot(5, 1, 4)
    plt.plot(dfTechnical['er22'], label='ER 22')
    plt.plot(dfTechnical['er77'], label='ER 77')
    plt.title('Efficiency Ratio')
    plt.legend()
    plt.subplot(5, 1, 5)
    plt.plot(dfTechnical['atr22'], label='ATR 22')
    plt.plot(dfTechnical['atr77'], label='ATR 77')
    plt.title('Average True Range')
    plt.legend()
    plt.subplots_adjust(left=0.085, bottom=0.055, right=0.9, top=0.95, hspace=0.69)
    plt.show()
def dataControlTechnical2():
    #plt.style.use('default')
    print(dfTechnical.columns)
    fig, axes = plt.subplots(nrows=5, ncols=1, figsize=(8, 8))
    axes[0].plot(dfBasic.index, dfBasic['Close'], label='Close', color='blue')
    axes[0].plot(dfTechnical.index, dfTechnical['ema22'], label='EMA22', color='green', linestyle='--')
    axes[0].legend()
    axes[1].plot(dfTechnical.index, dfTechnical['chill'], label='Chill', color='purple')
    axes[1].legend()
    axes[2].plot(dfTechnical.index, dfTechnical['noise'], label='Noise', color='orange')
    axes[2].legend()
    axes[3].plot(dfTechnical.index, dfTechnical['macd'], label='MACD', color='cyan')
    axes[3].legend()
    axes[4].plot(dfTechnical.index, dfTechnical['volumedriven'], label='Volume Driven', color='magenta')
    axes[4].legend()
    plt.tight_layout()
    plt.show()
def dataControlSignal():
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
    ax[3].plot(dfSignal.index, np.where((dfSignal['entryLevel'] != 0) & (dfSignal['exposure'] > 0), np.abs(dfSignal['entryLevel']), np.nan), color='green', linestyle='--', linewidth=1.0, label='Long Entry Level')
    ax[3].plot(dfSignal.index, np.where((dfSignal['entryLevel'] != 0) & (dfSignal['exposure'] < 0), np.abs(dfSignal['entryLevel']), np.nan), color='red', linestyle='--', linewidth=1.0, label='Short Entry Level')
    ax[3].plot(dfBasic.index, np.where(dfSignal['exposure'] > 0, dfBasic['Close'], np.nan), color='green', linewidth=1.0, label='Long Exposure')
    ax[3].plot(dfBasic.index, np.where(dfSignal['exposure'] < 0, dfBasic['Close'], np.nan), color='red', linewidth=1.0, label='Short Exposure')
    ax[3].legend()
    ax[3].set_title('Entry Levels and Exposure')

    plt.subplots_adjust(left=0.085, bottom=0.055, right=0.9, top=0.95, hspace=0.69)
    plt.tight_layout()
    plt.show()
def dataControlReturn():
    fig, (ax1, ax2, ax3) = plt.subplots(3, 1, figsize=(10, 12), sharex=True)
    
    ax1.plot(dfBasic.index, dfBasic['Close'], label='Closes')
    ax1.set_ylabel('Closes')
    ax1.set_title('Closing Prices')
    ax1.legend()
    
    ax2.plot(dfReturn.index, dfReturn['eqIntReturnAC'], label='System Daily Return AC', color='red')
    ax2.plot(dfReturn.index, dfReturn['eqIntReturn'], label='System Daily Return', color='blue')
    ax2.set_ylabel('System Daily Return')
    ax2.set_title('System Daily Returns')
    ax2.legend()
    
    ax3.plot(dfReturn.index, dfReturn['eqCurve'], label='Equity Curve', color='green')
    ax3.plot(dfReturn.index, dfReturn['eqCurveAC'], label='Equity Curve After Costs', color='orange')
    ax3.set_xlabel('Date')
    ax3.set_ylabel('Equity')
    ax3.set_title('Equity Curve')
    ax3.legend()
    
    plt.show()
def dataControlStats():
    fig, ax = plt.subplots(nrows=4, ncols=1, figsize=(10, 24))

    ax[0].plot(dfStats.index, dfStats['annTurnover'], color='blue', label='Annual Turnover')
    ax[0].set_ylabel('Annual Turnover')
    ax[0].legend(loc='upper left')
    ax0_twin = ax[0].twinx()
    ax0_twin.plot(dfStats.index, dfStats['heat'], color='red', label='Heat')
    ax0_twin.set_ylabel('Heat')
    ax0_twin.legend(loc='upper right')

    sns.histplot(dfReturn['eqIntReturn'][dfReturn['eqIntReturn'] > 0], bins=20, color='green', kde=True, ax=ax[1], label='Winning Days')
    sns.histplot(dfReturn['eqIntReturn'][dfReturn['eqIntReturn'] < 0], bins=20, color='red', kde=True, ax=ax[1], label='Losing Days')
    ax[1].set_xlabel('Return')
    ax[1].set_ylabel('Frequency')
    ax[1].legend()

    ax[2].plot(dfStats.index, dfStats['winRateDaily77'], color='purple', label='Rolling Win Rate (window=77)')
    ax[2].set_xlabel('Date')
    ax[2].set_ylabel('Win Rate')
    ax[2].legend()
    ax2_twin = ax[2].twinx()
    ax2_twin.plot(dfStats.index, dfStats['maxDrawdown'], color='orange', label='Max Drawdown')
    ax2_twin.set_ylabel('Max Drawdown')
    ax2_twin.legend(loc='lower left')

    ax[3].plot(dfStats.index, dfStats['sharpeRatio'], color='teal', label='Sharpe Ratio (window=77)', lw=2)
    ax[3].plot(dfStats.index, dfStats['sortinoRatio'], color='magenta', linestyle='--', label='Sortino Ratio', lw=2)
    ax[3].set_xlabel('Date')
    ax[3].set_ylabel('Ratio')
    ax[3].legend()
    ax[3].set_title('Sharpe and Sortino Ratios')

    sns.set_style("whitegrid")
    sns.despine()
    plt.tight_layout(h_pad=0.79)
    plt.show()

def storeSingle(ticker, cagr, maxDrawdown, bliss):
    global dictSingle
    dictSingle[ticker] = {'cagr': cagr, 'maxDrawdown': maxDrawdown, 'bliss': bliss}
    return dictSingle
def storeLoop(ticker, cagr, maxDrawdown, bliss, longEntry, longExit, shortEntry, shortExit):
    global dictLoop
    dictLoop[ticker] = {'cagr': cagr, 'maxDrawdown': maxDrawdown, 'bliss': bliss,
        'longEntry': longEntry, 'longExit': longExit, 'shortEntry': shortEntry, 'shortExit': shortExit}
    return dictLoop
def storeBest(ticker, cagr, maxDrawdown, bliss):
    global dictBest
    if 'dictBest' not in globals() or cagr > dictBest['cagr']:
        dictBest = {'ticker': ticker, 'cagr': cagr, 'maxDrawdown': maxDrawdown, 'bliss': bliss}
    return None

if __name__ == "__main__":

    triggerPrice, tradePrice = 'Close',  'Open'
    tickers = initTicker()
    dictSingle, dictLoop, dictBest = {}, {}, {}
    
    for ticker in tickers:
        dfBasic                                                   = basicData()
        dfTechnical                                               = technicalData(dfBasic)
        #dfSignal,longEntry, longExit, shortEntry, shortExit      = signalData(dfBasic, dfTechnical)
        #dfReturn                                                 = returnData(dfBasic, dfSignal)
        #dfStats, cagr, maxDrawdown, bliss                        = statsData(dfBasic, dfSignal, dfReturn)
        
        #storeSingle(ticker, cagr, maxDrawdown, bliss)
        #storeLoop(ticker, cagr, maxDrawdown, bliss)
        #print(dictLoop)

        #dataControlBasic()
        dataControlTechnical1()
        #dataControlTechnical2()
        #dataControlSignal()
        #dataControlReturn()
        #dataControlStats()


