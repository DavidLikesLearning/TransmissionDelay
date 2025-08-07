import marimo

__generated_with = "0.14.10"
app = marimo.App(width="medium")


@app.cell
def _():
    import marimo as mo
    import numpy as np
    import itertools
    import seaborn as sns
    import matplotlib.pyplot as plt
    import pandas as pd
    import scipy.stats as scistat
    from collections import defaultdict
    import seaborn as sb
    from collections import defaultdict
    return defaultdict, itertools, mo, np, pd, plt, sns


@app.cell
def _(np):
    def sample_rayleigh(center, size=1):
        """
        Samples from a Rayleigh distribution with a controlled center
        """
        sigma= center / np.sqrt(np.pi / 2)
        samples = np.random.rayleigh(scale=sigma, size=size)
        return samples

    def sample_normal(center, std = 1, size=1):
        """
        Samples from a Normal distribution with a controlled center
        """
        samples = np.random.randn(size)*std + center
        return samples
    return


@app.cell
def _(np, plt):
    def time_line(delay = 7, build_time = 3, cap_ex = .5, build_cost = .2,
                  profit = .1, T = 20, rate = .07, loan_rate = .1,
                  payments = 10, delay_cost = .1, delay_loan = False):
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
        if delay < 15:     # # # 14 year delay or lesser, project happens # # #
            seqs['profit'][delay+build_time:] = profit
            seqs['build_cost'][delay:delay+build_time] = -build_cost 
            seqs['delay_cost'][:delay+build_time] = -delay_cost
        else:              # # # 15 year delay or greater, project doesn't happen # # #
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
        for i, key in enumerate('profit build_cost cap_loan loan_pay delay_cost'.split(' ')):
            plt.plot(seqs[key], marker = marks[i], label =key)
        plt.legend()
        plt.title(f'NPV = {seqs['NPV']:.3f} '+title)
        plt.xlabel('years')
        plt.ylabel('cost (capex of AC is 1)')


    return plot_seqs, time_line


@app.cell
def _():
    # constants = {'delay': 3, 'build_time': 3, 'cap_ex':.5, 
    #             'profit': .1, 'T': 40, 'payments': 20}
    # seq_var = mo.ui.dropdown(constants.keys(), value = 'delay')
    # num_low = mo.ui.number(-100, 100, .1, label='lower bound', value = 2)
    # num_hi = mo.ui.number(-100, 100, .1, label='upper bound', value = 14)
    # mo.vstack([seq_var, num_low, num_hi])
    return


@app.cell
def _():
    # lo, hi = num_low.value, num_hi.value
    # def show_range(lo,hi, constants, delay_loan):
    #     plt.figure(figsize=(4,10))
    #     for k in range(1,5):
    #         constants[seq_var.value] = lo + (hi-lo)*(k-1)/3
    #         constants['build_cost'] = (.9*constants['cap_ex']/
    #                                    constants['build_time'])
    #         plt.subplot(4,1,k)
    #         seq = time_line(delay = constants['delay'], 
    #         build_time = constants['build_time'], cap_ex = constants['cap_ex'], 
    #         build_cost = constants['build_cost'], profit = constants['profit'], 
    #         T = constants['T'], rate = .07, loan_rate = .1, payments = 
    #         constants['payments'], delay_loan = delay_loan)

    #         plot_seqs(seq, 
    #             title = f'{seq_var.value} =  {constants[seq_var.value]}')

    #     plt.tight_layout()
    #     plt.show()

    return


@app.cell
def _(defaultdict, itertools, time_line):
    run_records = defaultdict(list)
    for delay in [2,5,8,11,14,15,17]:
        for build_time in [1,3,5,7]:
            for cap_ex in [1,2.2,3.4, 4.6]:
                for profit in [.01, .04, .16, .32,.64, 1.28]:
                    for payments in [15, 30, 40]:
                        for delay_cost in [.03, .06, .12, .24, .72, 1.28]:
                            for rate, loan_rate in itertools.product(
                                [.01, .03, .09, .12],[.01, .03, .09, .12]):
                                delay_loan = True
                                npv = time_line(delay = delay, 
        build_time = build_time, cap_ex = cap_ex, build_cost = .9*cap_ex/build_time, 
        profit = profit, T = 70, rate = rate, loan_rate = loan_rate, payments = payments, 
        delay_cost = delay_cost, delay_loan = False)['NPV']
                                run_records['rate']+=[rate]
                                run_records['loan_rate']+=[loan_rate]
                                run_records['delay_cost']+=[delay_cost]
                                run_records['npv']+= [npv]
                                run_records['delay'] += [delay]
                                run_records['build_time'] += [build_time]
                                run_records['cap_ex'] += [cap_ex]
                                run_records['profit'] += [profit]
                                run_records['payments'] += [payments]

    # rnd_records = defaultdict(list)
    # for _ in range(2000):
    #     delay = np.random.randint(2,17)
    #     build_time = np.random.randint(1,12)
    #     cap_ex = np.random.rand()*4+1
    #     profit = 5*10**(np.random.rand()*2.1-3)
    #     payments = np.random.randint(15,40)
    #     delay_cost = 1*10**(np.random.rand()*3.1-3)
    #     rate = 5*10**(np.random.rand()*2-3)
    #     loan_rate = 5*10**(np.random.rand()*2-3)
    #     delay_loan = True
    #     npv = time_line(delay = delay, 
    #         build_time = build_time, cap_ex = cap_ex, 
    #         build_cost = .9*cap_ex/build_time, profit = profit, T = 70,
    #         rate = rate, loan_rate = loan_rate, payments = payments, 
    #         delay_cost = delay_cost, delay_loan = False)['NPV']
    #     rnd_records['rate']+=[rate]
    #     rnd_records['loan_rate']+=[loan_rate]
    #     rnd_records['delay_cost']+=[delay_cost]
    #     rnd_records['npv']+= [npv]
    #     rnd_records['delay'] += [delay]
    #     rnd_records['build_time'] += [build_time]
    #     rnd_records['cap_ex'] += [cap_ex]
    #     rnd_records['profit'] += [profit]
    #     rnd_records['payments'] += [payments]                            
    return (run_records,)


@app.cell
def _(plot_seqs, plt, time_line):
    plot_seqs(time_line(
        delay = 5, build_time = 3, cap_ex = 2, 
            build_cost = .6, profit = .2, T = 60,
            rate = .07, loan_rate = .05, payments = 40, 
            delay_cost = .3, delay_loan = True
    ))
    plt.show()
    plot_seqs(time_line(
        delay = 15,  build_time = 3, cap_ex = 2, 
            build_cost = .6, profit = .2, T = 60,
            rate = .07, loan_rate = .05, payments = 40, 
            delay_cost = .3, delay_loan = True
    ))
    plt.show()
    return


@app.cell
def _(pd, plt, run_records, sns):
    records = pd.DataFrame(run_records)
    for col in ['delay', 'build_time', 'cap_ex', 'profit', 'payments', 'delay_cost', 'rate', 'loan_rate']:
        sns.scatterplot(data=records, x=col, y='npv')
        plt.title(f"NPV vs {col}")
        plt.show()
    return (records,)


@app.cell
def _(pd, records):
    from sklearn.ensemble import RandomForestRegressor

    X = records[['rate', 'loan_rate', 'delay_cost', 'delay', 'build_time', 'cap_ex', 'profit', 'payments']]
    y = records['npv']

    model = RandomForestRegressor(n_estimators=100, random_state=0)
    model.fit(X, y)

    importances = pd.Series(model.feature_importances_, index=X.columns)
    importances = importances.sort_values(ascending=False)
    print(importances)


    return


@app.cell
def _(records):
    correlations = records.corr(numeric_only=True)['npv'].sort_values(ascending=False)
    print(correlations)
    return


@app.cell
def _(records):
    records['profit'].unique()
    return


@app.cell
def _(records):
    small_df = records[
        (records['loan_rate'] == 0.12) & 
        (records['payments'] == 30) & 
        (records['rate'] == 0.09) &
    #    (records['build_time'] == 3) &
        (records['delay'] == 5)
    ]
    return (small_df,)


@app.cell
def _(records):
    records.keys()
    return


@app.cell
def _(plt, small_df, sns):
    for cat in ['delay', 'build_time', 'cap_ex', 'delay_cost']:
        for pro in small_df['profit'].unique():
            sns.scatterplot(data=small_df[small_df['profit']==pro], 
                            x=cat, y='npv', label = 'profit:' +str(pro))
            plt.title(f"NPV vs {cat} sorted by profit")
        plt.show()
    return


@app.cell
def _(run_records):
    run_records.head()
    return


@app.cell
def _(records):
    AC_npvs = records[
        (records['loan_rate'] == 0.12) & 
        (records['payments'] == 30) & 
        (records['rate'] == 0.09) &
        (records['cap_ex'] == 1) &
        (records['delay'] == 8)
    ]
    return (AC_npvs,)


@app.cell
def _(AC_npvs, plt, sns):
    pivot = AC_npvs.pivot_table(index='delay', columns='build_time', values='NPV', aggfunc='mean')
    sns.heatmap(pivot, cmap='coolwarm')
    plt.title("NPV by Delay and Build Time")
    plt.show()
    return


@app.cell
def _(AC_npvs):
    AC_npvs
    return


@app.cell
def _(mo):
    mo.md("""# Value Plots""")
    return


@app.cell
def _(constants, hi, lo, show_range):
    print('Delaying Loan')
    show_range(lo, hi, constants, True)
    print('Loan From Day 1')
    show_range(lo, hi, constants, False)
    return


@app.cell
def _(pd, run_records):
    df = pd.DataFrame(run_records)
    return (df,)


@app.cell
def _(df):
    cap_and_delay = df[df['build_time']==3][df['payments']==15 ][df['profit']==.1 ]
    return (cap_and_delay,)


@app.cell
def _(cap_and_delay, plt):
    for d in  [2,5,8,11]:
        thisdf  = cap_and_delay[cap_and_delay['delay']==d]
        plt.plot(thisdf['cap_ex'], thisdf['npv'], label = f'delay = {d}')
    plt.ylabel('npv value (1 = typical AC line cost)')
    plt.xlabel('cap_ex')


    plt.legend()
    plt.show()
    return


@app.cell
def _():
    return


if __name__ == "__main__":
    app.run()
