from flask import render_template, redirect, flash, url_for
from . import dash_app
from ...definitions import VERSION
from .. import datafetch
from .forms import LoginForm


@dash_app.route('/index')
@dash_app.route('/dashboard')
def dash_redirect():
    return redirect('/')


@dash_app.route('/')
def dashboard():
    alert_data = datafetch.get_alerts()
    alert_list = alert_data[0]
    alert_count = (alert_data[1], len(alert_list))
    factions = datafetch.get_tracked_factions()
    return render_template('index.html', page='Dashboard', version=VERSION, alerts=alert_list, alert_count=alert_count, factions=factions)


@dash_app.route('/faction')
@dash_app.route('/faction/<fac_id>')
def faction(fac_id=None):
    if fac_id is not None:
        faction_data = datafetch.get_faction(fac_id)
        template = render_template('faction.html', page='Factions', version=VERSION, faction=True, data=faction_data)
    else:
        factions = datafetch.get_all_factions()
        template = render_template('faction.html', page='Factions', version=VERSION, faction=False, data=factions)
    return template


@dash_app.route('/system')
@dash_app.route('/system/<sys_id>')
def system(sys_id=None):
    if sys_id is not None:
        system_data = datafetch.get_system(sys_id)
        template = render_template('system.html', page='Systems', version=VERSION, system=True, data=system_data)
    else:
        systems = datafetch.get_all_systems()
        template = render_template('system.html', page='Systems', version=VERSION, system=False, data=systems)
    return template


@dash_app.route('/manage')
def manage():
    return redirect(url_for('login'))


@dash_app.route('/manage/login', methods=['GET', 'POST'])
def login():
    form = LoginForm()
    if form.validate_on_submit():
        flash('Login requested for user {}, remember_me={}'.format(
            form.username.data, form.remember_me.data))
        return redirect(url_for('dashboard'))
    return render_template('login.html', title='Sign In', form=form)
