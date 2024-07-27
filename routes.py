import logging
from flask import render_template, request, g, redirect, url_for, flash as original_flash
from app import app
from extensions import db
from urllib.parse import urlparse
from flask_login import login_user, login_required, logout_user, current_user
import user_agents
from models import User, Track, Playlist, LoginForm, RegistrationForm
from datetime import datetime


# set up logging
logging.basicConfig(filename='app.log', level=logging.INFO,
                    format='%(asctime)s - %(levelname)s - %(message)s')


###
#  customized flash function, to 
#  automatically log flash messages
#  without the need for a separate function
###

# custom flash class
class FlashLogger:
    def __init__(self, original_flash):
        self.original_flash = original_flash

    def __call__(self, message, category='message'):
        logging.info(
            f'Flash Message - Category: {category}, Message: {message}')
        self.original_flash(message, category)
        script = f"<script>console.log('Flash Message - Category: {category}, Message: {message}');</script>"
        from markupsafe import Markup
        self.original_flash(Markup(script), 'console')

# Instantiate the custom flash logger
flash = FlashLogger(original_flash)

###
# end custom flash function
###


# grab user agent info before every page load 
# to aid handling of mobile layouts
@app.before_request
def detect_device():
    user_agent = user_agents.parse(request.headers.get('User-Agent'))
    g.is_mobile = user_agent.is_mobile


# public routes
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


# authentication routes
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

@app.route('/forgot_password', methods=['GET', 'POST'])
def forgot_password():
    if request.method == 'POST':
        email = request.form['email']
        # pw reset logic goes here
        flash('If an account with that email exists, a password reset link has been sent.', 'info')
        return render_template('forgot_password.html')


# user routes
@app.route('/history')
@login_required
def history():
    user_tracks = Track.query.filter_by(submitted_by=current_user.id).all()
    playlists = Playlist.query.filter(Playlist.ended_at != None).all()
    return render_template('history.html', title='History', user_tracks=user_tracks, playlists=playlists)


# admin routes
@app.route('/admin', methods=['GET'])
@login_required
def admin():
    if not current_user.is_admin:
        flash('You do not have permission to access this page.', 'error')
        return redirect(url_for('index'))
    current_playlist = Playlist.query.filter_by(ended_at=None).first()
    tracks = Track.query.filter_by(
        playlist_id=current_playlist.id).order_by(Track.upvotes.desc()).all()
    return render_template('admin.html', title='DJ Dashboard', tracks=tracks)


# public request routes
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
        username = current_user.username
    else:
        username = 'Anonymous'
    db.session.add(track)
    db.session.commit()
    flash(f'Track requested successfully by {username}!', 'success')
    return redirect(url_for('index'))


# user request routes
@app.route('/upvote/<int:track_id>', methods=['POST'])
@login_required
def upvote(track_id):
    track = Track.query.get_or_404(track_id)
    track.upvotes += 1
    db.session.commit()
    return redirect(url_for('index'))


# admin request routes
@app.route('/mark_played/<int:track_id>', methods=['GET', 'POST'])
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
    return redirect(request.referrer or url_for('admin'))

@app.route('/delete_track/<int:track_id>', methods=['POST'])
@login_required
def delete_track(track_id):
    if not current_user.is_admin:
        flash('You do not have permission to perform this action.', 'error')
        return (url_for('index'))
    track = Track.query.get_or_404(track_id)
    db.session.delete(track)
    db.session.commit()
    flash(f'Track {track.title} has been deleted.', 'success')
    return redirect(request.referrer or url_for('admin'))
