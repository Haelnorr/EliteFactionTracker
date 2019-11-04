from . import db, login
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime


class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(64), index=True, unique=True)
    password_hash = db.Column(db.String(128))
    reset_pass = db.Column(db.Boolean)
    permission = db.Column(db.String(15))

    def __repr__(self):
        return '<User {}; {}>'.format(self.username, self.permission)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)


@login.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))


class Notice(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(128))
    message = db.Column(db.String(512))
    priority = db.Column(db.Integer, index=True)
    timestamp = db.Column(db.DateTime, index=True, default=datetime.utcnow)
    expiry = db.Column(db.DateTime, index=True, default=None)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
