import os
from ...definitions import ROOT_DIR


class Config(object):
    SECRET_KEY = os.getenv('SECRET_KEY') or '0198237uqijowdfsgahsdk7qew645bvn837drh487i3wd6nymbctyrngzmla378924vrmfudsikdj'
    SQLALCHEMY_DATABASE_URI = 'sqlite:///' + os.path.join(ROOT_DIR, 'db', 'manage.db')
    SQLALCHEMY_TRACK_MODIFICATIONS = False
