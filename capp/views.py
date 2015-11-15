"""
main views module
mainly a place to register blueprints
"""

from pdb import set_trace as st

# external libs

from flask import session as login_session
from flask import g

# local modules

from models import User
from models import get_db

from capp import app

from views_auth import bp_auth
from views_api import bp_api
from views_catalog import bp_catalog


# todo: only the blueprint need know about before_request
@app.before_request
def before_request():
    g.user = None
    if 'user_id' in login_session:
        g.user = get_db().query(User).filter_by(
            id=login_session.get('user_id')).one()


app.register_blueprint(bp_auth)
app.register_blueprint(bp_catalog)
app.register_blueprint(bp_api)
