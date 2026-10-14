import getpass
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app import create_app
from config import BASE_DIR
from extensions import db
from flask_migrate import upgrade
from services.common import password_valid
from services.seed import seed
from sqlalchemy import text


def reset_database(app, username, email, name, password):
    with app.app_context():
        db.drop_all()
        db.session.execute(text('DROP TABLE IF EXISTS alembic_version'))
        db.session.commit()
        upgrade(directory=str(BASE_DIR / 'migrations'))
        seed(superadmin_password=password, superadmin_username=username,
             superadmin_email=email, superadmin_name=name)


def main():
    app = create_app()
    database_uri = app.config['SQLALCHEMY_DATABASE_URI']
    database_name = database_uri.rsplit('/', 1)[-1].split('?', 1)[0]
    print(f'This will permanently delete all Academe database records in: {database_name}')
    if input('Type RESET to continue: ').strip() != 'RESET':
        print('Reset cancelled.')
        return

    username = input('New Super Admin username: ').strip().lower()
    email = input('New Super Admin email: ').strip().lower()
    name = input('New Super Admin name: ').strip()
    if (not username or len(username) > 80 or len(email) > 254 or len(name) > 120
            or not re.fullmatch(r'[^@\s]+@[^@\s]+\.[^@\s]+', email) or not name):
        raise SystemExit('Username, a valid email, and name are required.')

    password = getpass.getpass('New Super Admin password (12+ characters, letters and numbers): ')
    confirmation = getpass.getpass('Confirm password: ')
    if password != confirmation or not password_valid(password):
        raise SystemExit('Passwords must match and contain 12-128 characters, including letters and numbers.')

    reset_database(app, username, email, name, password)
    print('Database reset complete. Only the new Super Admin account was created.')


if __name__ == '__main__':
    main()