from flask import Flask
from .config import Config

dash_app = Flask(__name__)
dash_app.config.from_object(Config)

from . import routes
