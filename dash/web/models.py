from . import db


class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(64), index=True, unique=True)
    password_hash = db.Column(db.String(128))
    reset_pass = db.Column(db.Boolean)
    permission = db.Column(db.String(15))

    def __repr__(self):
        return '<User {}; {}>'.format(self.username, self.permission)
