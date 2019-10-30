from flask import Flask
from .config import Config
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate

dash_app = Flask(__name__)
dash_app.config.from_object(Config)
db = SQLAlchemy(dash_app)
migrate = Migrate(dash_app, db)

from . import routes, models
