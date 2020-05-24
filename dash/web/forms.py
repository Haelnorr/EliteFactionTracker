from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, BooleanField, SubmitField, SelectField, TextAreaField
from wtforms.fields.html5 import DateField
from wtforms.validators import DataRequired, EqualTo, ValidationError
from .models import User
from ... import database


class LoginForm(FlaskForm):
    username = StringField('Username', validators=[DataRequired()])
    password = PasswordField('Password', validators=[DataRequired()])
    remember_me = BooleanField('Remember Me')
    submit = SubmitField('Sign In')


class ChangePassword(FlaskForm):
    password = PasswordField('Password', validators=[DataRequired()])
    password2 = PasswordField('Confirm Password', validators=[DataRequired(), EqualTo('password')])
    submit = SubmitField('Change Password')


class UserEdit(FlaskForm):
    __choices = [
        ('Administrator', 'Administrator'),
        ('Manager', 'Manager')
    ]
    permission = SelectField('Permission', choices=__choices, default=None)
    reset_pass = BooleanField('Reset password')
    new_pass = StringField('New password')
    submit = SubmitField('Save changes')


class NewUser(FlaskForm):
    __choices = [
        ('Administrator', 'Administrator'),
        ('Manager', 'Manager')
    ]
    username = StringField('Username', validators=[DataRequired()])
    password = StringField('Password', validators=[DataRequired()])
    permission = SelectField('Permission', choices=__choices, default='Manager')
    submit = SubmitField('Add user')

    def validate_username(self, username):
        user = User.query.filter_by(username=self.username.data).first()
        if user is not None:
            raise ValidationError('Please use a different username.')


class DeleteUser(FlaskForm):
    confirm = BooleanField('Confirm')
    submit = SubmitField('Delete User')

    def validate_confirm(self, confirm):
        if self.confirm.data is False:
            raise ValidationError('Check the box to confirm deletion.')


class NewNotice(FlaskForm):
    __choices = [
        (1, 'High'),
        (2, 'Medium'),
        (3, 'Low')
    ]
    post_title = StringField('Title', validators=[DataRequired()])
    priority = SelectField('Priority', coerce=int, choices=__choices, default=3)
    expiry_enable = BooleanField('Set to expire')
    expiry = DateField('Expiry', format='%Y-%m-%d')
    message = TextAreaField('Message', validators=[DataRequired()])
    submit = SubmitField('Create Notice')


class EditNotice(FlaskForm):
    __choices = [
        (1, 'High'),
        (2, 'Medium'),
        (3, 'Low')
    ]
    post_title = StringField('Title', validators=[DataRequired()])
    priority = SelectField('Priority', coerce=int, choices=__choices, default=3)
    expiry_enable = BooleanField('Set to expire')
    expiry = DateField('Expiry', format='%Y-%m-%d')
    message = TextAreaField('Message', validators=[DataRequired()])
    submit = SubmitField('Edit Notice')


class DeleteNotice(FlaskForm):
    confirm = BooleanField('Confirm')
    submit = SubmitField('Delete Notice')

    def validate_confirm(self, confirm):
        if self.confirm.data is False:
            raise ValidationError('Check the box to confirm deletion.')


class NewSystem(FlaskForm):
    systemname = StringField('System Name', validators=[DataRequired()])
    submit = SubmitField('Track System')

    def validate_systemname(self, systemname):
        conn = database.connect()
        system = database.fetch_system(conn, systemname.data)
        if system is not None:
            raise ValidationError('System is already in the database.')


class ConfirmNewSystem(FlaskForm):
    submit = SubmitField('Confirm')

