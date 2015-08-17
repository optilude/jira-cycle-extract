from query import QueryManager
import pandas as pd
import numpy as np

class StatusTypes:
    backlog = 'backlog'
    accepted = 'accepted'
    complete = 'complete'

class CycleTimeQueries(QueryManager):
    """Analysis for cycle time data, producing cumulative flow diagrams,
    scatter plots and histograms.

    Initialise with a `cycle`, a list of dicts representing the steps in
    a cycle. Each dict describes that step with keys `name`, `type` (one of
    "backlog", "accepted" or "complete" as per the `StatusTypes` enum) and
    `statuses` (a list of equivalent JIRA workflow statuses that map onto
    this step).
    """

    settings = dict(
        cycle=[  # flow steps, types, and mapped JIRA statuses
            {
                "name": 'todo',
                "type": StatusTypes.backlog,
                "statuses": ["Open", "To Do"],
            },
            {
                "name": 'analysis',
                "type": StatusTypes.accepted,
                "statuses": ["Analysis"],
            },
            {
                "name": 'analysis-done',
                "type": StatusTypes.accepted,
                "statuses": ["Analysis Done"],
            },
            {
                "name": 'development',
                "type": StatusTypes.accepted,
                "statuses": ["In Progress"],
            },
            {
                "name": 'done',
                "type": StatusTypes.complete,
                "statuses": ["Done", "Closed"],
            },
        ]
    )

    def __init__(self, jira, **kwargs):
        settings = super(CycleTimeQueries, self).settings.copy()
        settings.update(self.settings.copy())
        settings.update(kwargs)

        settings['cycle_lookup'] = {}
        for idx, cycle_step in enumerate(settings['cycle']):
            for status in cycle_step['statuses']:
                settings['cycle_lookup'][status] = dict(
                    index=idx,
                    name=cycle_step['name'],
                    type=cycle_step['type'],
                )

        super(CycleTimeQueries, self).__init__(jira, **settings)

    def cycle_data(self):
        """Build a numberically indexed data frame with the following 'fixed'
        columns: `key`, 'url', 'issue_type', `summary`, `status`, `resolution`,
        `size`, `release`, and `rank` from JIRA.

        In addition, `cycle_time` will be set to the time delta between the
        first `accepted`-type column and the first `complete` column, or None.

        The remaining columns are the names of the items in the configured
        cycle, in order.

        Each cell contains the last date/time stamp when the relevant status
        was set.

        If an item moves backwards through the cycle, subsequent date/time
        stamps in the cycle are erased.
        """

        data = []
        cycle_names = [s['name'] for s in self.settings['cycle']]
        accepted_steps = set(s['name'] for s in self.settings['cycle'] if s['type'] == StatusTypes.accepted)
        completed_steps = set(s['name'] for s in self.settings['cycle'] if s['type'] == StatusTypes.complete)

        for issue in self.find_issues():
            size = getattr(issue.fields, self.fields['size'], None)
            release = getattr(issue.fields, self.fields['release'], None)
            rank = getattr(issue.fields, self.fields['rank'], None)
            team = getattr(issue.fields, self.fields['team'], None)

            item = {
                'key': issue.key,
                'url': "%s/browse/%s" % (self.jira._options['server'], issue.key,),
                'issue_type': issue.fields.issuetype.name,
                'summary': issue.fields.summary,
                'status': issue.fields.status.name,
                'resolution': issue.fields.resolution.name if issue.fields.resolution else None,
                'size': size.value if size else None,
                'release': release[0].name if release else None,
                'team': team.value if team else None,
                'rank': rank,
                'cycle_time': None,
                'completed_timestamp': None
            }

            for cycle_name in cycle_names:
                item[cycle_name] = None

            # Record date of status changes
            for snapshot in self.iter_changes(issue, False):
                cycle_step = self.settings['cycle_lookup'].get(snapshot.status, None)
                if cycle_step is None:
                    continue

                item[cycle_step['name']] = snapshot.date

            # Wipe timestamps if items have moved backwards; calculate cycle time

            previous_timestamp = None
            accepted_timestamp = None
            completed_timestamp = None

            for cycle_name in cycle_names:
                if (
                    item[cycle_name] is not None and
                    previous_timestamp is not None and
                    item[cycle_name] < previous_timestamp
                ):
                    item[cycle_name] = None

                if item[cycle_name] is not None:
                    previous_timestamp = item[cycle_name]

                    if accepted_timestamp is None and previous_timestamp is not None and cycle_name in accepted_steps:
                        accepted_timestamp = previous_timestamp
                    if completed_timestamp is None and previous_timestamp is not None and cycle_name in completed_steps:
                        completed_timestamp = previous_timestamp

            if accepted_timestamp is not None and completed_timestamp is not None:
                item['cycle_time'] = completed_timestamp - accepted_timestamp
                item['completed_timestamp'] = completed_timestamp

            data.append(item)

        return pd.DataFrame(data, columns=['key', 'url', 'issue_type', 'summary', 'status', 'resolution', 'size',
                                          'team', 'release', 'rank', 'cycle_time', 'completed_timestamp'] + cycle_names)

    def cfd(self, cycle_data):
        """Return the data to build a cumulative flow diagram: a DataFrame,
        indexed by day, with columns containing cumulative counts for each
        of the items in the configured cycle.

        In addition, a column called `cycle_time` contains the approximate
        average cycle time of that day based on the first "accepted" status
        and the first "complete" status.
        """

        cycle_names = [s['name'] for s in self.settings['cycle']]
        cycle_start = next(s['name'] for s in self.settings['cycle'] if s['type'] == StatusTypes.accepted)
        cycle_end = next(s['name'] for s in self.settings['cycle'] if s['type'] == StatusTypes.complete)

        # Build a dataframe of just the "date" columns
        df = cycle_data[cycle_names]

        # Strip out times from all dates
        df = pd.DataFrame(
            np.array(df.values, dtype='<M8[ns]').astype('<M8[D]').astype('<M8[ns]'),
            columns=df.columns,
            index=df.index
        )

        # Count number of times each date occurs
        df = pd.concat({col: df[col].value_counts() for col in df}, axis=1)

        # Fill missing dates with 0 and run a cumulative sum
        df = df.fillna(0).cumsum(axis=0)

        # Reindex to make sure we have all dates
        start, end = df.index.min(), df.index.max()
        df = df.reindex(pd.date_range(start, end, freq='D'), method='ffill')

        # Calculate the approximate average cycle time
        df['cycle_time'] = df[cycle_end] - df[cycle_start]

        return df


    def histogram(self, cycle_data, bins=10):
        """Return histogram data for the cycle times in `cycle_data`. Returns
        a dictionary with keys `bin_values` and `bin_edges` of numpy arrays
        """
        hist = np.histogram(cycle_data['cycle_time'].astype('timedelta64[D]').dropna(), bins=bins)
        return {
            'bin_values': hist[0],
            'bin_edges': hist[1]
        }

    def scatterplot(self, cycle_data, percentiles=(0.3, 0.5, 0.7, 0.85, 0.95,)):
        """Return scatterplot data for the cycle times in `cycle_data`.
        Return a dictionary with keys `series` (a list of dicts with keys
        `x`, `y` and the fields from each record in `cycle_data`) and
        `percentiles` (a series with percentile values as keys).
        """

        data = cycle_data.dropna(subset=['cycle_time', 'completed_timestamp']) \
                         .rename(columns={'cycle_time': 'y', 'completed_timestamp': 'x'})

        data['y'] = data['y'].astype('timedelta64[D]')

        return {
            'series': data.to_dict('records'),
            'percentiles': data['y'].quantile(percentiles)
        }
