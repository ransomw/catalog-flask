"""
main views module
mainly a place to register blueprints
"""

from pdb import set_trace as st

# local modules

from capp import app

from views_auth import bp_auth
from views_api import bp_api
from views_catalog import bp_catalog

app.register_blueprint(bp_auth)
app.register_blueprint(bp_catalog)
app.register_blueprint(bp_api)

bp_auth.home_view = 'catalog.home'

