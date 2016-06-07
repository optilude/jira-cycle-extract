from setuptools import setup, find_packages
from codecs import open
from os import path

here = path.abspath(path.dirname(__file__))

# Get the long description from the README file
with open(path.join(here, 'README.rst'), encoding='utf-8') as f:
    long_description = f.read()

setup(
    name='jira-cycle-extract',
    version='0.10',
    description='Extract cycle time analytics data from JIRA',
    long_description=long_description,
    author='Martin Aspeli',
    author_email='optilude@gmail.com',
    url='https://github.com/optilude/jira-cycle-extract',
    license='MIT',
    keywords='agile jira analytics',
    packages=find_packages(exclude=['contrib', 'docs', 'tests*']),
    install_requires=[
        'jira',
        'PyYAML',
        'pandas>=0.18',
        'numpy',
        'python-dateutil',
        'pydicti',
        'openpyxl',
    ],

    extras_require={
        'charting': ['seaborn', 'matplotlib', 'statsmodels'],
    },

    entry_points={
        'console_scripts': [
            'jira-cycle-extract=jira_cycle_extract.cli:main',
        ],
    },
)
