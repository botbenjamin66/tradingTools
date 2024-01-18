import yfinance as yf
import pandas as pd
import requests
import json
import os

# COLOUR CODE
empColours = {'lila': '#7A5DA9', 'blue': '#000080', 'beige': '#F5F5CC', 'grey': '#A9A9A9'}

# FINANCIAL DATA
class dataObject:
    def __init__(self, name, startDate, endDate, interval):
        self.name = name
        self.startDate = startDate
        self.endDate = endDate        
        self.interval = interval
    def fetchData(self):
        pass
class yfinanceObject(dataObject):
    def fetchData(self):
        try:
            data = yf.download(self.name, start=self.startDate, end=self.endDate, interval=self.interval)
            data.drop(columns=['Close'], inplace=True)
            data.rename(columns={'Adj Close': 'Close'}, inplace=True)
            return data
        except Exception as e:
            print(f"An error occurred while fetching data for {self.name}: {e}")
            return None
class interactiveBrokersObject(dataObject):
    def fetchData(self):
        pass
class fileDataObject(dataObject):
    def __init__(self, name, startDate, endDate, interval, fileName, skipRows):
        super().__init__(name, startDate, endDate, interval)
        self.fileName = fileName
        self.skipRows = skipRows
        self.filePath = os.path.join('W:\\Praktikanten und Werkstudenten\\Benjamin Suermann\\finData', self.fileName)

    def fetchData(self):
        try:
            if self.fileName.endswith('.xlsx') or self.fileName.endswith('.xls'):
                data = pd.read_excel(self.filePath, skiprows=self.skipRows, header=None)
            elif self.fileName.endswith('.csv'):
                data = pd.read_csv(self.filePath, skiprows=self.skipRows, header=None)
            else:
                raise ValueError('Unsupported file format')

            if data.columns[0] != 'Date':
                data.columns = ['Date', 'Close']  # Rename columns if header is not present
                data['Date'] = pd.to_datetime(data['Date'])  # Convert Date to datetime format
                data.set_index('Date', inplace=True)  # Set Date as the index
            else:
                data.set_index('Date', inplace=True)  # If header is present, set Date as the index directly

            return data
        except Exception as e:
            print(f"An error occurred while fetching data from {self.filePath}: {e}")
            return None

# BACKTESTED OBJECT
class backtestDataObject:
    def __init__(self, priceDataObject, triggerPrice, signalParams, buySize, sellSize, maxLeverage, tradeCosts, tradePrice, tickers):
        self.priceDataObject = priceDataObject
        self.triggerPrice = triggerPrice
        self.signalParams = signalParams
        self.buySize = buySize
        self.sellSize = sellSize
        self.maxLeverage = maxLeverage
        self.tradeCosts = tradeCosts
        self.tradePrice = tradePrice
        self.tickers = tickers
        self.dataObjects = {}
        self.allSystemMetrics = {}
    def createDataObjects(self):
        factory = dataFactory()
        for ticker in self.tickers:
            dataObject = factory.createData("yfinance", ticker, self.priceDataObject.startDate, self.priceDataObject.endDate, self.priceDataObject.interval)
            data = dataObject.fetchData()
            self.dataObjects[ticker] = data
    def calculateFeatures(self, trail):
        for ticker, df in self.dataObjects.items():
            df['volume' + str(trail)] = df['Volume'].rolling(window=trail).mean()
            df['ema' + str(trail)] = df[self.triggerPrice].ewm(span=trail).mean()
            df['er' + str(trail)] = df[self.triggerPrice].diff(trail).abs() / df[self.triggerPrice].diff().abs().rolling(window=trail).sum()
    def calculateSignals(self):
        for ticker, df in self.dataObjects.items():
            signalTrendTotal(df, self.triggerPrice, **self.signalParams)
    def calculateExposure(self):
        for ticker, df in self.dataObjects.items():
            if not (df['longEntry'].any() or df['longExit'].any()):
                df['longExposure'] = 0
            else:
                conditions = [df['longEntry'], df['longExit']]
                choices = [self.buySize, -self.sellSize]
                df['deltaExposure'] = np.select(conditions, choices, 0)
                df['longExposure'] = df['deltaExposure'].cumsum()
                for i in range(1, len(df)):
                    previousIndex = df.index[i - 1]
                    currentIndex = df.index[i]
                    newValue = min(self.maxLeverage, max(0, df.at[previousIndex, 'longExposure'] + df.at[currentIndex, 'deltaExposure']))
                    df.at[currentIndex, 'longExposure'] = newValue

            if not (df['shortEntry'].any() or df['shortExit'].any()):
                df['shortExposure'] = 0
            else:
                conditions = [df['shortEntry'], df['shortExit']]
                choices = [-self.buySize, self.sellSize]
                df['deltaExposure'] = np.select(conditions, choices, 0)
                df['shortExposure'] = df['deltaExposure'].cumsum()
                for i in range(1, len(df)):
                    previousIndex = df.index[i - 1]
                    currentIndex = df.index[i]
                    newValue = max(-self.maxLeverage, min(0, df.at[previousIndex, 'shortExposure'] + df.at[currentIndex, 'deltaExposure']))
                    df.at[currentIndex, 'shortExposure'] = newValue

            df['exposure'] = df['longExposure'] + df['shortExposure']
            df['deltaExposure'] = df['exposure'].diff()
    def calculateReturns(self):
        for ticker, df in self.dataObjects.items():
            costPerTrade = self.tradeCosts['commissions'] + self.tradeCosts['spread'] + self.tradeCosts['slippage']

            # PERFORMANCE METRICS
            df['interestCost'] = abs(df['exposure']) * self.tradeCosts['interest'] * (df.index.to_series().diff().dt.days / 365)
            df['marketReturns'] = df[self.triggerPrice].pct_change()
            df['percentageReturns'] = df['exposure'].shift() * df[self.tradePrice].pct_change()
            df['percentageReturnsAC'] = df['percentageReturns'] - abs(np.where(df['exposure'].diff() != 0, costPerTrade * df['exposure'], 0)) - abs(df['exposure']) * self.tradeCosts['interest'] * (df.index.to_series().diff().dt.days / 365)
            df['nominal'] = (1 + df['percentageReturns']).cumprod() * self.tradeCosts['nominalUSD']
            df['nominalAC'] = (1 + df['percentageReturnsAC']).cumprod() * self.tradeCosts['nominalUSD']
            df['nominalNakedAC'] = self.tradeCosts['nominalUSD'] + (self.tradeCosts['nominalUSD'] * df['percentageReturnsAC'].cumsum())

            # COST BASIS
            for i in range(len(df)):
                curExposure = df.iloc[i]['exposure']
                prevExposure = df.iloc[i-1]['exposure'] if i > 0 else np.nan
                curTradePrice = df.iloc[i][self.tradePrice]

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
    def calculateStats(self):
        for ticker, df in self.dataObjects.items():
            deltaDays = (df.index[-1] - df.index[0]).days
            years, trDaysYear = (deltaDays / 365.25), 252

            # TRADE RESULTS
            df['longAbsGain'] = np.where((df['exposure'] == 0) & (df['exposure'].shift() > 0), df[self.tradePrice] - df['costBasis'].shift(), np.nan)
            df['shortAbsGain'] = np.where((df['exposure'] == 0) & (df['exposure'].shift() < 0), -(df[self.tradePrice] - df['costBasis'].shift()), np.nan)
            df['longPercGain'] = np.where((df['exposure'] == 0) & (df['exposure'].shift() > 0), df['longAbsGain'] / df['costBasis'].shift(), np.nan)
            df['shortPercGain'] = np.where((df['exposure'] == 0) & (df['exposure'].shift() < 0), df['shortAbsGain'] / df['costBasis'].shift(), np.nan)
            df['controlPnl'] = self.tradeCosts['nominalUSD'] * (df['longPercGain'].fillna(0) + df['shortPercGain'].fillna(0) + 1).cumprod()
            
            # KEY METRICS
            cagr = ((df['nominalAC'].iloc[-1] / df['nominalAC'].iloc[1]) ** (1 / years)) - 1
            drawdown = np.abs((df['nominalAC'] / df['nominalAC'].expanding(min_periods=1).max() - 1).min())
            bliss = 0 if drawdown == 0 else max(cagr / drawdown, 0)
            cagrBenchmark = ((df[self.triggerPrice].iloc[-1] / df[self.triggerPrice].iloc[1]) ** (1 / years)) - 1
            drawdownBenchmark = np.abs((df[self.triggerPrice] / df[self.triggerPrice].expanding(min_periods=1).max() - 1).min())
            blissBenchmark = max(cagrBenchmark / drawdownBenchmark, 0)
            
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

            # NON-SINGLE-VALUE STATS
            winPeriods = df['percentageReturns'][df['percentageReturns'] > 0]
            lossPeriods = df['percentageReturns'][df['percentageReturns'] < 0]

            singleSystemMetrics = {'cagr': cagr, 'drawdown': drawdown, 'bliss': bliss, 'cagrBenchmark': cagrBenchmark, 'drawdownBenchmark': drawdownBenchmark, 'blissBenchmark': blissBenchmark, 'avgLongGain': avgLongGain, 'avgShortGain': avgShortGain, 'avgLongLoss': avgLongLoss, 'avgShortLoss': avgShortLoss, 'avgGain': avgGain, 'avgLoss': avgLoss, 'longVSshortTrades': longVSshortTrades, 'winningTrades': winningTrades, 'totalTrades': totalTrades, 'hitRatio': hitRatio, 'expValue': expValue, 'tradesPerYear': tradesPerYear, 'annTurnover': annTurnover, 'marketVola': marketVola, 'systemVola': systemVola, 'winPeriods': winPeriods, 'lossPeriods': lossPeriods}
            self.allSystemMetrics[ticker] = {'cagr': cagr, 'drawdown': drawdown, 'bliss': bliss, 'blissBenchmark': blissBenchmark, 'avgGain': avgGain, 'avgLoss': avgLoss, 'hitRatio': hitRatio, 'expValue': expValue, 'tradesPerYear': tradesPerYear}

# PRODUCTION
class dataFactory:
    def createData(self, dataType, name, startDate, endDate, interval, fileName=None, skipRows=None):
        if dataType == "yfinance":
            return yfinanceObject(name, startDate, endDate, interval)
        elif dataType == "file":
            if fileName is None or skipRows is None:
                raise ValueError("fileName and skipRows are required for file data type")
            return fileDataObject(name, startDate, endDate, interval, fileName, skipRows)
        else:
            raise ValueError("Unsupported data type")