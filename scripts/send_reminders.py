import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from app import create_app
from services.deadline_service import send_reminders
if __name__=='__main__':
    with create_app().app_context(): print(f'Sent {send_reminders()} reminders.')
