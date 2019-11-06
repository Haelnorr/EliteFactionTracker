from flask import render_template, redirect, flash, url_for, request
from . import dash_app, db, forms
from ...definitions import VERSION
from .. import datafetch
from flask_login import current_user, login_user, logout_user, login_required
from .models import User, Notice
from werkzeug.urls import url_parse
from datetime import time, datetime
from sqlalchemy import or_


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
    notice_list = Notice.query.filter(or_(Notice.expiry > datetime.utcnow(), None == Notice.expiry)).filter(Notice.priority == 1)
    return render_template('index.html', page='Dashboard', version=VERSION, alerts=alert_list, alert_count=alert_count, factions=factions, notices=notice_list)


@dash_app.route('/about')
def about():
    return render_template('about.html', page='About', version=VERSION)


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
    return redirect(url_for('manage_notices'))


@dash_app.route('/manage/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('manage'))
    form = forms.LoginForm()
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
    form = forms.ChangePassword()
    if form.validate_on_submit():
        user = User.query.filter_by(username=current_user.username).first()
        if user is None:
            flash('Some error occurred, try again and if the problem persists contact the system administrator')
            return redirect(url_for('change_pass'))
        user.set_password(form.password.data)
        user.reset_pass = False
        db.session.add(user)
        db.session.commit()
        return redirect(url_for('manage'))
    return render_template('change_pass.html', page='Change Password', version=VERSION, form=form)


@dash_app.route('/manage/users')
@login_required
def users():
    if current_user.reset_pass is True:
        return redirect(url_for('change_pass'))
    user_list = User.query.with_entities(User.username, User.permission, User.id).order_by(User.permission)
    return render_template('users.html', page='Users', version=VERSION, users=user_list)


@dash_app.route('/manage/users/edit')
@dash_app.route('/manage/users/edit/<user_id>', methods=['GET', 'POST'])
@login_required
def user_edit(user_id=None):
    if current_user.reset_pass is True:
        return redirect(url_for('change_pass'))
    if user_id is None or user_id == '1' or not current_user.permission == 'Administrator':
        return redirect(url_for('users'))
    user = User.query.filter_by(id=user_id).first()
    if user is None:
        flash('Some error occurred, try again and if the problem persists contact the system administrator')
        return redirect(url_for('users'))
    if user.permission == 'Administrator' and not current_user.id == 1:
        return redirect(url_for('users'))
    form = forms.UserEdit(permission=user.permission)
    if form.validate_on_submit():
        user.permission = form.permission.data
        if form.reset_pass.data is True:
            user.set_password(form.new_pass.data)
            user.reset_pass = True
        db.session.add(user)
        db.session.commit()
        return redirect(url_for('users'))
    return render_template('users_edit.html', page='Edit User', version=VERSION, user=user, current_user=current_user, form=form)


@dash_app.route('/manage/users/add', methods=['GET', 'POST'])
@login_required
def add_user():
    if current_user.reset_pass is True:
        return redirect(url_for('change_pass'))
    if not current_user.permission == 'Administrator':
        return redirect(url_for('users'))
    form = forms.NewUser()
    if form.validate_on_submit():
        # noinspection PyArgumentList
        user = User(username=form.username.data, permission=form.permission.data, reset_pass=True)
        user.set_password(form.password.data)
        db.session.add(user)
        db.session.commit()
        return redirect(url_for('users'))
    return render_template('users_new.html', page='New User', version=VERSION, form=form)


@dash_app.route('/manage/users/delete')
@dash_app.route('/manage/users/delete/<user_id>', methods=['GET', 'POST'])
@login_required
def delete_user(user_id=None):
    if current_user.reset_pass is True:
        return redirect(url_for('change_pass'))
    if not current_user.permission == 'Administrator':
        return redirect(url_for('users'))
    user = User.query.filter_by(id=user_id).first()
    if user is None:
        return redirect(url_for('users'))
    if user.id == 1:
        return redirect(url_for('users'))
    if user.permission == 'Administrator' and not current_user.id == 1:
        return redirect(url_for('users'))
    form = forms.DeleteUser()
    if form.validate_on_submit():
        if form.confirm.data is True:
            User.query.filter_by(id=user.id).delete()
            db.session.commit()
            return redirect(url_for('users'))
        else:
            flash('Check the box to confirm deletion')
    return render_template('users_delete.html', page='Delete User', version=VERSION, form=form, user=user)


@dash_app.route('/manage/notices')
@login_required
def manage_notices():
    if current_user.reset_pass is True:
        return redirect(url_for('change_pass'))
    notices = Notice.query.order_by(Notice.priority)
    return render_template('notices_manage.html', page='Manage Notices', version=VERSION, notices=notices)


@dash_app.route('/manage/notices/new', methods=['GET', 'POST'])
@login_required
def new_notice():
    if current_user.reset_pass is True:
        return redirect(url_for('change_pass'))
    form = forms.NewNotice()
    if form.validate_on_submit():
        if form.expiry_enable.data is True:
            expiry = datetime.combine(form.expiry.data, time(12))
        else:
            expiry = None
        notice = Notice(title=form.post_title.data, priority=form.priority.data, expiry=expiry, message=form.message.data, author=current_user)
        db.session.add(notice)
        db.session.commit()
        return redirect(url_for('manage_notices'))
    return render_template('notices_new.html', page='New Notice', version=VERSION, form=form)


@dash_app.route('/manage/notices/edit')
@dash_app.route('/manage/notices/edit/<notice_id>', methods=['GET', 'POST'])
@login_required
def edit_notice(notice_id=None):
    if current_user.reset_pass is True:
        return redirect(url_for('change_pass'))
    if notice_id is None:
        return redirect(url_for('manage_notices'))
    notice = Notice.query.filter_by(id=notice_id).first()
    if notice is None:
        return redirect(url_for('manage_notices'))
    if not current_user.id == notice.author.id:
        return redirect(url_for('manage_notices'))
    if notice.expiry is None:
        form = forms.EditNotice(post_title=notice.title, expiry_enable=False, priority=notice.priority, message=notice.message)
    else:
        expiry = notice.expiry.date()
        form = forms.EditNotice(post_title=notice.title, expiry_enable=True, priority=notice.priority, expiry=expiry, message=notice.message)

    if form.validate_on_submit():
        if form.expiry_enable.data is True:
            expiry = datetime.combine(form.expiry.data, time(12))
        else:
            expiry = None
        notice.title = form.post_title.data
        notice.priority = form.priority.data
        notice.expiry = expiry
        notice.message = form.message.data
        notice.timestamp = datetime.utcnow()
        db.session.add(notice)
        db.session.commit()
        return redirect(url_for('manage_notices'))
    return render_template('notices_edit.html', page='Edit Notice', version=VERSION, form=form)


@dash_app.route('/manage/notices/delete')
@dash_app.route('/manage/notices/delete/<notice_id>', methods=['GET', 'POST'])
@login_required
def delete_notice(notice_id=None):
    if current_user.reset_pass is True:
        return redirect(url_for('change_pass'))
    if notice_id is None:
        return redirect(url_for('manage_notices'))
    notice = Notice.query.filter_by(id=notice_id).first()
    if notice is None:
        return redirect(url_for('manage_notices'))
    if not current_user.permission == 'Administrator' and not current_user.id == notice.author.id:
        return redirect(url_for('manage_notices'))
    form = forms.DeleteNotice()
    if form.validate_on_submit():
        if form.confirm.data is True:
            Notice.query.filter_by(id=notice.id).delete()
            db.session.commit()
            return redirect(url_for('manage_notices'))
        else:
            flash('Check the box to confirm deletion')
    return render_template('notices_delete.html', page='Delete Notice', version=VERSION, form=form, notice=notice)


@dash_app.route('/notices')
def notices():
    notice_list = Notice.query.filter(or_(Notice.expiry > datetime.utcnow(), None == Notice.expiry)).order_by(Notice.priority)
    return render_template('notices.html', page='Notices', version=VERSION, notices=notice_list)
