import pandas as pd
import numpy as np
import time
import glob
import os

def dfBasic():
    downloadsPath = os.path.expanduser('~/Downloads')
    filePaths = [file for file in sorted(glob.glob(f"{downloadsPath}/W*.csv"), key=os.path.getmtime, reverse=True)]
    latestFiles = filePaths[:2]

    # PRICE DATA
    if latestFiles:
        dfPrice = pd.read_csv(latestFiles[0], sep=';', decimal=',', thousands='.', engine='python', encoding='latin1', skiprows=5)
        dfPrice.drop(dfPrice.columns[1], axis=1, inplace=True)
        dfPrice['Date'] = pd.to_datetime(dfPrice.iloc[:, 0].str[:10], format='%d.%m.%Y')
        dfPrice['Time'] = dfPrice.iloc[:, 0].str[10:].str.strip()
        dfPrice.set_index('Date', inplace=True)
        dfPrice.drop(dfPrice.columns[0], axis=1, inplace=True)
        dfPrice.drop(columns=['Time'], inplace=True)

    # TRANSACTION DATA
    if len(latestFiles) > 1:
        dfTransactions = pd.read_csv(latestFiles[1], sep=';', decimal=',', thousands='.', engine='python', encoding='latin1', skiprows=5)
        dfTransactions['Date'] = pd.to_datetime(dfTransactions.iloc[:, 0].str[:10], format='%d.%m.%Y')
        dfTransactions['Time'] = dfTransactions.iloc[:, 0].str[10:].str.strip()
        dfTransactions.set_index('Date', inplace=True)

        # CUTOFF DATE
        cutOffDate = pd.to_datetime('01.01.2023', format='%d.%m.%Y')
        dfTransactions = dfTransactions[dfTransactions.index >= cutOffDate]
        dfTransactions.drop(dfTransactions.columns[0], axis=1, inplace=True)
        dfTransactions.insert(0, 'Time', dfTransactions.pop('Time'))

        # RENAME COLUMNS
        transaction_types = ['Wertpapier-Transaktion(Verkauf)', 'Wertpapier-Transaktion(Kauf)']
        dfTransactions = dfTransactions[dfTransactions['Beschreibung'].isin(transaction_types)]
        dfTransactions['Beschreibung'] = dfTransactions['Beschreibung'].replace({
            'Wertpapier-Transaktion(Kauf)': 'buy', 'Wertpapier-Transaktion(Verkauf)': 'sell'})
        dfTransactions = dfTransactions.filter(regex='^(?!.*Brutto).*$')

        # TRADES PER ISIN
        dfTransactions.sort_values(by=['ISIN', 'Date'], inplace=True)
        dfTransactions['Account'] = dfTransactions.groupby('ISIN')['ÄnderungAnzahl'].cumsum()
        td = dfTransactions
        isNewIsin = (td['ISIN'] != td['ISIN'].shift()).astype(bool)
        wasAccountZero = (td['Account'].shift() == 0).astype(bool)
        resetTrade = isNewIsin | wasAccountZero
        groupKeys = resetTrade.cumsum()
        td['Trades'] = td.groupby(groupKeys).cumcount() + 1

        # INDEX MAP ALPACA
        dfTransactions['Alpaca'] = dfTransactions.index.map(dfPrice['Close'])
        dfTransactions['Alpaca'].fillna(method='ffill', inplace=True)
        dfTransactions['Exposure'] = 1 - ((dfTransactions['Cashnachher'] / 1000) / dfTransactions['Alpaca'])
        dfTransactions['tradeSize'] = (dfTransactions['ÄnderungCash'] / 1000) / dfTransactions['Alpaca'] 

        # COST BASIS AND RETURNS
        dfTransactions.reset_index(drop=True, inplace=True)
        dfTransactions['costBasis'] = np.nan
        dfTransactions.loc[dfTransactions['Trades'] == 1, 'costBasis'] = dfTransactions['Preis']
        for i, row in dfTransactions.iterrows():
            if row['Trades'] != 1:
                change_amount = row['ÄnderungAnzahl']
                amount_after = row['Anzahlnachher']
                if row['ÄnderungCash'] < 0 and amount_after != 0:
                    dfTransactions.at[i, 'costBasis'] = (
                        row['Preis'] * (change_amount / amount_after) +
                        dfTransactions.at[i - 1, 'costBasis'] * (1 - (change_amount / amount_after)))
                elif i > 0:
                    dfTransactions.at[i, 'costBasis'] = dfTransactions.at[i - 1, 'costBasis']

        dfTransactions['percReturn'] = np.where(dfTransactions['ÄnderungCash'] > 0, (dfTransactions['Preis'] - dfTransactions['costBasis']) / dfTransactions['costBasis'], np.nan)
        dfTransactions['pfReturn'] = dfTransactions['percReturn'] * (dfTransactions['ÄnderungCash'] / dfTransactions['Alpaca'])

        dfTransactions['cumPfReturn'] = dfTransactions['pfReturn'].cumprod()

    return dfPrice, dfTransactions

dfPrice, dfTransactions = dfBasic()
print(dfPrice)
print(dfTransactions)

# dashboard: x, y
# alpaca, sdax, turnoverX
# avgGain, avgLoss, avgGainX, avgLossX, hitRate, hitRateX, avgHoldingPeriod, avgHoldingPeriodX
# last 5 buy charts, last 5 sell charts
# timeline 30days: winner/looser