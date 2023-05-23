from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from flask_bootstrap import Bootstrap
from decouple import config


app = Flask(__name__)

#Bootstrap 
Bootstrap(app)

app.config['SECRET_KEY'] = config('SECRET_KEY')
# suppress SQLAlchemy warning
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
#DB Connection
app.config['SQLALCHEMY_DATABASE_URI'] = config('DATABASE_URL', 'something.ac.uk')
#Admin email
app.config['MAIL_USERNAME'] = config('MAIL', 'mytable4@gmail.com')



#DB
db = SQLAlchemy(app)

with app.app_context():
    db.create_all()

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'
login_manager.refresh_view = 'login'

from blog import routes
from blog import reports_routes
