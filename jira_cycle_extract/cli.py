from jira import JIRA
import argparse
import getpass

from .config import config_to_options
from .cycletime import CycleTimeQueries

parser = argparse.ArgumentParser(description='Extract cycle time analytics data from JIRA.')
parser.add_argument('config', metavar='config.yml', help='Configuration file')
parser.add_argument('output', metavar='data.csv', help='Output file')
parser.add_argument('-v', dest='verbose', action='store_const', const=True, default=False, help='Verbose output')
parser.add_argument('-n', metavar='N', dest='max_results', type=int, help='Only fetch N most recently updated issues')
parser.add_argument('--cfd', metavar='cfd.csv', dest='cfd', help='Calculate data to draw a Cumulative Flow Diagram and write to CSV. Hint: Plot as a (non-stacked) area chart.')
parser.add_argument('--scatterplot', metavar='scatterplot.csv', dest='scatter', help='Calculate data to draw a cycle time scatter plot and write to CSV. Hint: Plot as a scatter chart.')
parser.add_argument('--histogram', metavar='histogram.csv', dest='histogram', help='Calculate data to draw a cycle time histogram and write to CSV. Hint: Plot as a column chart.')
parser.add_argument('--percentiles', action='store_const', const=True, default=False, help='Calculate and print cycle time percentiles')

def get_jira_client(connection):
    url = connection['domain']
    username = connection['username']
    password = connection['password']

    print "Connecting to", url

    if not username:
        username = raw_input("Username: ")

    if not password:
        password = getpass.getpass("Password: ")

    return JIRA({'server': url}, basic_auth=(username, password))

def main():
    args = parser.parse_args()

    if not args.config or not args.output:
        args.print_usage()
        return

    with open(args.config) as config:
        options = config_to_options(config.read())

    if args.max_results:
        options['settings']['max_results'] = args.max_results

    jira = get_jira_client(options['connection'])

    q = CycleTimeQueries(jira, **options['settings'])

    print "Fetching issues (this could take some time)"
    cycle_data = q.cycle_data(verbose=args.verbose)

    cycle_names = [s['name'] for s in q.settings['cycle']]
    field_names = sorted(options['settings']['fields'].keys())

    print "Writing cycle data to", args.output
    cycle_data.to_csv(args.output,
        columns=['key', 'url', 'summary'] + cycle_names + ['issue_type', 'status', 'resolution'] + field_names,
        header=['ID', 'Link', 'Name'] + cycle_names + ['Type', 'Status', 'Resolution'] + field_names,
        index=False
    )

    if args.cfd:
        print "Writing Cumulative Flow Diagram data to", args.cfd
        q.cfd(cycle_data).to_csv(args.cfd)

    if args.scatter:
        print "Writing cycle time scatter plot data to", args.scatter
        q.scatterplot(cycle_data).to_csv(args.scatter, index=False)

    if args.percentiles:
        print "Cycle time percentiles:"
        print q.percentiles(cycle_data).to_string()

    if args.histogram:
        print "Writing cycle time histogram data to", args.histogram
        q.histogram(cycle_data).to_csv(args.histogram, header=True)


    print "Done"
