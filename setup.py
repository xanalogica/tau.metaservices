#############################################################################
#
# Copyright (c) 2011 Tau Productions Inc.
# All Rights Reserved.
#
# This software is subject to the provisions of the Zope Public License,
# Version 2.1 (ZPL).  A copy of the ZPL should accompany this distribution.
# THIS SOFTWARE IS PROVIDED "AS IS" AND ANY AND ALL EXPRESS OR IMPLIED
# WARRANTIES ARE DISCLAIMED, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED
# WARRANTIES OF TITLE, MERCHANTABILITY, AGAINST INFRINGEMENT, AND FITNESS
# FOR A PARTICULAR PURPOSE.
#
##############################################################################
"""
"""

EGGNAME = 'tau.metaservices'
EGGVERS = '1.0'

from ez_setup import use_setuptools
use_setuptools()

import os
from setuptools import setup, find_packages

here = os.path.abspath(os.path.dirname(__file__))  # the directory containing this setup.py file

setup(
    # Basic Identification of Distribution
    name=EGGNAME,
    version=EGGVERS,

    # Descriptions for Potential Users of Distribution
    description="Library of tools for metaprogramming techniques.",
    long_description=(
        open('README.rst').read()
        + '\n' + '-'*60 + '\n\n' +
        "Download\n========"
    ),

    # Contact and Ownership Info
    author = 'Jeff Rush',
    author_email="jeff@taupro.com",
    url="https://github.com/xanalogica/tau.metaservices.git",
    license='ZPL 2.1',

    # Egg Classification Info
    classifiers=[ # python setup.py register --list-classifiers
        "Development Status :: 3 - Alpha",
        "Environment :: Plugins",
        "Intended Audience :: Developers",
        'License :: OSI Approved :: Zope Public License',
        "Natural Language :: English",
        'Operating System :: OS Independent',
        'Programming Language :: Python',
        "Programming Language :: Python :: 2.7",
        "Topic :: Software Development :: Libraries :: Python Modules",
    ],
    keywords='metaprogramming metaclasses descriptors',

    # Location of Stuff Within Distribution
    packages=find_packages('src'),
    namespace_packages=['tau'],
    include_package_data=True,
    zip_safe=False,
    package_dir={
        '': 'src',
    },

    # Dependencies on Other Eggs
    install_requires=[
        'setuptools',
        'zope.interface',
        'zope.testrunner',
    ],

    extras_require={
        'test': ['zope.testrunner',]
    },
)
