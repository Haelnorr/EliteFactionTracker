from . import log
log.start('dashboard')
from dotenv import load_dotenv
from .definitions import ROOT_DIR
import os
load_dotenv(os.path.join(ROOT_DIR, '.env'))
from .dash.web import dash_app as app
from .dash.web import db
from .dash.web.models import User, Notice
from sqlalchemy.exc import OperationalError

try:
    __users = User.query.all()
    if len(__users) == 0:
        # noinspection PyArgumentList
        superuser = User(username='admin', permission='Administrator', reset_pass=True)
        superuser.set_password('edftadmin')
        db.session.add(superuser)
        db.session.commit()
except OperationalError:
    pass


if __name__ == '__main__':
    app.run(host='0.0.0.0')


@app.shell_context_processor
def make_shell_context():
    return {'db': db, 'User': User, 'Notice': Notice}
