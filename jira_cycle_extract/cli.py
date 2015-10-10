from jira import JIRA
import argparse
import getpass

from .config import config_to_options
from .cycletime import CycleTimeQueries

parser = argparse.ArgumentParser(description='Extract cycle time analytics data from JIRA.')
parser.add_argument('config', metavar='config.yml', help='Configuration file')
parser.add_argument('output', metavar='data.csv', help='Output file')
parser.add_argument('-v', dest='verbose', action='store_const', const=True, default=False, help='Verbose output')
parser.add_argument('-n', metavar='N', dest='max_results', type=int, help='Only fetch N most recent issues')
parser.add_argument('--cfd', metavar='cfd.csv', dest='cfd', help='Also calculate Cumulative Flow Diagram values and write to CSV (Experimental!)')
parser.add_argument('--percentiles', metavar='percentiles.csv', dest='percentiles', help='Also calculate cycle time percentile values and write to CSV (Experimental!)')

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

    print "Writing cycle data to", args.output
    cycle_names = [s['name'] for s in q.settings['cycle']]
    cycle_data.to_csv(args.output,
        columns=['key', 'url', 'summary'] + cycle_names + ['issue_type', 'status', 'resolution'] + sorted(options['settings']['fields'].keys()),
        header=['ID', 'Link', 'Name'] + cycle_names + ['Type', 'Status', 'Resolution'] + sorted(options['settings']['fields'].keys()),
        index=False
    )

    if args.cfd:
        print "Writing CFD data to", args.cfd
        q.cfd(cycle_data).to_csv(args.cfd)

    if args.percentiles:
        print "Writing cycle time percentile data to", args.percentiles
        q.scatterplot(cycle_data)['percentiles'].to_csv(args.percentiles)

    print "Done"
