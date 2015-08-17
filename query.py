import itertools
import datetime
import dateutil.parser
import dateutil.tz

def to_datetime(date):
    """Turn a date into a datetime at midnight.
    """
    return datetime.datetime.combine(date, datetime.datetime.min.time())


def strip_time(datetime):
    """Return a version of the datetime with time set to zero.
    """
    return to_datetime(datetime.date())

class IssueSnapshot(object):
    """A snapshot of the key fields of an issue at a point in its change history
    """

    def __init__(self, change, key, date, status, resolution, is_resolved):
        self.change = change
        self.key = key
        self.date = date.astimezone(dateutil.tz.tzutc())
        self.status = status
        self.resolution = resolution
        self.is_resolved = is_resolved

    def __hash__(self):
        return hash(self.key)

    def __repr__(self):
        return "<IssueSnapshot change=%s key=%s date=%s status=%s resolution=%s is_resolved=%s>" % (
            self.change, self.key, self.date.isoformat(), self.status, self.resolution, self.is_resolved
        )

class QueryManager(object):
    """Manage and execute queries
    """

    settings = dict(
        project=None,

        issue_types=['Story'],
        valid_resolutions=["Done", "Wontfix"],
        epics=None,

        jql_filter=None,

        epic_link_field='Epic Link',
        release_field='Fix Version/s',
        size_field='Story Points',
        rank_field='Rank',
        team_field='Team',

        max_results=1000,
    )

    fields = dict(
        epic_link=None,
        release=None,
        size=None,
        rank=None,
        team=None,
    )

    def __init__(self, jira, **kwargs):
        self.jira = jira
        settings = self.settings.copy()
        settings.update(kwargs)

        self.settings = settings
        self.resolve_fields()

    # Helpers

    def resolve_fields(self):
        fields = self.jira.fields()

        for k in self.fields.keys():
            name = self.settings['%s_field' % k]
            self.fields[k] = next((f['id'] for f in fields if f['name'] == name))

    def iter_changes(self, issue, include_resolution_changes=True):
        """Yield an IssueSnapshot for each time the issue changed status or
        resolution
        """

        is_resolved = False

        # Find the first status change, if any
        status_changes = filter(
            lambda h: h.field == 'status',
            itertools.chain.from_iterable([c.items for c in issue.changelog.histories])
        )
        last_status = status_changes[0].fromString if len(status_changes) > 0 else issue.fields.status.name
        last_resolution = None

        # Issue was created
        yield IssueSnapshot(
            change=None,
            key=issue.key,
            date=dateutil.parser.parse(issue.fields.created),
            status=last_status,
            resolution=None,
            is_resolved=is_resolved
        )

        for change in issue.changelog.histories:
            change_date = dateutil.parser.parse(change.created)

            resolutions = filter(lambda i: i.field == 'resolution', change.items)
            is_resolved = (resolutions[-1].to is not None) if len(resolutions) > 0 else is_resolved

            for item in change.items:
                if item.field == 'status':
                    # Status was changed
                    last_status = item.toString
                    yield IssueSnapshot(
                        change=item.field,
                        key=issue.key,
                        date=change_date,
                        status=last_status,
                        resolution=last_resolution,
                        is_resolved=is_resolved
                    )
                elif item.field == 'resolution':
                    last_resolution = item.toString
                    if include_resolution_changes:
                        yield IssueSnapshot(
                            change=item.field,
                            key=issue.key,
                            date=change_date,
                            status=last_status,
                            resolution=last_resolution,
                            is_resolved=is_resolved
                        )

    # Basic queries

    def find_issues(self, jql=None, epics=None, order='KEY ASC'):
        """Return a list of issues with changelog metadata.

        Searches for the `issue_types`, `project` and `valid_resolutions`
        set in the settings for the query manager.

        Pass a JQL string to further qualify the query results.

        Pass a list of epics to search by epic link.
        """

        query = []

        query.append('issueType IN (%s)' % ', '.join(['"%s"' % t for t in self.settings['issue_types']]))
        query.append('(resolution IS EMPTY OR resolution IN (%s))' % ', '.join(['"%s"' % r for r in self.settings['valid_resolutions']]))

        if self.settings['project']:
            query.append('project = %s' % self.settings['project'])

        if self.settings['jql_filter'] is not None:
            query.append('(%s)' % self.settings['jql_filter'])

        if self.settings['epics'] is not None:
            query.append('%s in (%s)' % (self.settings['epic_link_field'], ', '.join([f.key for f in self.settings['epics']]),))

        if jql is not None:
            query.append('(%s)' % jql)

        if epics is not None:
            query.append('%s in (%s)' % (self.settings['epic_link_field'], ', '.join([f.key for f in epics]),))

        queryString = "%s ORDER BY %s" % (' AND '.join(query), order,)

        return self.jira.search_issues(queryString, expand='changelog', maxResults=self.settings['max_results'])
