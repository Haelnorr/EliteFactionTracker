from . import log
log.start('dashboard')
from .dash.web import dash_app as app
from .dash.web import db
from .dash.web.models import User, Notice

if __name__ == '__main__':
    app.run(host='0.0.0.0')


@app.shell_context_processor
def make_shell_context():
    return {'db': db, 'User': User, 'Notice': Notice}
