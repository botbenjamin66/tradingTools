# CODE INFRASTRUCTURE
createTool
    assetObject(source, name, startDate, endDate, curr)
    timesalesObject(name, date)
    transactionsObject(name)

        backtestTool: dataObject: dashboard
        backtestsTool: dataObject1, dataObject2, ...: dict/dashboard
        bestparamsTool: dataObject: 3Dplot
        correlationTool: dataObject1, dataObject2, ...: dashboard

        timesalesTool: timesalesObject: plot

        tradingstatsTool: transactionsObject: dashboard

        funcholdingsTool: safari

# VOCABULARY
    price1 : date, open, high, low, close, volume
    price2 : time, date, bid, ask, volume
    wiki1: date, close
    wiki2: time, date, isin, ...
    ts : time, date, price, volume

# NEXT STEPS
    sanity check backtests backtestsTool
    create volume trigger signals and exits
    create blackbastardTool - > run tickers , give categories of stocks
    createTool improvement: more object types + integrate tsTool adn wikiTool + FRED API + ECB + ...
