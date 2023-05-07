#stats import
import yfinance as yf
import numpy as np
import scipy.optimize as spop
import statsmodels.api as sm
import pandas as pd
from datetime import date, timedelta
import plotly.graph_objs as go
from plotly.offline import plot

def execute_trade(pair, raw_data):
    window = 21
    #specifying maximum KPSS statistic (95% critical value)
    KPSS_max = 0.463
    #specifying the KPSS test (one-parameter unbiased or two-parameter)
    unbiased = 1
    #strategy parameters - trading fee, optimal entry (divergence), and stop-loss
    fee = 0.0001
    entry = 0.02
    stop_loss = -0.05
    #initially start in cash
    signal = 0
    current_return = 0
    position0 = 0
    position1 = 0
    #initialising arrays
    gross_returns = np.array([])
    signals = np.array([])
    KPSS_stats = np.array([])
    for t in range(window, len(raw_data) - 1):
        old_signal = signal
        old_position0 = position0
        old_position1 = position1
        # specifying subsample
        data = raw_data[t - window:t]
        # stock 2 = a + b*stock 1
        # OLS parametsrs as starting values
        reg = sm.OLS(np.array(data[pair[1]]), sm.add_constant(np.array(data[pair[0]])))
        res = reg.fit()
        a0 = res.params[0]
        b0 = res.params[1]
        if unbiased == 1:
            # defining the KPSS function(unbiased one-parameter forecast)
            def KPSS(b):
                a = np.average(data[pair[1]] - b*data[pair[0]])
                resid = np.array(data[pair[1]] - (a + b*data[pair[0]]))
                cum_resid = np.cumsum(resid)
                st_error = (np.sum(resid**2)/(len(resid)-2))**(1/2)
                KPSS = np.sum(cum_resid**2)/(len(resid)**2*st_error**2)
                return KPSS
            #minimising the KPSS function (maximising the stationarity)
            res = spop.minimize(KPSS, b0, method='Nelder-Mead')
            KPSS_opt = res.fun
            #retrieving optimal parameters
            b_opt = float(res.x)
            a_opt = np.average(data[pair[1]] - b_opt*data[pair[0]]) 
        else:
            #defining the KPSS function (two-parameter)
            def KPSS2(kpss_params):
                a = kpss_params[0]
                b = kpss_params[1]
                resid = np.array(data[pair[1]] - (a + b*data[pair[0]]))
                cum_resid = np.cumsum(resid)
                st_error = (np.sum(resid**2)/(len(resid)-2))**(1/2)
                KPSS = np.sum(cum_resid**2)/(len(resid)**2*st_error**2)
                return KPSS
            #minimising the KPSS function (maximising the stationarity)
            res = spop.minimize(KPSS2, [a0, b0], method='Nelder-Mead')
            #retrieving optimal parameters
            KPSS_opt = res.fun
            a_opt = res.x[0]
            b_opt = res.x[1]
        #simulate trading
        #first check whether stop-loss is violated
        if current_return < stop_loss:
            signal = 0
            #print('stop-loss triggered')
        #if we are already in position, check whether the equilibrium is restored, continue in position if not
        elif np.sign(raw_data[pair[1]][t] - (a_opt + b_opt*raw_data[pair[0]][t])) == old_signal:
            singal = old_signal
        else:
        #only trade if the pair is cointegrated
            if KPSS_opt > KPSS_max:
                signal = 0
            #only trade if there are large enough profit opportunities (optimal entry)
            elif abs(raw_data[pair[1]][t]/(a_opt + b_opt*raw_data[pair[0]][t])-1) < entry:
                signal = 0
            else:
                signal = np.sign(raw_data[pair[1]][t] - (a_opt + b_opt*raw_data[pair[0]][t]))
            #calculate strategy returns with beta loading
        
        position0 = signal
        position1 = -signal
        #calculating returns
        gross = position0*(raw_data[pair[0]][t+1]/raw_data[pair[0]][t] - 1) + position1*(raw_data[pair[1]][t+1]/raw_data[pair[1]][t] - 1)
        # net = gross - fee*(abs(position0 - old_position0) + abs(position1 - old_position1))
        if signal == old_signal:
            current_return = (1+current_return)*(1+gross)-1
        else:
            current_return = gross
        #populating arrays
        KPSS_stats = np.append(KPSS_stats, KPSS_opt)
        signals = np.append(signals, signal)
        gross_returns = np.append(gross_returns, gross)
    # net_returns = np.append(net_returns, net)
    #building the output dataframe
    output = pd.DataFrame()
    output['KPSS'] = KPSS_stats
    output['signal'] = signals
    output['gross'] = gross_returns
    #output['net'] = net_returns
    return output

def execute_trade_for_time(transaction):
    if not is_long_transaction(transaction):
        return None

    stocks = transaction.get_stock_pair()
    stock1 = stocks.stock1
    stock2 = stocks.stock2
    data = yf.download([stock1, stock2], end=transaction.end_time, start = transaction.start_time, repair=True)
    data.dropna(inplace=True)
    output = execute_trade((stock1, stock2), data['Close'])
    output['time'] = pd.Series(data.index)
    return output


def is_long_transaction(transaction):
    start_time = transaction.start_time
    end_time = transaction.end_time
    return (end_time - start_time) > timedelta(days=21)


def generate_graphs(data):
    plots = []
    for pair in data.keys():
        output = data[pair]
        stock1 = pair.split('_')[0]
        stock2 = pair.split('_')[1]
        temp = {
            'date': output['time'].values,
            'gross': np.append(1,np.cumprod(1+output['gross'])),
            'kpss': output['KPSS']
        }
        df = pd.DataFrame.from_dict(temp, orient='index')
        df = df.transpose()
        df['date'] = pd.to_datetime(df['date'])

        trace1 = go.Scatter(x=df['date'], y=df['gross'], name='Cumulative Gross Revenue', mode='lines', line_color="#5255c9")

        # Create a bar trace for the indicator
        trace2 = go.Bar(x=df['date'], y=df['kpss'], marker_color="#f3c22c", name='Indicator Strength')
        layout = go.Layout(
            title = f'Performance of {stock1}, {stock2}',
            xaxis = dict(title='Date'),
            yaxis = dict(title='Times')
        )
        # Create a figure with both traces
        fig = go.Figure([trace1, trace2], layout=layout)
        #fig = px.line(df, x='date', y=['gross', 'kpss'], title = f"Stats For Pair {stock1}, {stock2}")
        #fig.update_xaxes(title_text='Date')
        #fig.update_yaxes(title_text='')
        plots.append(plot(fig, output_type="div"))
    return plots