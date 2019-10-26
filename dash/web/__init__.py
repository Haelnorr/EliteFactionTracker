from flask import Flask

dash_app = Flask(__name__)

from . import routes
