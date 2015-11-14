from pdb import set_trace as st

import os
import logging

from flask import Flask
from flask.ext.seasurf import SeaSurf

import config

_SETTINGS_ENV_VAR = 'FLASK_CATALOG_SETTINGS'

app = Flask(__name__)

if os.environ.get(_SETTINGS_ENV_VAR):
    app.config.from_envvar(_SETTINGS_ENV_VAR)
else:
    app.config.from_object(config)

csrf = SeaSurf(app)

if not app.debug:
    file_handler = logging.FileHandler(app.config['LOG_FILE'])
    # possible log levels:
    # CRITICAL ERROR WARNING INFO DEBUG NOTSET
    file_handler.setLevel(logging.WARNING)
    file_handler.setFormatter(logging.Formatter(
        '%(asctime)s %(levelname)s: %(message)s '
        '[in %(pathname)s:%(lineno)d]'))
    app.logger.addHandler(file_handler)
    logging.getLogger('sqlalchemy').addHandler(file_handler)

# although a pep8 violation, this is recommended at
# http://flask.pocoo.org/docs/0.10/patterns/packages/
import capp.views
from lotsofitems import lots_of_items as initdb
