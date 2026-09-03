from flask import Blueprint

governance_bp = Blueprint('governance', __name__, url_prefix='/governance')

from . import routes
