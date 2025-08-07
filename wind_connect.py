import marimo

__generated_with = "0.14.10"
app = marimo.App(width="medium")


@app.cell
def _():
    import marimo as mo
    import numpy as np
    import itertools
    import seaborn as sb
    import matplotlib.pyplot as plt
    import pandas as pd
    import scipy.stats as scistat
    from collections import defaultdict
    from sklearn.ensemble import RandomForestRegressor
    return RandomForestRegressor, defaultdict, itertools, mo, np, pd, plt, sb


@app.cell
def _():
    mwhr_sold = 1000*.4*8760
    # https://css.umich.edu/publications/factsheets/energy/wind-energy-factsheet
    # capacity factor from .09 to .53, averages .37, call it .4 now
    # 
    # all include 30% contingency
    # AC
    # missouri 345 kv, 5.5 to 6.4M per mile, page 39 MISO guide
    #  per mile if double circuit
    # AC substation 20 to 25M
    # 
    # HVDC bipole 400kv at 2.3 to 3.3M per mile
    # 296 per foot of trenching
    # converter is 461M per end
    # 
    # 1800 MVA
    def ac_costs(rand = False,  miles = 31):
        # in millions
        return 20 + miles*5.5
    def dc_costs(rand = False, miles = 31):
        # in millions
        return 461*2 + miles*2.3 + miles*296*(10**-6)*5280 # trenching
  

    return ac_costs, dc_costs, mwhr_sold


@app.cell
def _(ac_costs, dc_costs, np, plt):
    def dist_switch():
        fig, ax = plt.subplots()
        lengths = np.arange(20,700,15)
        ac = ac_costs(miles = lengths)
        dc = dc_costs(miles = lengths)
        ax.plot(lengths, ac, label = 'AC over')
        ax.plot(lengths, dc, label = 'DC under')
        ax2 = ax.twinx()
        ax2.scatter(lengths, dc/ac, color = 'green', label = 'ratio')
        ax2.set_ylabel('ratio of dc:ac costs')
        ax.set_xlabel('distance in miles')
        ax.set_ylabel('cost in millions USD')
        ax.set_title('transmission costs: wire, substations and converters')
        fig.legend()
    return (dist_switch,)


@app.cell
def _(dist_switch, plt):
    dist_switch()
    plt.show()
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md(
        """
    Assume a 1000MW wind farm in the Midwest with a capacity factor of 0.4 that is 50 km from a load (or a grid connection) that will be completed and ready to export power in four years.

    Assume that the operator could either build an overhead HVAC line or a buried HVDC cable at the costs/km that you find as best estimates from the literature.

    To simplify things, assume that once construction begins, yes, there are no complications the time to construct either line is 4 years.

    Assume that construction of the HVDC cable can start immediately and the probability of successfully completing the line is p=1.

    Assume that because of a variety of legal and other issues that could arise, it will not be possible to start construction of the overhead AC line for D = [1, .  3; 5; 10] years and that after waiting that long and starting construction, the probability of successfully completing the overhead line is p = [1; 0.8; 0.5]. At least for starters assume that p does not vary with D

    Assume that the developer can secure a 15 year firm contract to sell the power at C=$X/MWhr, where C is [60, 80, 100]

    So, the initial basic problem involves 3 uncertain parameters: D, p and C.

    Report the combinations of the values of those three parameters (if any) for which, in terms of expected value, the operator should choose the HVDC cable. 

    = = = 
    As it’s framed here, this problem is pretty simple. Once you have performed this analysis, then you should develop and suggest a variety of ways to elaborate the problem and make it more interesting and work with us to revise you Part A proposal appropriately.
    However, ignore all of these complications for now.
    """
    )
    return


@app.cell
def _(np, plt):
    def time_line(delay = 7, build_time = 3, cap_ex = .5, build_cost = .2,
                  profit = .1, T = 20, rate = .07, loan_rate = .1, p_success = 1,
                  payments = 10, delay_cost = .1, delay_loan = True):
        '''
        we take out a loan at the beginning (or after delay), start paying 
        for construction after the delay
        and receive profits after the construction's build time
        '''
        delay, build_time, T, payments = (
            int(delay), int(build_time), int(T), int(payments) )
        loan_time = delay if delay_loan else 0

        seqs = {}
        seqs['loan_pay'] = np.zeros(T)
        seqs['loan_pay'][1+loan_time:1+loan_time+payments] = -cap_ex * (
            loan_rate*(1+loan_rate)**payments / ( (1+loan_rate)**payments-1) )
        seqs['cap_loan'] = np.zeros(T)
        seqs['cap_loan'][loan_time] = cap_ex
        seqs['build_cost'] = np.zeros(T)
        seqs['profit'] = np.zeros(T)
        seqs['delay_cost'] = np.zeros(T)
        if np.random.rand() <p_success:
            seqs['profit'][delay+build_time:] = profit
            seqs['build_cost'][delay:delay+build_time] = -build_cost 
            seqs['delay_cost'][:delay+build_time] = -delay_cost
        else:             
            seqs['profit'][delay+build_time:] = 0
            seqs['build_cost'][delay:delay+build_time] = 0
            seqs['delay_cost'][:] = -delay_cost

        seqs['totals'] = (seqs['loan_pay']+seqs['cap_loan']+
                          seqs['build_cost']+seqs['profit']+
                         seqs['delay_cost'])
        seqs['discounts'] = (1+rate)**-np.arange(1,T+1)
        seqs['NPV'] = (seqs['totals'] * seqs['discounts']).sum()
        return seqs

    def plot_seqs(seqs, title = ''):
        marks = '*o^.3'
        for i, key in enumerate(
            'profit build_cost cap_loan loan_pay delay_cost'.split(' ')):
            plt.plot(seqs[key], marker = marks[i], label =key)
        plt.legend()
        plt.title(f'NPV = {seqs['NPV']:.3f} '+title)
        plt.xlabel('years')
        plt.ylabel('cost (capex of AC is 1)')
    return plot_seqs, time_line


@app.cell
def _(plot_seqs, plt, time_line):
    plot_seqs(time_line(delay = 10, build_time = 4, cap_ex = .5, build_cost = .2,
                  profit = .1, T = 19, rate = .07, loan_rate = .1,
                  payments = 10, delay_cost = 0, delay_loan = True))
    plt.show()
    return


@app.cell
def _(plot_seqs, plt, time_line):
    plot_seqs(time_line(delay = 4, build_time = 4, cap_ex = .5, build_cost = .2,
                  profit = .1, T = 24, rate = .07, loan_rate = .1,
                  payments = 10, delay_cost = 0.1, delay_loan = True,
                        p_success = .1))
    plt.show()
    return


@app.cell
def _(ac_costs, dc_costs, defaultdict, itertools, mwhr_sold, np, time_line):
    run_records = defaultdict(list)
    for d in [30,120, 360]:
        AC_CAP = ac_costs(miles = d)
        DC_CAP = dc_costs(miles = d)
        revenues = np.array([0,60,80,100])
        for delay in [1,3,5,10]:
            # for build_time in [4]:
            # for cap_ex in [1, DC_CAP/AC_CAP]:
            for profit_USD, delay_cost_USD in itertools.product(
                                                revenues,revenues):
                profit = profit_USD*mwhr_sold/(AC_CAP*10**6)
                delay_cost = delay_cost_USD*mwhr_sold/(AC_CAP*10**6)
                for prob in [1, .8, .5]:
                    for _ in range(40):
                        payments = 15
                        build_time = 4
                        rate, loan_rate = .07, .10
                        DCnpv = time_line(delay = 0, build_time = build_time, 
        cap_ex =DC_CAP/AC_CAP, build_cost = DC_CAP/AC_CAP/build_time, 
        profit = profit, T = 30, rate = rate, loan_rate = loan_rate, 
        payments = payments, delay_cost = delay_cost, p_success = 1)['NPV']
                        ACnpv = time_line(delay = delay, build_time = build_time, 
        cap_ex = 1, build_cost = 1/build_time, profit = profit, 
        T = 30, rate = rate, loan_rate = loan_rate, payments = payments, 
        delay_cost = delay_cost, p_success = prob)['NPV']
                        run_records['delay_cost']+=[delay_cost]
                        run_records['profit'] += [profit]
                        run_records['delay_cost_USD']+=[delay_cost_USD]
                        run_records['profit_USD'] += [profit_USD]
                        run_records['npv_DC'] += [DCnpv/AC_CAP]
                        run_records['npv_AC'] += [ACnpv/AC_CAP]
                        run_records['npv_diff']+= [(DCnpv - ACnpv)/AC_CAP]
                        run_records['AC_delay'] += [delay]
                        # run_records['build_time'] += [build_time]
                        run_records['DC_cost'] += [DC_CAP/AC_CAP]
                        # run_records['payments'] += [payments]
                        run_records['distance'] += [d]
                        run_records['AC_prob'] += [prob]
                    
    return (run_records,)


@app.cell
def _(RandomForestRegressor, pd, run_records):
    df = pd.DataFrame(run_records)
    X = df[[ 'delay_cost', 'AC_delay', 'DC_cost', 'profit', 'AC_prob', 'distance']]
    y = df['npv_diff']

    correlations = df.corr(
        numeric_only=True)['npv_diff'].sort_values(ascending=False)
    print('Correlation coefficients: \n',correlations)

    model = RandomForestRegressor(n_estimators=100, random_state=0)
    model.fit(X, y)

    importances = pd.Series(model.feature_importances_, index=X.columns)
    importances = importances.sort_values(ascending=False)
    print('\n\nRandom forest importances: \n',importances)
    return (df,)


@app.cell
def _(df):
    df
    return


@app.cell
def _(df, plt):
    for del_val in df['delay_cost_USD'].unique():
        plt.subplots(3,1, figsize=(6,6))
        for i,prob_val in enumerate(df['AC_prob'].unique()):
            plt.subplot(3,1,i+1)
            df_fix = df[
                (df['distance']==120)&
                (df['delay_cost_USD']==del_val)  &
                (df['AC_prob']==prob_val) 
            ]
            for col in [ 'profit_USD']:
                for delay_val in df_fix['AC_delay'].unique():
                    this_df = df_fix[df_fix['AC_delay']==delay_val]
                    plt.scatter(this_df[col], y=this_df['npv_diff'],
                                label=f'delay={delay_val}', s =15)
                plt.axhline(0, dashes = (2,4), color = 'black')
                plt.title(
        f" d = 120 miles, delay_cost = {del_val}, prob(AC) = {prob_val} ")
                plt.xlabel(col)
                plt.ylabel('NPV Diff')
                if i==0:
                    plt.legend()
        plt.tight_layout()
        plt.show()
    return (df_fix,)


@app.cell
def _(df, df_fix, plt, sb):
    my_df = df[
        (df['distance']==30)&
        (df['delay_cost_USD']==0)
    ]
    for col in [ 'DC_cost', 'profit_USD', 'AC_delay', 'AC_prob']:
        sb.scatterplot(data=df_fix, x=col, y='npv_diff')
        plt.title(f"NPV Diff vs {col}, d = 30 miles, delay_cost = 0 ")
        plt.show()
    return


if __name__ == "__main__":
    app.run()
