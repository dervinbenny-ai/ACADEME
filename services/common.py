from datetime import datetime, timezone
import re
from flask import request, abort
from flask_login import current_user
from email_validator import validate_email, EmailNotValidError
from extensions import db
from models import AdminAccount, AuditLog, Notification, ProfileValue, ProfileVersion, TeacherAccount, User, Role

def audit(action, entity='', entity_id=None, details=''):
    db.session.add(AuditLog(actor_id=current_user.id if current_user.is_authenticated else None,
                           action=action, entity=entity, entity_id=entity_id, details=details,
                           ip=request.remote_addr or ''))

def notify(user_id, title, link='/dashboard', body='', dedupe=None, kind='GENERAL'):
    if dedupe and Notification.query.filter_by(dedupe_key=dedupe).first(): return
    db.session.add(Notification(user_id=user_id, title=title, link=link, body=body, dedupe_key=dedupe, kind=kind))

def required(key, max_length=200):
    value = request.form.get(key, '').strip()
    if not value or len(value) > max_length: abort(400, f'{key.replace("_", " ").title()} is required (maximum {max_length} characters).')
    return value

def integer(key):
    try: return int(request.form.get(key, ''))
    except (ValueError, TypeError): abort(400, f'Choose a valid {key}.')

def deadline(key='deadline'):
    try:
        raw_value = required(key)
        if not re.fullmatch(r'\d{4}-\d{2}-\d{2}T\d{2}:\d{2}(?::\d{2}(?:\.\d{1,6})?)?(?:Z|[+-]\d{2}:\d{2})?', raw_value):
            raise ValueError
        value=datetime.fromisoformat(raw_value)
        return value.astimezone(timezone.utc).replace(tzinfo=None) if value.tzinfo else value
    except ValueError: abort(400, 'Enter a valid deadline.')

def password_valid(value):
    return len(value) >= 12 and len(value) <= 128 and any(c.isalpha() for c in value) and any(c.isdigit() for c in value)

def email(value):
    try: return validate_email(value, check_deliverability=False).normalized.lower()
    except EmailNotValidError: abort(400, 'Enter a valid email address.')

def phone(value):
    value = value.strip()
    if not re.fullmatch(r'\+[1-9]\d{6,14}', value):
        abort(400, 'Enter a phone number with country code, for example +919876543210.')
    return value

def new_user(role):
    password = required('password', 128)
    if not password_valid(password): abort(400, 'Use at least 12 characters including letters and numbers.')
    phone_value = request.form.get('phone', '').strip()
    user = User(username=required('username',80).lower(), name=required('name',120), email=email(required('email',254)),
                phone=phone(phone_value) if phone_value else None,
                role_record=Role.query.filter_by(name=role).one(), created_by=current_user.id)
    user.set_password(password)
    db.session.add(user)
    db.session.flush()
    if role == 'ADMIN': db.session.add(AdminAccount(user_id=user.id))
    elif role == 'TEACHER': db.session.add(TeacherAccount(user_id=user.id))
    audit('Account created', 'user', user.id, role)
    return user

IMPORTANT = ['name','register_number','email','phone','blood_group','emergency_contact','cgpa','resume']
IDENTITY = {'name','register_number','email','class','department','semester','batch'}

def profile_data(student):
    data = {p.key: p.value for p in student.profile}
    data.update(name=student.user.name, register_number=student.register_number, email=student.user.email,
                **{'class':student.academic_class.name, 'department':student.academic_class.department.name,
                   'semester':student.academic_class.semester, 'batch':student.academic_class.batch})
    return data

def completion(student):
    data = profile_data(student)
    missing = [key for key in IMPORTANT if not data.get(key)]
    return round((len(IMPORTANT)-len(missing))/len(IMPORTANT)*100), missing

def set_profile(student, key, value, reason, request_id=None, change_source=None, approved_by=None):
    if not value or key in IDENTITY: return
    record = ProfileValue.query.filter_by(student_id=student.id, key=key).first()
    old = record.value if record else ''
    if old == value: return
    if record: record.value = value
    else: db.session.add(ProfileValue(student_id=student.id, key=key, value=value))
    db.session.add(ProfileVersion(student_id=student.id, key=key, old_value=old, new_value=value,
                                 actor_id=current_user.id, request_id=request_id, reason=reason,
                                 change_source=change_source or ('VERIFIED_FORM_SUBMISSION' if reason=='Verified submission' else 'TEACHER_UPDATE' if current_user.role=='TEACHER' else 'SYSTEM_UPDATE'), approved_by=approved_by))

def request_stats(item):
    total = len(item.targets)
    submitted = sum(s.submitted_at is not None or s.status != 'DRAFT' for s in item.submissions)
    verified = sum(s.status in ('VERIFIED','APPROVED') for s in item.submissions)
    return {'total':total, 'submitted':submitted, 'pending':total-submitted, 'verified':verified,
            'completion':round(submitted/total*100) if total else 0}
