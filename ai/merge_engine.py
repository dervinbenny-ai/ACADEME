import re
from flask import abort
from services.common import profile_data, IDENTITY
from services.profile_service import LOCKED

def normalize(key, value):
    value = ' '.join(str(value or '').split()).casefold()
    if key in ('phone','emergency_contact'): value = re.sub(r'\D','',value)
    return value

def comparisons(submission):
    existing = profile_data(submission.student)
    labels = {f.key:f.label for f in submission.data_request.fields}
    return [{'key':v.key,'label':labels.get(v.key,v.key.replace('_',' ').title()),'old':existing.get(v.key,''),'new':v.value,'eligible':v.key not in IDENTITY | LOCKED and bool(v.value.strip()),
             'status':'EMPTY' if not v.value.strip() else 'SAME' if normalize(v.key,existing.get(v.key,''))==normalize(v.key,v.value) else 'CONFLICT' if existing.get(v.key) else 'NEW'} for v in submission.values]

def merge(submission, decisions):
    abort(400, 'Automatic profile merging is disabled. Use the Master Profile Update Review.')
