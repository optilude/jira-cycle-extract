from setuptools import setup, find_packages
# To use a consistent encoding
# from codecs import open
from os import path

here = path.abspath(path.dirname(__file__))

long_description = ""

# Get the long description from the README file
# with open(path.join(here, 'README.rst'), encoding='utf-8') as f:
#     long_description = f.read()

setup(
    name='actionable-agile-extract',
    version='0.1',
    description='Extract data from JIRA to the ActionableAgile analytics tool',
    long_description=long_description,
    author='Martin Aspeli',
    author_email='optilude@gmail.com',
    license='MIT',
    keywords='agile jira analytics',
    packages=find_packages(exclude=['contrib', 'docs', 'tests*']),
    install_requires=[
        'jira',
        'PyYAML',
        'pandas',
        'numpy',
        'python-dateutil',
        'pydicti'
    ],

    # extras_require={
    #     'dev': ['check-manifest'],
    #     'test': ['coverage'],
    # },

    entry_points={
        'console_scripts': [
            'jira-cycle-extract=jira_cycle_extract.cli:main',
        ],
    },
)
