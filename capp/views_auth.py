"""
authorization module
(currently not very modular)
"""

from pdb import set_trace as st

# python standard library
import json
import random
import string
from functools import wraps

# external libs

from werkzeug.security import generate_password_hash
from werkzeug.security import check_password_hash

from flask import render_template
from flask import session as login_session
from flask import redirect
from flask import url_for
from flask import Blueprint
from flask import make_response
from flask import request
from flask import current_app
from flask import g

from sqlalchemy.orm.exc import NoResultFound

from oauth2client.client import flow_from_clientsecrets
from oauth2client.client import FlowExchangeError

import requests

import httplib2

# local modules

import view_helpers as vh

from models import User
from models import get_db

from capp import csrf

G_CLIENT_ID = json.loads(
    open('client_secrets.json', 'r').read())['web']['client_id']


class AuthBlueprint(Blueprint):

    def __init__(self, *args, **kwargs):
        self._home_url = '/'
        self._home_view = None
        super(AuthBlueprint, self).__init__(*args, **kwargs)

    def register(self, app, options, first_registration=False):

        @app.before_request
        def before_request():
            g.user = None
            if 'user_id' in login_session:
                g.user = get_db().query(User).filter_by(
                    id=login_session.get('user_id')).one()

        super(AuthBlueprint, self).register(
            app, options, first_registration)

    @property
    def home_view(self):
        return self._home_view

    @home_view.setter
    def home_view(self, val):
        # # throw an error if the view doesn't exist
        # # ... maybe this isn't the desired behavior?
        # url_for(val)
        # # ... attempting to generate url w/o app ctx "pushed" error
        self._home_view = val

    @property
    def home_url(self):
        if self._home_view is not None:
            return url_for(self._home_view)
        else:
            return self._home_url


bp_auth = AuthBlueprint('auth', __name__,
                        template_folder='templates')


def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in login_session:
            return redirect(url_for('auth.login', next=request.url))
        return f(*args, **kwargs)
    return decorated_function


@bp_auth.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        if request.form.get('sign-in') is not None:
            try:
                user = get_db().query(User).filter_by(
                    email=request.form.get('email')).one()
            except NoResultFound:
                err_msg = ("no user record found for email '%s'" %
                           request.form.get('email'))
                return render_template(
                    'err.html', err_msg=err_msg), 401
            if user.password is None:
                err_msg = ("User account created with third-party"
                           "service.  Sign up locally"
                           " or sign in with third-party.")
                return render_template(
                    'err.html', err_msg=err_msg), 401
            if check_password_hash(user.password,
                                   request.form.get('password')):
                login_session['user_id'] = user.id
            else:
                # todo: use a template
                return "bad password", 401
        else:
            # request.form.get('sign-in') is None
            if request.form.get('sign-up') is None:
                # todo: use a template
                return "must specify sign up or sign in", 400
            if ((request.form.get('password') !=
                 request.form.get('password-confirm'))):
                # todo: use a template
                return "passwords don't match", 400
            try:
                user = get_db().query(User).filter_by(
                    email=request.form.get('email')).one()
            except NoResultFound:
                user = User(email=request.form.get('email'))
            if user.password is not None:
                err_msg = "user already registered"
                return render_template(
                    'err.html', err_msg=err_msg), 401
            user.password = generate_password_hash(
                request.form.get('password'))
            user.name = request.form.get('name')
            get_db().add(user)
            get_db().commit()
            user = get_db().query(User).filter_by(
                email=request.form.get('email')).one()
            login_session['user_id'] = user.id
        return redirect(bp_auth.home_url)
    else:
        # request.method != 'POST'
        state = ''.join(
            random.choice(string.ascii_uppercase + string.digits)
            for _ in range(32))
        login_session['state'] = state
        return render_template(
            'login.html',
            state=state,
            G_CLIENT_ID=G_CLIENT_ID,
            GH_CLIENT_ID=current_app.config['GITHUB_CLIENT_ID'])


# disable for production, used only for dev w/o internet connection
# @app.route('/login/<int:user_id>')
# def login_testing(user_id):
#     login_session['user_id'] = user_id
#     return redirect(url_for('home'))


@bp_auth.route('/login/github')
def login_github():
    # check random state string
    if request.args.get('state') != login_session['state']:
        response = make_response(json.dumps('Invalid state'), 401)
        response.headers['Content-Type'] = 'application/json'
        return response
    # get temporary access code
    code = request.args.get('code')
    if code is None:
        response = make_response(
            json.dumps("didn't get temporary code"), 401)
        response.headers['Content-Type'] = 'application/json'
        return response
    # exchange access code for access token
    token_url = 'https://github.com/login/oauth/access_token'
    token_params = {
        'client_id': current_app.config['GITHUB_CLIENT_ID'],
        'client_secret': current_app.config['GITHUB_CLIENT_SECRET'],
        'code': str(code),
    }
    token_headers = {
        'Accept': 'application/json',
        'content-type': 'application/json',
    }
    token_answer = requests.post(token_url,
                                 data=json.dumps(token_params),
                                 headers=token_headers)
    token_json = token_answer.json()
    access_token = token_json.get('access_token')
    if access_token is None:
        response = make_response(json.dumps('no access token'), 401)
        response.headers['Content-Type'] = 'application/json'
        return response
    info_url = 'https://api.github.com/user'
    info_params = {
        'access_token': access_token,
    }
    info_answer = requests.get(info_url, params=info_params)
    info_json = info_answer.json()
    # todo: error if name and email not present
    user_id = vh.get_create_user(info_json['name'], info_json['email'])
    login_session['user_id'] = user_id
    return redirect(bp_auth.home_url)


# todo: possible to remove csrf.exempt from google login endpoint?
@csrf.exempt
@bp_auth.route('/gconnect', methods=['POST'])
def gconnect():
    # check that request is from the login page
    if request.args.get('state') != login_session['state']:
        response = make_response(json.dumps('Invalid state'), 401)
        response.headers['Content-Type'] = 'application/json'
        return response
    # exchange code for access token
    code = request.data
    try:
        oauth_flow = flow_from_clientsecrets('client_secrets.json',
                                             scope='')
        oauth_flow.redirect_uri = 'postmessage'
        credentials = oauth_flow.step2_exchange(code)
    except FlowExchangeError as e:
        response = make_response(
            json.dumps('Failed to upgrade authorization code.'),
            401)
        response.headers['Content-Type'] = 'application/json'
        return response
    access_token = credentials.access_token
    # make certain that we have the correct access token
    url = ('https://www.googleapis.com/oauth2/v1/tokeninfo?'
           'access_token=%s' % access_token)
    h = httplib2.Http()
    res_headers, res_str = h.request(url, 'GET')
    result = json.loads(res_str)
    if ((result.get('error') is not None or
         res_headers['status'] != '200')):
        response = make_response(
            json.dumps('token info error'),
            500)
        response.headers['Content-Type'] = 'application/json'
        return response
    if result['user_id'] != credentials.id_token['sub']:
        response = make_response(
            json.dumps('token/user-id mismatch'), 401)
        response.headers['Content-Type'] = 'application/json'
        return response
    if result['issued_to'] != G_CLIENT_ID:
        response = make_response(
            json.dumps('token/client-id mismatch'), 401)
        print 'token/client-id mismatch'
        response.headers['Content-Type'] = 'application/json'
        return response
    # get google user info
    userinfo_url = 'https://www.googleapis.com/oauth2/v1/userinfo'
    params = {'access_token': access_token, 'alt': 'json'}
    answer = requests.get(userinfo_url, params=params)
    data = answer.json()
    # get or create user record
    user_id = vh.get_create_user(data['name'], data['email'])
    login_session['user_id'] = user_id
    return 'logged in'


@bp_auth.route('/logout')
def logout():
    if login_session.get('user_id'):
        login_session.pop('user_id')
    return redirect(bp_auth.home_url)
