import os
from ...definitions import ROOT_DIR


class Config(object):
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'you-will-never-guess'
    SQLALCHEMY_DATABASE_URI = 'sqlite:///' + os.path.join(ROOT_DIR, 'db', 'manage.db')
    SQLALCHEMY_TRACK_MODIFICATIONS = False
