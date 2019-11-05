from flask import Flask
from .config import Config
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_login import LoginManager
from datetime import datetime, date

dash_app = Flask(__name__)
dash_app.config.from_object(Config)
db = SQLAlchemy(dash_app)
migrate = Migrate(dash_app, db)
login = LoginManager(dash_app)
login.login_view = 'login'


def format_datetime(timestamp):
    return datetime.strftime(timestamp, '%d/%b/%y')


def format_date(timestamp):
    return date.strftime(timestamp, '%d/%b/%y')


dash_app.jinja_env.filters['datetime'] = format_datetime
dash_app.jinja_env.filters['date'] = format_date

from . import routes, models, errors
