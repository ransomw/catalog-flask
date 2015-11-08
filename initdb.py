from pdb import set_trace as st

from flask import g

import capp

with capp.app.app_context():
    capp.initdb()


