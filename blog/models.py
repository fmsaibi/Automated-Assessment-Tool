from datetime import datetime
from blog import db,app, login_manager
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from blog import app
from time import time
import jwt

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    first_name = db.Column(db.String(200), nullable=False)
    last_name = db.Column(db.String(200), nullable=False)
    access_type = db.Column(db.Enum('admin', 'developer', 'lecturer', 'student'), nullable=False)
    hashed_password = db.Column(db.String(128))
    email = db.Column(db.String(120), nullable=False, unique=True)
    created_date = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    initiator = db.Column(db.Integer, nullable=False)

    # adated from Grinberg(2014, 2018)
    @property
    def password(self):
        raise AttributeError('Password is not readable.')

    @password.setter
    def password(self, password):
        self.hash_password = generate_password_hash(password)

    def verify_password(self, password):
        return check_password_hash(self.hashed_password, password)

    def get_token(self, expire_in=3600):
        token = jwt.encode({'encoded': self.id, 'exp': time() + expire_in}, app.config['SECRET_KEY'], algorithm='HS256')
        return token

    @staticmethod
    def verify_token(token):
        try:
            user_id = jwt.decode(token, app.config['SECRET_KEY'], algorithms=['HS256'])['encoded']
        except:
            return None
        return User.query.get(user_id)

    @login_manager.user_loader
    def load_user(user_id):
        return User.query.get(int(user_id))

    def to_dict(self):
        return {
            'name': self.first_name + " " + self.last_name,
            'id': self.id,
            'email': self.email
        }
#
#
@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))


class Assessment(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    module_code = db.Column(db.String(200), nullable=False)
    question_id_score = db.Column(db.JSON, nullable=False)
    is_formative = db.Column(db.Boolean, default=True)
    created_date = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    start_date = db.Column(db.DateTime, nullable=False, default="0000-00-00 00:00:00")
    end_date = db.Column(db.DateTime, nullable=False, default="9999-12-31 23:59:59")
    publish_report_date = db.Column(db.DateTime, default=datetime.utcnow)




class Assessment_view(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    module_code = db.Column(db.String(200), nullable=False)
    question_id_score = db.Column(db.JSON, nullable=False)
    is_formative = db.Column(db.Boolean, default=True)
    created_date = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    start_date = db.Column(db.DateTime, nullable=False, default="0000-00-00 00:00:00")
    end_date = db.Column(db.DateTime, nullable=False, default="9999-12-31 23:59:59")
    publish_report_date = db.Column(db.DateTime, default=datetime.utcnow)
    assessment_name = db.Column(db.String(100))


class Attempts(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    uid = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    assessment_id = db.Column(db.Integer, db.ForeignKey('assessment.id'), nullable=False)
    marks = db.Column(db.Integer)
    feedback = db.Column(db.Text)
    student_answers = db.Column(db.JSON)
    module_code = db.Column(db.String(200), db.ForeignKey('module_list.module_code'), nullable=False)
    created_date = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    mark_change_reason = db.Column(db.Text)
    lecturer_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    time_of_change = db.Column(db.DateTime, onupdate=datetime.utcnow())


class Question(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    module_code = db.Column(db.String(50), db.ForeignKey('module_list.module_code'), nullable=False)
    question = db.Column(db.Text, nullable=False)
    tags = db.Column(db.Text, nullable=True)
    answers = db.Column(db.JSON, nullable=False)
    created_date = db.Column(db.TIMESTAMP, nullable=False, default=db.func.current_timestamp())
    modify_date = db.Column(db.TIMESTAMP, server_default=db.func.current_timestamp(),
                            onupdate=db.func.current_timestamp(), nullable=True)
    initiator = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)
    category = db.Column(db.Enum('single', 'multiple'), nullable=False)
    tags = db.Column(db.Text)
    points = db.Column(db.Integer)
    level = db.Column(db.Enum('1', '2', '3'), default=1)


class Module_list(db.Model):
    module_code = db.Column(db.String(50), primary_key=True)
    module_name = db.Column(db.String(50), nullable=False)
    module_credit = db.Column(db.Integer, nullable=False)
    created_date = db.Column(db.TIMESTAMP, nullable=False, default=db.func.current_timestamp())


class Module(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    uid = db.Column(db.Integer, db.ForeignKey('user.id'))
    module_code = db.Column(db.String(50), db.ForeignKey('module_list.module_code'))


class Comments(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    uid = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    text = db.Column(db.Text, nullable=False, unique=False)
    parent_comment_id = db.Column(db.Integer, db.ForeignKey('comment.id'), nullable=False)
    question_id = db.Column(db.Integer, db.ForeignKey('question.id'), nullable=False)


class Contact(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    uid = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    message = db.Column(db.Text, nullable=False, unique=False)
    created_date = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)

class Assessment_list(db.Model):
  id = db.Column(db.Integer,primary_key=True)
  list = db.Column(db.ARRAY(db.String(50)))
