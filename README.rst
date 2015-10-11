JIRA Cycle Data extract utility
===============================

This utility helps extract data from JIRA for processing with the
ActionableAgile™ Analytics tool (https://www.actionableagile.com/analytics-tools/),
as well as ad-hoc analysis using Excel.

It will produce a CSV file with one row for each JIRA issue matching a set of
filter criteria, containing basic information about the issue as well as the
date the issue entered each step in the main cycle workflow.

This data can be used to produce a Cumulative Flow Diagram, a cycle time
scatterplot, a cycle time histogram, and other analytics based on cycle time.

To make it easier to draw these diagrams, the tool can also be used to output
CSV files with pre-calculated values for charting in e.g. Excel.

Installation
------------

Install Python 2.7 and pip. See http://pip.readthedocs.org/en/stable/installing/.

Install using `pip`::

    $ pip install jira-cycle-extract

If you get errors, try to install `numpy` and `pandas` separately first::

    $ pip install numpy pandas
    $ pip install jira-cycle-extract

This will install a binary called `jira-cycle-extract`. You can test that it was
correctly installed using::

    $ jira-cycle-extract -h

If this doesn't work, check the output of `pip install jira-cycle-extract` to
see where it may have installed the binary.

Configuration
-------------

Write a YAML configuration file like so, calling it e.g. `config.yaml`::

    # How to connect to JIRA?
    Connection:
        Domain: https://myserver.atlassian.net
        Username: myusername # If missing, you will be prompted at runtime
        Password: secret     # If missing, you will be prompted at runtime

    # What to search for?
    Criteria:
        Project: ABC # JIRA project key to search
        Issue types: # Which issue types to include
            - Story
            - Defect
        Valid resolutions: # Which resolution statuses to include (unresolved is always included)
            - Done
            - Closed
        JQL: labels != "Spike" # Additional filter as raw JQL, optional

    # Describe the workflow. Each step can be mapped to either a single JIRA
    # status, or a list of statuses that will be treated as equivalent
    Workflow:
        Open: Open
        Analysis IP: Analysis in Progress
        Analysis Done: Analysis Done
        Development IP: Development in Progress
        Development Done: Development Done
        Test IP: Test in Progress
        Test Done: Test Done
        Done:
            - Closed
            - Done

    # Map field names to additional attributes to extract
    Attributes:
        Components: Component/s
        Priority: Priority
        Release: Fix version/s

If you are unfamiliar with YAML, remember that:

* Comments start with `#`
* Sections are defined with a name followed by a colon, and then an indented
  block underneath. `Connection`, `Criteria`, `Workflow` and `Attributes` area
  all sections in the example above.
* Indentation has to use spaces, not tabs!
* Single values can be set using `Key: value` pairs. For example,
  `Project: ABC` above sets the key `Project` to the value `ABC`.
* Lists of values can be set by indenting a new block and placing a `-` in front
  of each list value. In the example above, the `Issue types` list contains
  the values `Story` and `Defect`.

The sections for `Connection`, `Criteria` and `Workflow` are required.

Under `Conection`, only `Domain` is required. If not specified, the script will
prompt for both or either of username and password when run.

Under `Criteria`, all fields are technically optional, but you should specify
at least some of them to avoid an unbounded query. `Issue types` and
`Valid resolutions` can be set to either single values or lists.

Under `Workflow`, at least two steps are required. Specify the steps in order.
You may either specify a single workflow value or a list (as shown for `Done`
above), in which case multiple JIRA statuses will be collapsed into a single
state for analytics purposes.

The file, and values for things like workflow statuses and attributes, are case
insensitive.

When specifying attributes, use the *name* of the field (as rendered on screen
in JIRA), not its id (as you might do in JQL), so e.g. use `Component/s` not
`components`.

The attributes `Type` (issue type), `Status` and `Resolution` are always
included.

When specifying fields like `Component/s` or `Fix version/s` that may have
lists of values, only the first value set will be used.

Running
-------

To produce the basic cycle time data, run `jira-cycle-extract` passing the name
of the YAML configuration file and the name of the output CSV file::

    $ jira-cycle-extract config.yaml data.csv

This will extract a CSV file called `data.csv` with cycle data based on the
configuration in `config.yaml`.

Use the `-v` option to print more information during the extract process.

Use the `-n` option to limit the number of items fetched from JIRA, based on
the most recently updated issues. This is useful for testing the Configuration
without waiting for long downloads:

    $ jira-cycle-extract -v -n 10 config.yaml data.csv

To produce Cumulative Flow Diagram statistics, use the `--cfd` option:

    $ jira-cycle-extract --cfd cfd.csv config.yaml data.csv

This will yield a `cfd.csv` file with one row for each date, one column for each
step in the workflow, and a count of the number of issues in that workflow state
on that day. To plot a CFD, chart this data as a (non-stacked) area chart. You
should technically exclude the series in the first column if it represents the
backlog!

To produce cycle time scatter plot statistics, use the `--scatterplot` option:

    $ jira-cycle-extract --scatterplot scatterplot.csv config.yaml data.csv

This will yield a `scatterplot.csv` file with one row for each item that was
completed (i.e. it reached the last workflow state), with columns giving the
completion date and the number of days elapsed from the item entering the first
active state (i.e. the second step in the workflow, on the basis that the first
item represents a backlog or intake queue) to the item entering the completed
state. These two columns can be plotted as an X/Y scatter plot. Further columns
contain the dates of entry into each workflow state and the various issue
metadata to allow further filtering.

To be able to easily draw a histogram of the cycle time values, use the
`--histogram` option:

    $ jira-cycle-extract --histogram histogram.csv config.yaml data.csv

This will yield a `histogram.csv` file with two columns: bin ranges and the
number of items with cycle times falling within each bin. These can be charted
as a column or bar chart.

To find out the 30th, 50th, 70th, 85th and 95th percentile cycle time values,
pass the --percentiles option:

    $ jira-cycle-extract --scatterplot scatterplot.csv --percentiles config.yaml data.csv

These will be printed to the console.

Troubleshooting
---------------

* If Excel complains about a `SYLK` format error, ignore it. Click OK. See
  https://support.microsoft.com/en-us/kb/215591.
* JIRA error messages may be printed out as HTML in the console. The error is
  in there somewhere, but may be difficult to see. Most likely, this is either
  an authentication failure (incorrect username/password or blocked account),
  or an error in the `Criteria` section resulting in invalid JQL.
* If you aren't getting the issues you expected to see, use the `-v` option to
  see the JQL being sent to JIRA. Paste this into the JIRA issue filter search
  box ("Advanced mode") to see how JIRA evaluates it.
* Old workflow states can still be part of an issue's history after a workflow
  has been modified. Use the `-v` option to find out about workflow states that
  haven't been mapped.
* Excel sometimes picks funny formats for data in CSV files.

Changelog
---------

0.3 - October 11 2015
    * Add proper support for `--cfd`, `--scatterplot`, `--percentiles` and
      `--histogram`
    * Fix some typing issues with the main cycle data extract.

0.2 - October 10 2015
    * Fix documentation errors

0.1 - October 10 2015
    * Initial release
