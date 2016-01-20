try:
    from setuptools import setup
except ImportError:
    from distutils.core import setup

config = {
    'description': 'delim - Utility functions for working with delimited (CSV) files in Python 2.',
    'author': 'Jeff Zellman',
    'url': 'http://github.com/jzellman/delim',
    'download_url': 'http://github.com/jzellman/delim',
    'author_email': 'jzellman@gmail.com',
    'version': '0.0.3',
    'install_requires': ['nose'],
    'packages': ['delim'],
    'scripts': [],
    'name': 'delim'
}

setup(**config)
