HAVE_CHARTING = True

try:
    import seaborn as sns
    import pandas as pd
    import numpy as np
    import matplotlib.pyplot as plt

    import statsmodels.formula.api as sm

except ImportError:
    HAVE_CHARTING = False

import datetime

class UnchartableData(Exception):
    """Thrown when data does not support the required chart
    """

def set_context(context="talk"):
    sns.set_context(context)

def set_style(style="darkgrid"):
    sns.set_style(style)

def cycle_time_scatterplot(cycle_data, percentiles=[0.3, 0.5, 0.75, 0.85, 0.95], ax=None):
    scatter_df = cycle_data[['key', 'summary', 'completed_timestamp', 'cycle_time']].dropna(subset=['cycle_time', 'completed_timestamp'])
    ct_days = scatter_df['cycle_time'].dt.days

    if len(ct_days.index) < 2:
        raise UnchartableData("Need at least 2 completed items to draw scatterplot")

    if ax is None:
        fig, ax = plt.subplots()
    else:
        fig = ax.get_figure()

    fig.autofmt_xdate()

    ax.set_xlabel("Completed date")
    ax.set_ylabel("Cycle time (days)")

    ax.plot_date(x=scatter_df['completed_timestamp'], y=ct_days, ms=5)

    # Add percentiles
    left, right = ax.get_xlim()
    for percentile, value in ct_days.quantile(percentiles).iteritems():
        ax.hlines(value, left, right, linestyles='--', linewidths=1)
        ax.annotate("%.0f%% (%.0f days)" % ((percentile * 100), value,),
            xy=(left, value),
            xytext=(left + 1, value + 0.5),
            fontsize="small",
            ha="left"
        )

    return ax

def cycle_time_histogram(cycle_data, bins=30, percentiles=[0.3, 0.5, 0.75, 0.85, 0.95], ax=None):
    histogram_df = cycle_data[['cycle_time']].dropna(subset=['cycle_time'])
    ct_days = histogram_df['cycle_time'].dt.days

    if len(ct_days.index) < 2:
        raise UnchartableData("Need at least 2 completed items to draw histogram")

    if ax is None:
        fig, ax = plt.subplots()

    sns.distplot(ct_days, bins=bins, ax=ax, axlabel="Cycle time (days)")

    left, right = ax.get_xlim()
    ax.set_xlim(0, right)

    # Add percentiles
    bottom, top = ax.get_ylim()
    for percentile, value in ct_days.quantile(percentiles).iteritems():
        ax.vlines(value, bottom, top - 0.001, linestyles='--', linewidths=1)
        ax.annotate("%.0f%% (%.0f days)" % ((percentile * 100), value,),
            xy=(value, top),
            xytext=(value, top - 0.001),
            rotation="vertical",
            fontsize="small",
            ha="right"
        )

    return ax

def cfd(cfd_data, ax=None):
    if len(cfd_data.index) == 0:
        raise UnchartableData("Cannot draw CFD with no data")

    if ax is None:
        fig, ax = plt.subplots()
    else:
        fig = ax.get_figure()

    fig.autofmt_xdate()

    ax.set_xlabel("Date")
    ax.set_ylabel("Number of items")

    cfd_data.plot.area(ax=ax, stacked=False, legend=False)
    ax.legend(loc=0, title="", frameon=True)

    return ax

def throughput_chart(throughput_data, ax=None):
    if len(throughput_data.index) == 0:
        raise UnchartableData("Cannot draw throughput chart with no completed items")

    if ax is None:
        fig, ax = plt.subplots()
    else:
        fig = ax.get_figure()

    fig.autofmt_xdate()

    ax.set_xlabel("Completed date")
    ax.set_ylabel("Number of items")

    ax.bar(throughput_data.index, throughput_data['count'])

    return ax

def throughput_trend_chart(throughput_data, ax=None):
    if len(throughput_data.index) == 0:
        raise UnchartableData("Cannot draw throughput chart with no completed items")

    if ax is None:
        fig, ax = plt.subplots()
    else:
        fig = ax.get_figure()

    fig.autofmt_xdate()

    # Calculate zero-indexed days to allow linear regression calculation
    day_zero = throughput_data.index[0]
    throughput_data['day'] = (throughput_data.index - day_zero).days

    # Fit a linear regression (http://stackoverflow.com/questions/29960917/timeseries-fitted-values-from-trend-python)
    fit = sm.ols(formula="count ~ day", data=throughput_data).fit()
    throughput_data['fitted'] = fit.predict(throughput_data)

    # Plot

    ax.set_xlabel("Completed date")
    ax.set_ylabel("Number of items")

    ax.bar(throughput_data.index, throughput_data['count'])

    bottom, top = ax.get_ylim()
    ax.set_ylim(0, top + 1)

    for x, y in zip(throughput_data.index, throughput_data['count']):
        if y == 0:
            continue
        ax.annotate(
            "%.0f" % y,
            xy=(x.toordinal(), y + 0.2),
            ha='center',
            va='bottom',
            fontsize="x-small",
        )

    ax.plot(throughput_data.index, throughput_data['fitted'], '--', linewidth=2)

    return ax

def burnup(cfd_data, backlog_column=None, done_column=None, ax=None):
    if len(cfd_data.index) == 0:
        raise UnchartableData("Cannot draw burnup with no data")

    if ax is None:
        fig, ax = plt.subplots()

    ax.set_xlabel("Date")
    ax.set_ylabel("Number of items")

    if backlog_column is None:
        backlog_column = cfd_data.columns[0]

    if done_column is None:
        done_column = cfd_data.columns[-1]

    plot_data = cfd_data[[backlog_column, done_column]]
    plot_data.plot.line(ax=ax, legend=True)
    ax.legend(loc=0, title="", frameon=True)

    return ax

def burnup_monte_carlo(start_value, target_value, start_date, throughput_data, trials=100):

    frequency = throughput_data.index.freq

    # degenerate case - no steps, abort
    if throughput_data['count'].sum() <= 0:
        return None

    # guess how far away we are; drawing samples one at a time is slow
    sample_buffer_size = int(2 * (target_value - start_value) / throughput_data['count'].mean())

    sample_buffer = dict(idx=0, buffer=None)

    def get_sample():
        if sample_buffer['buffer'] is None or sample_buffer['idx'] >= len(sample_buffer['buffer'].index):
            sample_buffer['buffer'] = throughput_data['count'].sample(sample_buffer_size, replace=True)
            sample_buffer['idx'] = 0

        sample_buffer['idx'] += 1
        return sample_buffer['buffer'].iloc[sample_buffer['idx'] - 1]

    series = {}
    for t in range(trials):
        current_date = start_date
        current_value = start_value

        dates = [current_date]
        steps = [current_value]

        while current_value < target_value:
            current_date += frequency
            current_value += get_sample()

            dates.append(current_date)
            steps.append(current_value)

        series["Trial %d" % t] = pd.Series(steps, index=dates, name="Trial %d" % t)

    return pd.DataFrame(series)

def burnup_forecast(
    cfd_data, throughput_data, trials=100,
    target=None, backlog_column=None, done_column=None, percentiles=[0.5, 0.75, 0.85, 0.95],
    ax=None
):
    if len(cfd_data.index) == 0:
        raise UnchartableData("Cannot draw burnup forecast chart with no data")
    if len(throughput_data.index) == 0:
        raise UnchartableData("Cannot draw burnup forecast chart with no completed items")


    if backlog_column is None:
        backlog_column = cfd_data.columns[0]

    if done_column is None:
        done_column = cfd_data.columns[-1]

    if target is None:
        target = cfd_data[backlog_column].max()

    if ax is None:
        fig, ax = plt.subplots()
    else:
        fig = ax.get_figure()

    fig.autofmt_xdate()

    ax.set_xlabel("Date")
    ax.set_ylabel("Number of items")

    plot_data = cfd_data[[backlog_column, done_column]]
    plot_data.plot.line(ax=ax, legend=True)

    mc_trials = burnup_monte_carlo(
        start_value=cfd_data[done_column].max(),
        target_value=target,
        start_date=cfd_data.index.max(),
        throughput_data=throughput_data,
        trials=trials
    )

    if mc_trials is not None:

        for col in mc_trials:
            mc_trials[col][mc_trials[col] > target] = target

        mc_trials.plot.line(ax=ax, legend=False, color='r', linewidth=1)

        # percentiles at finish line
        finish_dates = mc_trials.apply(pd.Series.last_valid_index)
        finish_date_percentiles = finish_dates.quantile(percentiles).dt.normalize()

        # workaround for mpld3 date serialization bug
        to_days_since_epoch = lambda d: (d - datetime.datetime(1970, 1, 1)).days

        bottom, top = ax.get_ylim()
        for percentile, value in finish_date_percentiles.iteritems():

            ax.vlines(value, bottom, target, linestyles='--', linewidths=1)
            ax.annotate("%.0f%% (%s)" % ((percentile * 100), value.strftime("%d/%m/%Y"),),
                xy=(to_days_since_epoch(value), (top - bottom) / 2),
                xytext=(to_days_since_epoch(value), (top - bottom) / 2),
                rotation="vertical",
                fontsize="x-small",
                ha="left",
                backgroundcolor="#ffffff"
            )

    left, right = ax.get_xlim()
    ax.hlines(target, left, right, linestyles='--', linewidths=1)

    ax.get_legend().set_frame_on(True)

    return ax

def ageing_wip_chart(cycle_data, start_column, end_column, done_column=None, now=None, ax=None):
    if len(cycle_data.index) == 0:
        raise UnchartableData("Cannot draw ageing WIP chart with no data")

    if ax is None:
        fig, ax = plt.subplots()

    if now is None:
        now = pd.Timestamp.now()

    if done_column is None:
        done_column = cycle_data.columns[-1]

    today = now.date()

    # remove items that are done
    cycle_data = cycle_data[pd.isnull(cycle_data[done_column])]
    cycle_data = pd.concat((
        cycle_data[['key', 'summary']],
        cycle_data.ix[:, start_column:end_column]
    ), axis=1)

    def extract_status(row):
        last_valid = row.last_valid_index()
        if last_valid is None:
            return np.NaN
        return last_valid

    def extract_age(row):
        started = row[start_column]
        if pd.isnull(started):
            return np.NaN
        return (today - started.date()).days

    wip_data = cycle_data[['key', 'summary']].copy()
    wip_data['status'] = cycle_data.apply(extract_status, axis=1)
    wip_data['age'] = cycle_data.apply(extract_age, axis=1)

    wip_data.dropna(how='any', inplace=True)

    sns.swarmplot(x='status', y='age', order=cycle_data.columns[2:], data=wip_data, ax=ax)

    ax.set_xlabel("Status")
    ax.set_ylabel("Age (days)")

    ax.set_xticklabels(ax.xaxis.get_majorticklabels(), rotation=90)

    bottom, top = ax.get_ylim()
    ax.set_ylim(0, top)

    return ax

def wip_chart(cfd_data, frequency="1W-MON", start_column=None, end_column=None, ax=None):
    if len(cfd_data.index) == 0:
        raise UnchartableData("Cannot draw WIP chart with no data")

    if start_column is None:
        start_column = cfd_data.columns[1]
    if end_column is None:
        end_column = cfd_data.columns[-1]

    if ax is None:
        fig, ax = plt.subplots()

    wip_data = pd.DataFrame({'wip': cfd_data[start_column] - cfd_data[end_column]})

    groups = wip_data[['wip']].groupby(pd.TimeGrouper(frequency, label='left'))
    labels = [x[0].strftime("%d/%m/%Y") for x in groups]

    groups.boxplot(subplots=False, ax=ax, showmeans=True, return_type='axes')
    ax.set_xticklabels(labels, rotation=70, size='small')

    ax.set_xlabel("Week")
    ax.set_ylabel("WIP")

    return ax

def net_flow_chart(cfd_data, frequency="1W-MON", start_column=None, end_column=None, ax=None):
    if len(cfd_data.index) == 0:
        raise UnchartableData("Cannot draw net flow chart with no data")

    if start_column is None:
        start_column = cfd_data.columns[1]
    if end_column is None:
        end_column = cfd_data.columns[-1]

    if ax is None:
        fig, ax = plt.subplots()

    weekly_data = cfd_data[[start_column, end_column]].resample(frequency, label='left').max()
    weekly_data['arrivals'] = weekly_data[start_column].diff()
    weekly_data['departures'] = weekly_data[end_column].diff()
    weekly_data['net_flow'] = weekly_data['departures'] - weekly_data['arrivals']
    weekly_data['positive'] = weekly_data['net_flow'] >= 0

    ax.set_xlabel("Week")
    ax.set_ylabel("Net flow (departures - arrivals)")

    weekly_data['net_flow'].plot.bar(ax=ax, color=weekly_data['positive'].map({True: 'b', False: 'r'}),)

    labels = [d.strftime("%d/%m/%Y") for d in weekly_data.index]
    ax.set_xticklabels(labels, rotation=70, size='small')

    return ax
