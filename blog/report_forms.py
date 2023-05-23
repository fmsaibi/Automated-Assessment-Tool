from flask_ckeditor import CKEditorField
from flask_wtf import FlaskForm
from wtforms import SubmitField, IntegerField
from wtforms.validators import DataRequired, InputRequired


class FeedbackForm(FlaskForm):
    feedback = CKEditorField('Feedback', validators=[DataRequired(message='The body of the feedback must not be empty')])
    submit = SubmitField('Publish Feedback')


class MarkForm(FlaskForm):
    marks = IntegerField('Test Score', validators=[InputRequired(message='A new mark is required')])
    reason = CKEditorField('Reason for change', validators=[InputRequired(message='The reason for change must be provided')], render_kw={"placeholder": "Please provide a reason for the change."})
    submit = SubmitField('Publish Mark')