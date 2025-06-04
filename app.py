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

# Set database environment variables
DB_HOST = os.getenv('DB_HOST')
DB_PORT = os.getenv('DB_PORT')
DB_NAME = os.getenv('DB_NAME')
DB_USER = os.getenv('DB_USER')
DB_PASSWORD = os.getenv('DB_PASSWORD')

# create the url
DATABASE_URL = f"postgresql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"
app.config['SQLALCHEMY_DATABASE_URI'] = DATABASE_URL

db.init_app(app)
migrate = Migrate(app, db)

# connect the postgres db
try:
    conn = psycopg2.connect(DATABASE_URL, sslmode='disable')
except psycopg2.Error as e:
    raise RuntimeError(f"Failed to connect to the database: {str(e)}") from e

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
    app.debug = True
    app.run(host="0.0.0.0", port=80)