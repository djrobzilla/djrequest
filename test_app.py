import pytest
from flask import url_for
from app import app, db 

@pytest.fixture
def client():
    app.config['TESTING'] = True
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
    app.config['SERVER_NAME'] = 'localhost'
    client = app.test_client()

    with app.app_context():
        db.create_all()

    yield client

    with app.app_context():
        db.drop_all()

def test_index(client):
    with app.app_context():
        response = client.get(url_for('index'))
        assert response.status_code == 200

def test_register(client):
    with app.app_context():
        response = client.get(url_for('register'))
        assert response.status_code == 200

def test_login(client):
    with app.app_context():
        response = client.get(url_for('login'))
        assert response.status_code == 200