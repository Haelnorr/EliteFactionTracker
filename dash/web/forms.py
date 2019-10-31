from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, BooleanField, SubmitField, SelectField
from wtforms.validators import DataRequired, EqualTo, ValidationError
from .models import User


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
