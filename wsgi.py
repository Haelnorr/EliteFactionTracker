import log
log.start('dashboard')
from dash.web import dash_app as app

if __name__ == '__main__':
    app.run(host='0.0.0.0')
