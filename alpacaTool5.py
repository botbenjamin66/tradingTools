from dash import html, dcc, Output, Input, dash_table
from dash.dependencies import Input, Output
from plotly.subplots import make_subplots
import plotly.graph_objs as go
import matplotlib.pyplot as plt
import plotly.express as px
import pandas as pd
import yfinance as yf
import dash

# FINANCIAL DATA
dfs = {}
dataObjects = {}

for name, obj in dataObjects.items():
    df1 = obj.fetchData()
    df1.sort_index(ascending=True, inplace=True)
    df1 = df1.asfreq('B').ffill()
    dfs[name] = df1
df = pd.concat(dfs.values(), axis=1)
df.columns = dfs.keys()

# EVENT DATA
fedMoves = [
    ["2023-07-26", "+0.25%", "5.25%"],
    ["2023-05-03", "+0.25%", "5.00%"],
    ["2023-03-22", "+0.25%", "4.75%"],
    ["2023-02-01", "+0.25%", "4.50%"],
    ["2022-12-15", "+0.50%", "4.25%"],
    ["2022-11-02", "+0.75%", "3.75%"],
    ["2022-09-21", "+0.75%", "3.00%"],
    ["2022-07-27", "+0.75%", "2.25%"],
    ["2022-06-15", "+0.75%", "1.50%"],
    ["2022-05-04", "+0.50%", "0.75%"],
    ["2022-03-17", "+0.25%", "0.25%"],
    ["2020-03-16", "-1.00%", "0.00%"],
    ["2020-03-03", "-0.50%", "1.00%"],
    ["2019-10-31", "-0.25%", "1.50%"],
    ["2019-09-19", "-0.25%", "1.75%"],
    ["2019-08-01", "-0.25%", "2.00%"],
    ["2018-12-20", "+0.25%", "2.25%"],
    ["2018-09-27", "+0.25%", "2.00%"],
    ["2018-06-14", "+0.25%", "1.75%"],
    ["2018-03-22", "+0.25%", "1.50%"],
    ["2017-12-14", "+0.25%", "1.25%"],
    ["2017-06-15", "+0.25%", "1.00%"],
    ["2017-03-16", "+0.25%", "0.75%"],
    ["2016-12-15", "+0.25%", "0.50%"],
    ["2015-12-16", "+0.25%", "0.25%"],
    ["2008-12-16", "-1.00%", "0.00%"],
    ["2008-10-29", "-0.50%", "1.00%"],
    ["2008-10-08", "-0.50%", "1.50%"],
    ["2008-04-30", "-0.25%", "2.00%"],
    ["2008-03-18", "-0.75%", "2.25%"],
    ["2008-01-30", "-0.50%", "3.00%"],
    ["2008-01-22", "-0.75%", "3.50%"],
    ["2007-12-11", "-0.25%", "4.25%"],
    ["2007-10-31", "-0.25%", "4.50%"],
    ["2007-09-18", "-0.50%", "4.75%"],
    ["2006-06-29", "+0.25%", "5.25%"],
    ["2006-05-10", "+0.25%", "5.00%"],
    ["2006-03-28", "+0.25%", "4.75%"],
    ["2006-01-31", "+0.25%", "4.50%"],
    ["2005-12-13", "+0.25%", "4.25%"],
    ["2005-11-01", "+0.25%", "4.00%"],
    ["2005-09-20", "+0.25%", "3.75%"],
    ["2005-08-09", "+0.25%", "3.50%"],
    ["2005-06-30", "+0.25%", "3.25%"],
    ["2005-05-03", "+0.25%", "3.00%"],
    ["2005-03-22", "+0.25%", "2.75%"],
    ["2005-02-02", "+0.25%", "2.50%"],
    ["2004-12-14", "+0.25%", "2.25%"],
    ["2004-11-10", "+0.25%", "2.00%"],
    ["2004-09-21", "+0.25%", "1.75%"],
    ["2004-08-10", "+0.25%", "1.50%"],
    ["2004-06-30", "+0.25%", "1.25%"],
    ["2003-06-25", "-0.25%", "1.00%"],
    ["2002-11-06", "-0.50%", "1.25%"],
    ["2001-12-11", "-0.25%", "1.75%"],
    ["2001-11-06", "-0.50%", "2.00%"],
    ["2001-10-02", "-0.50%", "2.50%"],
    ["2001-09-17", "-0.50%", "3.00%"],
    ["2001-08-21", "-0.25%", "3.50%"],
    ["2001-06-27", "-0.25%", "3.75%"],
    ["2001-05-15", "-0.50%", "4.00%"],
    ["2001-04-18", "-0.50%", "4.50%"],
    ["2001-03-20", "-0.50%", "5.00%"],
    ["2001-01-31", "-0.50%", "5.50%"],
    ["2001-01-03", "-0.50%", "6.00%"],
    ["2000-05-16", "+0.50%", "6.50%"],
    ["2000-03-21", "+0.25%", "6.00%"],
    ["2000-02-02", "+0.25%", "5.75%"],
    ["1999-11-16", "+0.25%", "5.50%"],
    ["1999-08-24", "+0.25%", "5.25%"],
    ["1999-06-30", "+0.25%", "5.00%"],
    ["1998-11-17", "-0.25%", "4.75%"],
    ["1998-10-15", "-0.25%", "5.00%"],
    ["1998-09-29", "-0.25%", "5.25%"],
    ["1997-03-25", "+0.25%", "5.50%"],
    ["1996-01-31", "-0.25%", "5.25%"],
    ["1995-12-19", "-0.25%", "5.50%"],
    ["1995-07-06", "-0.25%", "5.75%"],
    ["1995-02-01", "+0.50%", "6.00%"],
    ["1994-11-15", "+0.75%", "5.50%"],
    ["1994-08-16", "+0.50%", "4.75%"],
    ["1994-05-17", "+0.50%", "4.25%"],
    ["1994-04-18", "+0.25%", "3.75%"],
    ["1994-03-22", "+0.25%", "3.50%"],
    ["1994-02-04", "+0.25%", "3.25%"],
    ["1992-09-04", "-0.25%", "3.00%"],
    ["1992-07-02", "-0.50%", "3.25%"],
    ["1992-04-09", "-0.25%", "3.75%"],
    ["1991-12-20", "-0.50%", "4.00%"],
    ["1991-12-06", "-0.25%", "4.50%"],
    ["1991-11-06", "-0.25%", "4.75%"],
    ["1991-10-31", "-0.25%", "5.00%"],
    ["1991-09-13", "-0.25%", "5.25%"],
    ["1991-08-06", "-0.25%", "5.50%"],
    ["1991-04-30", "-0.25%", "5.75%"],
    ["1991-03-08", "-0.25%", "6.00%"],
    ["1991-02-01", "-0.50%", "6.25%"],
    ["1991-01-09", "-0.25%", "6.75%"],
    ["1990-12-18", "-0.25%", "7.00%"],
    ["1990-12-07", "-0.25%", "7.25%"],
    ["1990-11-13", "-0.25%", "7.50%"],
    ["1990-10-29", "-0.25%", "7.75%"],
    ["1990-07-13", "-0.25%", "8.00%"]]
presidentialElections = [
    ["2020-11-03", "Joe Biden", "Democrat"],
    ["2016-11-08", "Donald J. Trump", "Republican"],
    ["2012-11-06", "Barack Obama", "Democrat"],
    ["2008-11-04", "Barack Obama", "Democrat"],
    ["2004-11-02", "George W. Bush", "Republican"],
    ["2000-11-07", "George W. Bush", "Republican"],
    ["1996-11-05", "Bill Clinton", "Democrat"],
    ["1992-11-03", "Bill Clinton", "Democrat"],
    ["1988-11-08", "George H.W. Bush", "Republican"],
    ["1984-11-06", "Ronald Reagan", "Republican"],
    ["1980-11-04", "Ronald Reagan", "Republican"],
    ["1976-11-02", "Jimmy Carter", "Democrat"],
    ["1972-11-07", "Richard Nixon", "Republican"]]

df2 = pd.DataFrame(fedMoves, columns=["Date", "fedChange", "fedPolicyRate"])
df2["Date"] = pd.to_datetime(df2["Date"])
df2.set_index("Date", inplace=True)
df2["fedAction"] = df2["fedChange"].apply(lambda x: "Hike" if "+" in x else "Cut")
df2["fedPolicyRate"] = df2["fedPolicyRate"].str.rstrip('%').astype(float)
df2['fedChange'] = df2['fedChange'].str.rstrip('%').astype(float)
df2['fedEventDate'] = df2.index.strftime('%Y-%m-%d') + ' ' + df2['fedAction']

df3 = pd.DataFrame(presidentialElections, columns=["Date", "President", "Party"])
df3["Date"] = pd.to_datetime(df3["Date"])
df3.set_index("Date", inplace=True)
df3['electionEventDate'] = df3.index.strftime('%Y-%m-%d') + ' Elections'

### CONCAT
df = df.combine_first(df2)
df = df.combine_first(df3)
df = df.asfreq('B').ffill()

# PERFORMANCE AROUND SPECIFIED DATES
def calculateIntervalPerformance(df, column, selectedDate, performanceRange):
    dateIndex = df.index.get_loc(pd.to_datetime(selectedDate))
    startIdx = max(0, dateIndex - performanceRange)
    endIdx = min(len(df) - 1, dateIndex + performanceRange)
    backwardPercentReturn = (df[column].iloc[dateIndex] - df[column].iloc[startIdx]) / max(1e-6, df[column].iloc[startIdx]) * 100
    forwardPercentReturn = (df[column].iloc[endIdx] - df[column].iloc[dateIndex]) / max(1e-6, df[column].iloc[dateIndex]) * 100
    return backwardPercentReturn, forwardPercentReturn

# DASHBOARD
purpleColor, beigeColor, blueColor, greyColor, blackColor = '#8B008B', '#F5F5DC', '#1E90FF', '#808080', 'black'
line_colors = ['#8B008B', '#1E90FF', '#FFA500', '#00FF00', '#FF0000']

app = dash.Dash(__name__)
app.layout = html.Div([
    html.Div([
        dcc.Dropdown(id='columnDropdown',
                     options=[{'label': col, 'value': col} for col in df.columns],
                     multi=True, value=[df.columns[0]],
                     style={'color': purpleColor}),
        dcc.Dropdown(id='columnDropdown2',
                     options=[{'label': col, 'value': col} for col in df2.columns],
                     multi=True, value=[df2.columns[0]],
                     style={'color': purpleColor}),
        dcc.Dropdown(id='dateActionDropdown',
                     options=[{'label': da, 'value': da} for da in df3['electionEventDate']],
                     multi=True,
                     style={'color': purpleColor}),
        dcc.Input(id='performanceRange', type='number', value=10, step=1,
                  style={'color': purpleColor}),
        dcc.Graph(id='timeSeriesChart')],
        style={'width': '80%', 'padding': '10px', 'margin': 'auto'}),
    html.Div([
        dcc.Graph(id='timeSeriesChart2', style={'height': '300px'},
                  config={'displayModeBar': False})],
        style={'width': '80%', 'padding': '5px', 'margin': 'auto'}),
    html.Div([dash_table.DataTable(id='returnsTable',
                                   columns=[],
                                   data=[],
                                   sort_action='native',
                                   sort_by=[{'column_id': 'Date fedAction', 'direction': 'asc'}],
                                   style_cell={'padding': '5px', 'color': blackColor, 'text-align': 'center',
                                               'font-weight': 'bold'},
                                   style_table={'margin': 'auto', 'width': '80%'},
                                   style_header={'text-align': 'center', 'font-weight': 'bold',
                                                 'background-color': greyColor, 'color': 'white'},
                                   style_data={'height': 'auto', 'background-color': beigeColor}),
               ], style={'width': '90%', 'padding': '5px'})],
    style={'backgroundColor': beigeColor, 'fontFamily': 'Arial', 'color': purpleColor})
@app.callback(
    [Output('timeSeriesChart', 'figure'), Output('timeSeriesChart2', 'figure'),
     Output('returnsTable', 'columns'), Output('returnsTable', 'data')],
    [Input('columnDropdown', 'value'), Input('dateActionDropdown', 'value'),
     Input('performanceRange', 'value'), Input('columnDropdown2', 'value')])
def updateGraphAndTable(selectedColumns, selectedDateActions, performanceRange, selectedColumns2):
    tableData = []
    selectedDates = [da.split()[0] for da in selectedDateActions] if selectedDateActions else []
    for i, col in enumerate(selectedColumns or []):
        line_color = line_colors[i % len(line_colors)]
        for da in selectedDates:
            backwardPercentReturn, forwardPercentReturn = calculateIntervalPerformance(df, col, da, performanceRange)
            tableData.append({
                'Column': col,
                'Date fedAction': da,
                f'Prior {performanceRange} Day Return (%)': f"{backwardPercentReturn:.2f}%",
                f'Following {performanceRange} Day Return (%)': f"{forwardPercentReturn:.2f}%"})

    returnsTableColumns = [
        {'name': 'Index', 'id': 'Column'},
        {'name': 'Date - Fed Policy Change', 'id': 'Date fedAction'},
        {'name': f'Prior {performanceRange} Day Return (%)', 'id': f'Prior {performanceRange} Day Return (%)'},
        {'name': f'Following {performanceRange} Day Return (%)', 'id': f'Following {performanceRange} Day Return (%)'}]

    fig = make_subplots(specs=[[{"secondary_y": True}]])
    for i, col in enumerate(selectedColumns or []):
        line_color = line_colors[i % len(line_colors)]  # Use a different color for each selected column
        fig.add_trace(go.Scatter(x=df.index, y=df[col], mode='lines', name=col, line=dict(color=line_color)),
                      secondary_y=(i % 2 == 1))

    for da in selectedDates:
        if pd.to_datetime(da) in df.index:
            selectedDate = pd.to_datetime(da)
            selectedDate_value = df3.loc[df3['electionEventDate'].str.contains(selectedDate.strftime('%Y-%m-%d'))][
                'electionEventDate'].values[0]
            fig.add_trace(go.Scatter(x=[selectedDate], y=[df[selectedColumns[0]].loc[selectedDate]],
                                     mode='markers+text',
                                     marker=dict(size=12, color=blueColor, opacity=0.85),
                                     text=[selectedDate_value],
                                     textfont=dict(size=12, color=blackColor, family='Arial Bold'),
                                     showlegend=False, textposition='bottom center'))
    fig.update_layout(plot_bgcolor='white', paper_bgcolor=beigeColor, font=dict(family='Arial', size=10, color=blackColor))
    fig2 = make_subplots(specs=[[{"secondary_y": True}]])
    for i, col in enumerate(selectedColumns2 or []):
        fig2.add_trace(go.Scatter(x=df2.index, y=df2[col], mode='lines', name=col, line=dict(color=purpleColor)),
                       secondary_y=(i % 2 == 1))
    fig2.update_xaxes(range=[df.index[0], df.index[-1]])
    fig2.update_layout(plot_bgcolor='white', paper_bgcolor=beigeColor, font=dict(family='Arial', size=10, color=blackColor))
    return fig, fig2, returnsTableColumns, tableData

if __name__ == '__main__':
    app.run_server(debug=True)