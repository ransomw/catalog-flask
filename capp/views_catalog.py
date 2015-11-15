"""
catalog application views
"""

from pdb import set_trace as st

# python standard library

import os
import time
import json

# external libs

from flask import jsonify
from flask import send_file
from flask import g
from flask import render_template
from flask import redirect
from flask import url_for
from flask import redirect
from flask import Blueprint
from flask import current_app
from flask import request

# from sqlalchemy import asc
from sqlalchemy import desc
from sqlalchemy.orm.exc import NoResultFound
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm.exc import NoResultFound


# local modules

from models import Category
from models import Item
from models import get_db

import view_helpers as vh

from views_auth import login_required

NUM_RECENT_ITEMS = 9

# todo: currently have urls like Soccer%20Cleats, which is ugly

bp_catalog = Blueprint('catalog', __name__,
                       template_folder='templates')


@bp_catalog.route('/')
def home():
    categories = get_db().query(Category).all()
    items = get_db().query(
        Item).order_by(desc(Item.last_update)).limit(NUM_RECENT_ITEMS)
    return render_template('home.html',
                           categories=categories,
                           items=items)


@bp_catalog.route('/catalog/item/new', methods=['GET', 'POST'])
@login_required
def item_new():
    if request.method == 'POST':
        # store form data
        try:
            item = vh.item_from_form(Item(), request.form,
                                     user_id=g.user.id)
        except ValueError as e:
            # client-side validation should prevent this
            current_app.logger.exception(e)
            return render_template('err.html',
                                   err_msg="Database validation error")
        except SQLAlchemyError as e:
            current_app.logger.exception(e)
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
        return redirect(url_for('.home'))
    else:
        categories = get_db().query(Category).all()
        return render_template('item_add.html',
                               categories=categories)


@bp_catalog.route('/catalog/<string:item_title>/edit',
                  methods=['GET', 'POST'])
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
            current_app.logger.exception(e)
            return render_template('err.html',
                                   err_msg="Database validation error")
        except SQLAlchemyError as e:
            current_app.logger.exception(e)
            # todo: reinitialize db connection if necessary
            return render_template('err.html',
                                   err_msg="Database error")
        return redirect(url_for('.home'))
    else:
        form = vh.get_item_form()(obj=item)
        return render_template('item_edit.html',
                               form=form,
                               file_err=None)


@bp_catalog.route('/catalog/<string:item_title>/delete',
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
        return redirect(url_for('.home'))
    if request.method == 'POST':
        img_filepath = vh.get_item_image_filepath(item.id)
        # todo: error-handling, filesystem/db consistency story as w/ C&U
        if os.path.isfile(img_filepath):
            os.remove(img_filepath)
        get_db().delete(item)
        get_db().commit()
        return redirect(url_for('.home'))
    else:
        return render_template('item_delete.html',
                               item=item)


@bp_catalog.route('/catalog/<string:category_name>/items')
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


@bp_catalog.route('/catalog/<string:category_name>/<string:item_title>')
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


@bp_catalog.route('/catalog/item/<int:item_id>/img')
def item_img(item_id):
    try:
        item = get_db().query(Item).filter_by(
            id=item_id).one()
    except NoResultFound:
        return json.dumps('Image not found'), 401
    img_info = vh.get_item_image_info(item.id)
    if img_info is None:
        current_app.logger.exception("got None for img_info")
        return json.dumps("programming or operation error"), 500
    # todo: edit out this '..' nonsense after tests for file uploading
    return send_file(os.path.join('..', img_info['path']),
                     mimetype='image/'+img_info['type'])


@bp_catalog.route('/api/category')
def api_categories():
    categories = get_db().query(Category).all()
    return jsonify(Categories=[c.serialize for c in categories])


@bp_catalog.route('/api/item')
def api_items():
    items = get_db().query(Item).all()
    return jsonify(Items=[i.serialize for i in items])
