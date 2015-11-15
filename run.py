#! /usr/bin/env python
"""
top-level script executable.
run with python 2.7 after installing packages in pip.txt
"""

from pdb import set_trace as st

# python standard library

import unittest
import argparse

# external libs

# local modules

import capp

import test.func

arg_parser = argparse.ArgumentParser()
arg_parser.add_argument(
    "task",
    help="the task to perform",
    choices=['run', 'initdb', 'test'])

args = arg_parser.parse_args()

if args.task == 'run':
    capp.app.run(host='0.0.0.0', port=5000)
elif args.task == 'initdb':
    with capp.app.app_context():
        capp.initdb()
    print "populated database with sample data"
elif args.task == 'test':
    suite = unittest.TestLoader().loadTestsFromModule(test.func)
    unittest.TextTestRunner().run(suite)
else:
    raise NotImplementedError((
        "unimplemented task '" +
        args.task))
