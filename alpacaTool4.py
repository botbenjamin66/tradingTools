from matplotlib.ticker import MaxNLocator
import matplotlib.dates as mdates
import matplotlib.pyplot as plt
from datetime import datetime
import pandas as pd
import glob
import os

def dfBasic(inputDays):
    folder_path = r'Users/benjaminsuermann/downloads'
    file_paths = sorted(
        glob.glob(f"{folder_path}\\*01.csv"),
        key=os.path.getmtime,
        reverse=True
    )[:inputDays + 1]

    dfs = {} 
    for i, filePath in enumerate(file_paths, start=1):
        df = pd.read_csv(filePath, sep=';', decimal=',', thousands='.', engine='python', encoding='latin1')

        df[['Date', 'Time']] = df.iloc[:, 0].str.split(' ', n=1, expand=True)
        df.drop(df.columns[0], axis=1, inplace=True)

        df['Date'] = pd.to_datetime(df['Date'], format='%d.%m.%Y').dt.date
        df.set_index(pd.to_datetime(df.pop('Time'), format='%H:%M:%S').dt.time, inplace=True)
        df.rename(columns={'Kurs': 'Price', 'WÃ¤hrung': 'Currency', 'StÃ¼ck': 'Contracts', 'Kumuliert': 'Cumulative'}, inplace=True)

        df = df.iloc[::-1]
        dateColumn = df.pop('Date')
        df.insert(0, 'Date', dateColumn)

        trail1, trail2 = 2, 11
        df['VolWeightedPrice'] = df['Price'] * df['Contracts']
        df['TrailingPrice1'] = df['Price'].ewm(span=trail1, adjust=False).mean()
        df['TrailingPrice2'] = df['Price'].ewm(span=trail2, adjust=False).mean()

        cutOff = 2
        largest_indices = df['Contracts'].nlargest(cutOff).index
        df.drop(largest_indices, inplace=True)

        df['bigOrders'] = df['Contracts'].where(df['Contracts'] > df['Contracts'].quantile(0.8), 0)
        df['smallOrders'] = df['Contracts'].where(df['Contracts'] < df['Contracts'].quantile(0.25), 0)
        df['VWAP'] = (df['VolWeightedPrice']).cumsum() / df['Contracts'].cumsum()
        
        df['PriceRange'] = df['Price'].max() - df['Price'].min()
        df['PriceChangePercent'] = df['Price'].pct_change()
        df['NormalizedChange'] = df['PriceChangePercent'] / df['PriceRange']
        df['Direction'] = (~df['Price'].diff().le(0) * 2 - 1)
        df['AdjustedVolume'] = df['Contracts'] * df['Direction'] * df['NormalizedChange']
        df['OBV'] = df['AdjustedVolume'].cumsum()

        dfs[f'day{i}'] = df

    return dfs
def plotDfBasic(df):
    avg_price = df['Price'].mean()
    times = mdates.date2num([datetime.combine(datetime.min.date(), t) for t in df.index])
    fig, axes = plt.subplots(4, 1, figsize=(10, 20), sharex=True)

    contracts_mask = df['Contracts'] != 0
    cumulative_mask = df['Cumulative'] != 0
    big_orders_mask = df['bigOrders'] != 0
    small_orders_mask = df['smallOrders'] != 0

    colors = {'contracts': 'navy', 'cumulative': 'orange', 'trailing1': 'navy', 'trailing2': 'orange', 'vwap': 'navy', 'obv': 'orange', 'big_orders': 'navy', 'small_orders': 'orange'}

    plotTitle = df['Date'].iloc[0].strftime('%Y-%m-%d')
    plt.suptitle(plotTitle, fontsize=14)

    axes[0].set_ylabel('Contracts in k)', fontsize=12)
    axes[0].plot_date(times[contracts_mask], (df['Contracts'] / 1000 * avg_price)[contracts_mask], '.', label='Contracts (in k)', color=colors['contracts'])
    axes0Secondary = axes[0].twinx()
    axes0Secondary.plot_date(times[cumulative_mask], (df['Cumulative'] / 1000)[cumulative_mask], '-', label='Cumulative (in k)', color=colors['cumulative'])
    axes0Secondary.set_ylabel('Cumulative (in k)', fontsize=12)
    axes[0].legend(loc='upper left')
    axes0Secondary.legend(loc='upper right')

    axes[1].set_ylabel('Price', fontsize=12)
    axes[1].plot_date(times, df['TrailingPrice1'], '-', label='TrailingPrice1', color=colors['trailing1'])
    axes[1].plot_date(times, df['TrailingPrice2'], '-', label='TrailingPrice2', color=colors['trailing2'])
    axes[1].legend(loc='upper left')

    axes[3].set_ylabel('VWAP', fontsize=12)
    axes[3].plot_date(times, df['VWAP'], '-', label='VWAP', color=colors['vwap'])
    axes3Secondary = axes[3].twinx()
    axes3Secondary.plot_date(times, df['OBV'], '-', label='OBV', color=colors['obv'], lw=0.5, ms=2)
    axes3Secondary.set_ylabel('OBV', fontsize=12)
    axes[3].legend(loc='upper left')
    axes3Secondary.legend(loc='upper right')

    axes[2].set_ylabel('Big Orders (k EUR)', fontsize=12)
    axes[2].plot_date(times[big_orders_mask], (df['bigOrders'] * avg_price / 1000)[big_orders_mask], 'o', label='Big Orders', color=colors['big_orders'], markersize=7)
    axes2Secondary = axes[2].twinx()
    axes2Secondary.plot_date(times[small_orders_mask], (df['smallOrders'] * avg_price)[small_orders_mask], 'o', label='Small Orders', color=colors['small_orders'], markersize=2.5)
    axes2Secondary.set_ylabel('Small Orders (EUR)', fontsize=12)
    axes[2].legend(loc='upper left')
    axes2Secondary.legend(loc='upper left', bbox_to_anchor=(0, 0.8))

    for ax in [axes[0], axes[1], axes0Secondary, axes[2], axes2Secondary, axes[3], axes3Secondary]:
        ax.xaxis.set_major_locator(mdates.MinuteLocator(byminute=[0, 30]))
        ax.xaxis.set_major_formatter(mdates.DateFormatter('%H:%M'))
        ax.xaxis.set_minor_locator(mdates.MinuteLocator(byminute=range(0, 60, 5)))
        ax.yaxis.set_major_locator(MaxNLocator(integer=True))
        plt.setp(ax.xaxis.get_majorticklabels(), rotation=45, fontsize=10)

    plt.subplots_adjust(hspace=0.3, left=0.1, right=0.85, bottom=0.1, top=0.95)
    plt.show()

dfData = dfBasic(inputDays=1) 

for day, df in dfData.items():
    print(f"Plotting {day} data")
    plotDfBasic(df)