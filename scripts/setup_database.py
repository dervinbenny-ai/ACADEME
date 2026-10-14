import sys
import os
import re
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from config import Config, BASE_DIR
from app import create_app
from flask_migrate import upgrade
from services.seed import seed

if __name__=='__main__':
    if not os.getenv('DATABASE_URL'):
        import pymysql
        name=os.getenv('MYSQL_DATABASE','academe_db')
        if not re.fullmatch(r'[A-Za-z0-9_]+',name): raise ValueError('MYSQL_DATABASE may contain only letters, digits and underscores.')
        conn=pymysql.connect(host=os.getenv('MYSQL_HOST','localhost'),port=int(os.getenv('MYSQL_PORT','3306')),user=os.getenv('MYSQL_USER','root'),password=os.getenv('MYSQL_PASSWORD',''))
        with conn.cursor() as cursor: cursor.execute(f'CREATE DATABASE IF NOT EXISTS `{name}` CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci')
        conn.close()
    with create_app().app_context():
        upgrade(directory=str(BASE_DIR/'migrations'))
        seed()
    print('Database migrated. Super Admin ready. No academic demo records were created.')
