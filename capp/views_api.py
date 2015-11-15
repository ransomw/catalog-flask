""" public-facing api """
from pdb import set_trace as st

# external libs
from flask import Blueprint
from flask import jsonify
from flask import make_response

from dict2xml import dict2xml

# local modules
import view_helpers as vh

bp_api = Blueprint('api', __name__,
                    template_folder='templates')


# todo: query strings for json and xml responses
# todo: generic view to handle both json and xml responses
@bp_api.route('/catalog.json')
def json_catalog():
    return jsonify(vh.serialize_catalog())


@bp_api.route('/catalog.xml')
def xml_catalog():
    xml = dict2xml(vh.serialize_catalog(), wrap="Catalog")
    response = make_response(xml)
    response.headers['Content-Type'] = 'application/xml'
    return response
