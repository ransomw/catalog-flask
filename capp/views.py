from pdb import set_trace as st

import os
import random
import string
import json
from functools import wraps
import imghdr
import time

from werkzeug.security import generate_password_hash
from werkzeug.security import check_password_hash

from flask import render_template
from flask import session as login_session
from flask import request
from flask import make_response
from flask import redirect
from flask import url_for
from flask import jsonify
from flask import send_file
from flask import g

from sqlalchemy import asc
from sqlalchemy import desc
from sqlalchemy.orm.exc import NoResultFound
from sqlalchemy.exc import SQLAlchemyError

from oauth2client.client import flow_from_clientsecrets
from oauth2client.client import FlowExchangeError

import httplib2
import requests

from dict2xml import dict2xml

from models import User
from models import Category
from models import Item
from models import get_db

import view_helpers as vh

from capp import app
from capp import csrf

G_CLIENT_ID = json.loads(
    open('client_secrets.json', 'r').read())['web']['client_id']

NUM_RECENT_ITEMS = 9

# todo: currently have urls like Soccer%20Cleats, which is ugly

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in login_session:
            return redirect(url_for('login', next=request.url))
        return f(*args, **kwargs)
    return decorated_function


@app.route('/login', methods=['GET', 'POST'])
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
                return render_template(
                    'err.html', err_msg="bad password"), 401
        else:
            # request.form.get('sign-in') is None
            if request.form.get('sign-up') is None:
                err_msg = "must specify sign up or sign in"
                return render_template(
                    'err.html', err_msg=err_msg), 400
            if ((request.form.get('password') !=
                 request.form.get('password-confirm'))):
                err_msg = "passwords don't match"
                return render_template(
                    'err.html', err_msg=err_msg), 400
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
        return redirect(url_for('home'))
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
            GH_CLIENT_ID=app.config['GITHUB_CLIENT_ID'])


# disable for production, used only for dev w/o internet connection
# @app.route('/login/<int:user_id>')
# def login_testing(user_id):
#     login_session['user_id'] = user_id
#     return redirect(url_for('home'))


@app.route('/login/github')
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
        'client_id': app.config['GITHUB_CLIENT_ID'],
        'client_secret': app.config['GITHUB_CLIENT_SECRET'],
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
    return redirect(url_for('home'))


@csrf.exempt
@app.route('/gconnect', methods=['POST'])
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


@app.route('/logout')
def logout():
    if login_session.get('user_id'):
        login_session.pop('user_id')
    return redirect(url_for('home'))


@app.before_request
def before_request():
    g.user = None
    if 'user_id' in login_session:
        g.user = get_db().query(User).filter_by(
            id=login_session.get('user_id')).one()


@app.route('/')
def home():
    categories = get_db().query(Category).all()
    items = get_db().query(
        Item).order_by(desc(Item.last_update)).limit(NUM_RECENT_ITEMS)
    return render_template('home.html',
                           categories=categories,
                           items=items)


@app.route('/catalog/item/new', methods=['GET', 'POST'])
@login_required
def item_new():
    if request.method == 'POST':
        # store form data
        try:
            item = vh.item_from_form(Item(), request.form,
                                     user_id=g.user.id)
        except ValueError as e:
            # client-side validation should prevent this
            app.logger.exception(e)
            return render_template('err.html',
                                   err_msg="Database validation error")
        except SQLAlchemyError as e:
            app.logger.exception(e)
            # todo: reinitialize db connection if necessary
            return render_template('err.html',
                                   err_msg="Database error")
        # store image file
        file_storage_err = vh.store_item_pic(
            item, request.files['picture'])
        if file_storage_err is not None:
            # todo: what if item delete after failed pic storage fails?
            # using wtfform in item_add.html would simplify all this
            get_db().delete(item)
            return render_template(
                'err.html', err_msg=file_storage_err), 500
        return redirect(url_for('home'))
    else:
        categories = get_db().query(Category).all()
        return render_template('item_add.html',
                               categories=categories)


@app.route('/catalog/<string:item_title>/edit', methods=['GET', 'POST'])
@login_required
def item_edit(item_title):
    try:
        item = get_db().query(Item).filter_by(
            title=item_title).one()
    except NoResultFound:
        err_msg = "item '" + item_title + "' not found"
        return render_template(
            'err.html', err_msg=err_msg), 404
    if item.user is not None and item.user.id != g.user.id:
        err_msg = "user doesn't have edit permissions for this item"
        return render_template(
            'err.html', err_msg=err_msg), 404
    if request.method == 'POST':
        form = vh.get_item_form()(request.form, item)
        file_storage_err = vh.store_item_pic(
            item, request.files['picture'])
        if (not form.validate() or file_storage_err is not None):
            http_err_code = 500 if file_storage_err is not None else 400
            return (render_template('item_edit.html',
                                    form=form,
                                    file_err=file_storage_err),
                    http_err_code)
        form.populate_obj(item)
        try:
            get_db().add(item)
            get_db().commit()
            # todo: pic updated w/o updating item record
        except ValueError as e:
            # client-side validation should prevent this
            app.logger.exception(e)
            return render_template('err.html',
                                   err_msg="Database validation error")
        except SQLAlchemyError as e:
            app.logger.exception(e)
            # todo: reinitialize db connection if necessary
            return render_template('err.html',
                                   err_msg="Database error")
        return redirect(url_for('home'))
    else:
        form = vh.get_item_form()(obj=item)
        return render_template('item_edit.html',
                               form=form,
                               file_err=None)


@app.route('/catalog/<string:item_title>/delete',
           methods=['GET', 'POST'])
@login_required
def item_delete(item_title):
    try:
        item = get_db().query(Item).filter_by(
            title=item_title).one()
    except NoResultFound:
        err_msg = "item '" + item_title + "' not found"
        return render_template(
            'err.html', err_msg=err_msg), 404
    if item.user is not None and item.user.id != g.user.id:
        return redirect(url_for('home'))
    if request.method == 'POST':
        img_filepath = vh.get_item_image_filepath(item.id)
        # todo: error-handling, filesystem/db consistency story as w/ C&U
        if os.path.isfile(img_filepath):
            os.remove(img_filepath)
        get_db().delete(item)
        get_db().commit()
        return redirect(url_for('home'))
    else:
        return render_template('item_delete.html',
                               item=item)


@app.route('/catalog/<string:category_name>/items')
def items_list(category_name):
    try:
        category = get_db().query(Category).filter_by(
            name=category_name).one()
    except NoResultFound:
        err_msg = "category '" + category_name + "' not found"
        return render_template(
            'err.html', err_msg=err_msg), 404
    categories = get_db().query(Category).all()
    items = get_db().query(Item).filter_by(
        category_id=category.id).all()
    return render_template('items.html',
                           categories=categories,
                           category=category,
                           items=items)


@app.route('/catalog/<string:category_name>/<string:item_title>')
def item_detail(category_name, item_title):
    try:
        category = get_db().query(Category).filter_by(
            name=category_name).one()
    except NoResultFound:
        # return tuples automatically passed flask.make_response
        err_msg = "category '" + category_name + "' not found"
        return render_template(
            'err.html', err_msg=err_msg), 404
    item = get_db().query(Item).filter_by(
        category_id=category.id).filter_by(
            title=item_title).one()
    has_img = vh.get_item_image_info(item.id) is not None
    can_modify = (g.user is not None and
                  (item.user is None or item.user.id == g.user.id))
    return render_template('item.html',
                           item=item,
                           has_img=has_img,
                           can_modify=can_modify,
                           rand_q=time.time())


@app.route('/catalog/item/<int:item_id>/img')
def item_img(item_id):
    try:
        item = get_db().query(Item).filter_by(
            id=item_id).one()
    except NoResultFound:
        return json.dumps('Image not found'), 401
    img_info = vh.get_item_image_info(item.id)
    if img_info is None:
        app.logger.exception("got None for img_info")
        return json.dumps("programming or operation error"), 500
    # todo: edit out this '..' nonsense after tests for file uploading
    return send_file(os.path.join('..', img_info['path']),
                     mimetype='image/'+img_info['type'])


@app.route('/api/category')
def api_categories():
    categories = get_db().query(Category).all()
    return jsonify(Categories=[c.serialize for c in categories])


@app.route('/api/item')
def api_items():
    items = get_db().query(Item).all()
    return jsonify(Items=[i.serialize for i in items])


@app.route('/catalog.json')
def json_catalog():
    return jsonify(vh.serialize_catalog())


@app.route('/catalog.xml')
def xml_catalog():
    xml = dict2xml(vh.serialize_catalog(), wrap="Catalog")
    response = make_response(xml)
    response.headers['Content-Type'] = 'application/xml'
    return response
