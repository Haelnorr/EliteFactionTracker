from flask import render_template
from dash.web import dash_app
from definitions import VERSION
from dash import datafetch


@dash_app.route('/')
@dash_app.route('/index')
@dash_app.route('/dashboard')
def index():
    alerts = datafetch.get_alerts()
    return render_template('index.html', page='Dashboard', version=VERSION, alerts=alerts)
