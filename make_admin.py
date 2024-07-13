import os
import sys
from app import app, db
from app import User


def make_admin(username, password):
    # check if the provided password matches the environment variable
    if password != os.getenv('ADMIN_SCRIPT_PASSWORD'):
        print("Unauthorized: Incorrect Password.")
        return

    with app.app_context():
        user = User.query.filter_by(username=username).first()
        if user:
            user.is_admin = True
            db.session.commit()
            print(f"User {user.username} is now an admin.")
        else:
            print("User not found.")


if __name__ == '__main__':
    if len(sys.argv) != 3:
        print("Usage: python make_admin.py <username> <password>")
    else:
        make_admin(sys.argv[1], sys.argv[2])
