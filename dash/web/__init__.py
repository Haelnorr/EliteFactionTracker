from flask import Flask
from .config import Config
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_login import LoginManager

dash_app = Flask(__name__)
dash_app.config.from_object(Config)
db = SQLAlchemy(dash_app)
migrate = Migrate(dash_app, db)
login = LoginManager(dash_app)
login.login_view = 'login'

from . import routes, models, errors
