from flask import render_template, redirect, flash, url_for, request
from . import dash_app, db
from ...definitions import VERSION
from .. import datafetch
from .forms import LoginForm, ChangePassword
from flask_login import current_user, login_user, logout_user, login_required
from .models import User
from werkzeug.urls import url_parse


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
@login_required
def manage():
    if current_user.reset_pass is True:
        return redirect(url_for('change_pass'))
    return redirect(url_for('dashboard')) # temp while manage under construction


@dash_app.route('/manage/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('manage'))
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(username=form.username.data).first()
        if user is None or not user.check_password(form.password.data):
            flash('Invalid username or password')
            return redirect(url_for('login'))
        login_user(user, remember=form.remember_me.data)
        next_page = request.args.get('next')
        if not next_page or url_parse(next_page).netloc != '':
            next_page = url_for('manage')
        return redirect(next_page)
    return render_template('login.html', page='Login', version=VERSION, form=form)


@dash_app.route('/manage/logout')
def logout():
    logout_user()
    return redirect(url_for('dashboard'))


@dash_app.route('/manage/change_pass', methods=['GET', 'POST'])
@login_required
def change_pass():
    form = ChangePassword()
    if form.validate_on_submit():
        user = User.query.filter_by(username=current_user.username).first()
        if user is None:
            flash('Some error occurred, try again and if the problem persists contact the administrator')
            return redirect(url_for('change_pass'))
        user.set_password(form.password.data)
        user.reset_pass = False
        db.session.add(user)
        db.session.commit()
        return redirect(url_for('manage'))
    return render_template('change_pass.html', page='Change Password', version=VERSION, form=form)
