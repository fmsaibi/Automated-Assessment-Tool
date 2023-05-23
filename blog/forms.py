from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SubmitField, TextAreaField, SelectField, FormField, FieldList, BooleanField, validators
from wtforms.validators import DataRequired, EqualTo, ValidationError, Regexp, InputRequired
from blog.models import User, Module_list
from flask import flash
from flask_login import current_user

class RegistrationForm(FlaskForm):
  first_name = StringField('First Name',validators=[DataRequired()])
  last_name = StringField('Last Name',validators=[DataRequired()])
  email = StringField('Email',validators=[DataRequired()])
  access_type = SelectField('Access Type', validators=[DataRequired()])
  password = PasswordField('Password',validators=[DataRequired(),Regexp('^(?=.*\d)(?=.*[a-z])(?=.*[A-Z])(?=.*[@#$%^&+=])\S{8,}$',
                                      message='Passwords must contain at least \none uppercase letter,\
                                               \none lowercase letter, \none number, and \none special \
                                                character.')])
  register = SubmitField('Register')

  def validate_email(self, email):
    email = User.query.filter_by(email=email.data).first()
    if email is not None:
      raise ValidationError('Email already exist.')

  def __init__(self, *args, **kwargs):
    super(RegistrationForm, self).__init__(*args, **kwargs)
    if current_user.access_type == "admin":
      self.access_type.choices =  [('select', 'Select'),
                                   ('admin', 'Admin'), 
                                   ('developer', 'Devoloper'), 
                                   ('lecturer', 'Dummy Lecturer'), 
                                   ('student', 'Dummy Student')]
    else:
      self.access_type.choices =  [('select', 'Select'),
                                   ('lecturer', 'Dummy Lecturer'), 
                                   ('student', 'Dummy Student')]

  
# Login to AAT
class LoginForm(FlaskForm):
  email = StringField('Email',validators=[DataRequired()])
  password = PasswordField('Password',validators=[DataRequired()])
  login = SubmitField('Login')

# Logout from AAT
class LogoutForm(FlaskForm):
  logout = SubmitField('logout')

# Forget password
class ForgetPWForm(FlaskForm):
  email = StringField(label="Email", validators=[DataRequired()], render_kw={'placeholder': 'Email'})
  submit = SubmitField(label="Reset Password")

# Reset password
class ResetPWForm(FlaskForm):
  email = StringField(label="Email")
  password = PasswordField(label="New Password", validators=[DataRequired()], render_kw={'placeholder': 'Password'})
  confirm_password = PasswordField(label="Confirm Password", validators=[DataRequired()], render_kw={'placeholder': 'Confirm Password'})
  submit = SubmitField(label="Change Password")


class QuestionForm(FlaskForm):

  question = StringField(validators=[DataRequired()])
  category = SelectField(validators=[DataRequired()])
  module_code = SelectField(validators=[DataRequired()])
  points = StringField(validators=[DataRequired()])
  level = SelectField('Level', validators=[DataRequired()])
  save = SubmitField('Save')
  update = SubmitField('Update')

  def __init__(self, *args, **kwargs):
    super(QuestionForm, self).__init__(*args, **kwargs)
    self.category.choices = [('', ''), 
                             ('single', 'Single Choice'), 
                             ('multiple', 'Multiple Choice')]
    self.module_code.choices = [""] + self.get_module_choices()
    self.level.choices =  [('', ''),('1', 'Easy'), ('2', 'Medium'), ('3', 'Hard')]


  # function to get module code from databasse
  def get_module_choices(self):
    modules = Module_list.query.all()
    return [(module.module_code) for module in modules]

