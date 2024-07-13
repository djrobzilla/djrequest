import os
import logging
from flask import Flask, render_template, request, g, redirect, url_for, flash as original_flash
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from urllib.parse import urlparse
from datetime import datetime
from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, BooleanField, SubmitField
from wtforms.validators import DataRequired, EqualTo, ValidationError
import user_agents

# set up logging
logging.basicConfig(filename='app.log', level=logging.INFO,
                    format='%(asctime)s - %(levelname)s - %(message)s')

app = Flask(__name__)
app.config['SECRET_KEY'] = os.getenv(
    'DJ_REQUEST_SECRET_KEY', 'default_secret_key')
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///djrequests.db'
db = SQLAlchemy(app)
migrate = Migrate(app, db)

# setting up prerequisites for the login manager
login_manager = LoginManager(app)
login_manager.login_view = 'login'


@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# saving request_loader function here in case its needed later
# @login_manager.request_loader
# def load_user_from_request(request):
#     # Load user from a token in the request headers
#     token = request.headers.get('Authorization')
#     if token:
#         user_id = verify_token(token)  # Implement token verification
#         if user_id:
#             return User.query.get(int(user_id))
#     return None

# Data Models


class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), index=True,
                         unique=True, nullable=False)
    password_hash = db.Column(db.String(120), nullable=False)
    is_admin = db.Column(db.Boolean, default=False)
    tracks = db.relationship('Track', backref='user',
                             lazy=True, foreign_keys='Track.user_id')

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)


class Track(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    artist = db.Column(db.String(200), nullable=False)
    submitted_by = db.Column(db.Integer, db.ForeignKey('user.id'))
    submitted_at = db.Column(db.DateTime, default=datetime.utcnow)
    played_at = db.Column(db.DateTime)
    upvotes = db.Column(db.Integer, default=0)
    playlist_id = db.Column(db.Integer, db.ForeignKey('playlist.id'))
    user_id = db.Column(db.String(80), db.ForeignKey(
        'user.id'), nullable=True)


class Playlist(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    ended_at = db.Column(db.DateTime)
    tracks = db.relationship('Track', backref='playlist', lazy=True)

# login classes


class LoginForm(FlaskForm):
    username = StringField('Username', validators=[DataRequired()])
    password = PasswordField('Password', validators=[DataRequired()])
    remember_me = BooleanField('Remember Me')
    submit = SubmitField('Sign In')


class RegistrationForm(FlaskForm):
    username = StringField('Username', validators=[DataRequired()])
    password = PasswordField('Password', validators=[DataRequired()])
    password2 = PasswordField('Repeat Password', validators=[
                              DataRequired(), EqualTo('password')])
    submit = SubmitField('Register')

    def validate_username(self, username):
        user = User.query.filter_by(username=username.data).first()
        if user is not None:
            raise ValidationError('Please use a different username.')

#  custom flash function, to automatically log flash messages
#  without the need for an additional function


# custom flash class
class FlashLogger:
    def __init__(self, original_flash):
        self.original_flash = original_flash

    def __call__(self, message, category=''):
        logging.info(
            f'Flash Message - Category: {category}, Message: {message}')
        self.original_flash(message, category)


# Instantiate the custom flash logger
flash = FlashLogger(original_flash)

# Routes


@app.before_request
def detect_device():
    user_agent = user_agents.parse(request.headers.get('User-Agent'))
    g.is_mobile = user_agent.is_mobile


@app.route('/')
def index():
    user_agent = user_agents.parse(request.headers.get('User-Agent'))
    is_mobile = user_agent.is_mobile
    current_playlist = Playlist.query.filter_by(ended_at=None).first()
    if not current_playlist:
        current_playlist = Playlist()
        db.session.add(current_playlist)
        db.session.commit()
    tracks = Track.query.filter_by(
        playlist_id=current_playlist.id).order_by(Track.upvotes.desc()).all()
    return render_template('index.html', title='Current Requests', tracks=tracks, is_mobile=is_mobile)


@app.route('/request', methods=['POST'])
def request_track():
    title = request.form['title']
    artist = request.form['artist']
    user_id = current_user.id if current_user.is_authenticated else None
    current_playlist = Playlist.query.filter_by(ended_at=None).first()
    track = Track(title=title, artist=artist,
                  playlist_id=current_playlist.id, user_id=user_id)
    if current_user.is_authenticated:
        track.submitted_by = current_user.id
    db.session.add(track)
    db.session.commit()
    flash(f'Track requested successfully by {user_id}!', 'success')
    return redirect(url_for('index'))


@app.route('/upvote/<int:track_id>', methods=['POST'])
@login_required
def upvote(track_id):
    track = Track.query.get_or_404(track_id)
    track.upvotes += 1
    db.session.commit()
    return redirect(url_for('index'))


@app.route('/admin')
@login_required
def admin():
    if not current_user.is_admin:
        flash('You do not have permission to access this page.', 'error')
        return redirect(url_for('index'))
    current_playlist = Playlist.query.filter_by(ended_at=None).first()
    tracks = Track.query.filter_by(
        playlist_id=current_playlist.id).order_by(Track.upvotes.desc()).all()
    return render_template('admin.html', title='DJ Dashboard', tracks=tracks)


@app.route('/mark_played/<int:track_id>', methods=['POST'])
@login_required
def mark_played(track_id):
    if not current_user.is_admin:
        flash('You do not have permission to perform this action.', 'error')
        return redirect(url_for('index'))
    track = Track.query.get_or_404(track_id)
    if track:
        track.played_at = datetime.utcnow()
        db.session.commit()
        flash(f'Track "{track.title}" marked as played.', 'success')
    return redirect(url_for('admin'))


@app.route('/mark_unplayed/<int:track_id>', methods=['POST'])
@login_required
def mark_unplayed(track_id):
    if not current_user.is_admin:
        flash('You do not have permission to perform this action.', 'error')
        return redirect(url_for('index'))
    track = Track.query.get_or_404(track_id)
    if track:
        track.played_at = None
        db.session.commit()
        flash(f'Track "{track.title}" marked as unplayed.', 'success')
    return redirect(url_for('admin'))


@app.route('/end_playlist', methods=['POST'])
@login_required
def end_playlist():
    if not current_user.is_admin:
        flash('You do not have permission to perform this action.', 'error')
        return redirect(url_for('index'))
    current_playlist = Playlist.query.filter_by(ended_at=None).first()
    current_playlist.ended_at = datetime.utcnow()
    db.session.commit()
    new_playlist = Playlist()
    db.session.add(new_playlist)
    db.session.commit()
    flash('Playlist ended and new one created.', 'success')
    return redirect(url_for('admin'))


@app.route('/history')
@login_required
def history():
    user_tracks = Track.query.filter_by(submitted_by=current_user.id).all()
    playlists = Playlist.query.filter(Playlist.ended_at != None).all()
    return render_template('history.html', title='History', user_tracks=user_tracks, playlists=playlists)


@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('index'))
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(username=form.username.data).first()
        if user is None or not user.check_password(form.password.data):
            flash('Invalid username or password', 'danger')

            return redirect(url_for('login'))
        login_user(user, remember=form.remember_me.data)
        next_page = request.args.get('next')
        if not next_page or urlparse(next_page).netloc != '':
            next_page = url_for('index')
        return redirect(next_page)
    return render_template('login.html', title='Sign In', form=form)


@app.route('/logout', methods=['GET', 'POST'])
@login_required
def logout():
    logout_user()
    flash('You have been logged out.', 'success')
    return redirect(url_for('index'))


@app.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('index'))
    form = RegistrationForm()
    if form.validate_on_submit():
        user = User(username=form.username.data)
        user.set_password(form.password.data)
        db.session.add(user)
        db.session.commit()
        flash('Congratulations, you are now a registered user!', 'success')
        return redirect(url_for('login'))
    return render_template('register.html', title='Register', form=form)


if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True)
