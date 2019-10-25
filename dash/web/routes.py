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


@dash_app.route('/faction/<fac_id>')
def faction(fac_id):
    faction_data = datafetch.get_faction(fac_id)
    faction_name = faction_data[0]
    systems = faction_data[1]

    return render_template('faction.html', page='Faction', version=VERSION, faction=faction_name, systems=systems)


@dash_app.route('/system/<sys_id>')
def system(sys_id):
    system_data = datafetch.get_system(sys_id)
    return render_template('system.html', page='System', version=VERSION, system=system_data)
