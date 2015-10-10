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

Installation
------------

Install Python 2.7 and pip. See http://pip.readthedocs.org/en/stable/installing/.

Install using `pip`::

    $ pip install jira-cycle-extract

If you get errors, try to install `numpy` and `pandas` separately first::

    $ pip install numpy pandas
    $ pip install jira-cycle-extract

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

The sections for `Connection`, `Criteria` and `Workflow` are required.

Under `Conection`, only `Domain` is required. If not specified, the script will
prompt for both or either of username and password when run.

Under `Criteria`, all fields are technically optional, but you should specify
at least some of them to avoid an unbounded query.

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

Run the binary with::

    $ jira-cycle-extract config.yaml data.csv

This will extract a CSV file called `data.csv` with cycle data based on the
configuration in `config.yaml`.

Use the `-v` option to print more information during the extract process.
