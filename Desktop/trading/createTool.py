import yfinance as yf
import pandas as pd

# PRICE1
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
        # Implement data fetching logic for Interactive Brokers
        pass

# INDEX OBJECT : DATE | INDEX1 | INDEX...

# TRADING OBJECT : TIME | BID | ASK | VOLUME

# TS
class timeSalesObject:
    def __init__(self, name, date):
        self.name = name
        self.date = date
    def fetchTimeSales(self):
        pass

# WIKI1
class transactionObject:
    def __init__(self, name):
        self.name = name
    def processTransaction(self):
        pass
# WIKI2

# PRODUCTION
class dataFactory:
    def createData(self, source, name, startDate, endDate, interval):
        if source == "yfinance":
            return yfinanceObject(name, startDate, endDate, interval)
        elif source == "interactiveBrokers":
            return interactiveBrokersObject(name, startDate, endDate, interval)
        else:
            raise ValueError("Unknown source")


