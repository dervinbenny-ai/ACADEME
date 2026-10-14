import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from app import create_app
from services.seed import seed

if __name__=='__main__':
    with create_app().app_context():
        seed()
        print('Essential roles, fields and Super Admin are ready. No academic demo data created.')
