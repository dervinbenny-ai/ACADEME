import os
from datetime import timedelta
from pathlib import Path
from urllib.parse import quote_plus
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR / '.env')

class Config:
    SECRET_KEY = os.getenv('SECRET_KEY', '')
    SQLALCHEMY_DATABASE_URI = os.getenv('DATABASE_URL') or (
        f"mysql+pymysql://{quote_plus(os.getenv('MYSQL_USER', 'root'))}:"
        f"{quote_plus(os.getenv('MYSQL_PASSWORD', ''))}@{os.getenv('MYSQL_HOST', 'localhost')}:"
        f"{os.getenv('MYSQL_PORT', '3306')}/{os.getenv('MYSQL_DATABASE', 'academe_db')}?charset=utf8mb4"
    )
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_ENGINE_OPTIONS = {'pool_pre_ping': True}
    MAX_CONTENT_LENGTH = int(os.getenv('MAX_UPLOAD_MB', '10')) * 1024 * 1024
    UPLOAD_FOLDER = str(BASE_DIR / os.getenv('UPLOAD_FOLDER', 'instance/uploads'))
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = 'Lax'
    SESSION_COOKIE_SECURE = os.getenv('SESSION_COOKIE_SECURE', 'false').lower() == 'true'
    REMEMBER_COOKIE_HTTPONLY = True
    REMEMBER_COOKIE_SECURE = SESSION_COOKIE_SECURE
    REMEMBER_COOKIE_DURATION = timedelta(days=7)
    PERMANENT_SESSION_LIFETIME = timedelta(minutes=30)
    INSTITUTION_NAME = os.getenv('INSTITUTION_NAME', 'Your College Name')
