import os
import psycopg2
from flask import Flask
from flask_migrate import Migrate
from flask_login import LoginManager
from extensions import db

###
# APP CONFIG
###

# initialise the flask app
app = Flask(__name__)
app.config['SECRET_KEY'] = os.getenv(
    'DJ_REQUEST_SECRET_KEY', 'default_secret_key')
app.config['DEBUG'] = True

# set db env variables for
DATABASE_URL = os.getenv('DATABASE_URL')
app.config['SQLALCHEMY_DATABASE_URI'] = DATABASE_URL.replace(
    "postgres://", "postgresql://", 1)

db.init_app(app)
migrate = Migrate(app, db)

# connect the postgres db
conn = psycopg2.connect(DATABASE_URL, sslmode='require')

# setting up prerequisites for the login manager
login_manager = LoginManager(app)
login_manager.login_view = 'login'


@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# Data Models
from models import User, Track, Playlist

# Routes
from routes import *

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True)
