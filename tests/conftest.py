import sys
from pathlib import Path
import pytest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from app import create_app
from extensions import db
from models import User
from services.seed import seed

@pytest.fixture
def app(tmp_path,monkeypatch):
    monkeypatch.setenv('SUPERADMIN_PASSWORD','SuperAdmin@123')
    app=create_app({'TESTING':True,'SECRET_KEY':'test-only-key','WTF_CSRF_ENABLED':False,'SQLALCHEMY_DATABASE_URI':'sqlite://',
                    'UPLOAD_FOLDER':str(tmp_path/'uploads')})
    with app.app_context():
        db.create_all(); seed()
        yield app
        db.session.remove(); db.drop_all()

@pytest.fixture
def client(app): return app.test_client()
