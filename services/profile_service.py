"""Profile permissions and traceable updates shared by students and reviewers."""
from datetime import date
from flask import abort
from flask_login import current_user
from extensions import db
from models import Student, ProfileValue, ProfileVersion, ProfileChangeRequest, User, now
from services.common import audit, notify, profile_data, email, IDENTITY
from services.access import student_access
from services.validation import validate_value
from types import SimpleNamespace

EDITABLE = {'phone':'phone', 'address':'textarea', 'emergency_contact':'phone',
            'skills':'textarea', 'linkedin':'url', 'portfolio':'url', 'bio':'textarea'}
SENSITIVE = {'name':'text', 'dob':'date', 'email':'email', 'gender':'text', 'blood_group':'text'}
LOCKED = IDENTITY - {'name','email'} | {'roll_number','admission_year','teacher','teacher_id','hod','hod_id','department_id','class_id','user_id','student_id'}

def validate_profile(key, value):
    kind = {**EDITABLE, **SENSITIVE}.get(key)
    if not kind: abort(403, 'This field is managed by the institution.')
    value = str(value).strip()
    maximum = 2000 if kind=='textarea' else 254 if key=='email' else 500 if kind=='url' else 120
    if len(value)>maximum: abort(400, f'{key.replace("_", " ").title()} is too long.')
    if key in SENSITIVE and not value: abort(400, 'Official personal information cannot be blank.')
    field = SimpleNamespace(key=key, label=key.replace('_',' ').title(), type=kind, required=key in SENSITIVE, validation={}, options=[])
    value = validate_value(field, value)
    if key=='blood_group' and value not in ('A+','A-','B+','B-','AB+','AB-','O+','O-'): abort(400,'Choose a valid ABO/Rh blood group.')
    if key=='dob' and date.fromisoformat(value)>date.today(): abort(400, 'Date of birth cannot be in the future.')
    return value

def update_profile_value(student, key, value, source, reason='', request_id=None, approved_by=None):
    if key=='phone': value=validate_profile(key,value)
    old = profile_data(student).get(key, '')
    if old == value: return False
    if key in ('name','email'):
        if key=='email':
            value=email(value)
            if User.query.filter(User.email==value, User.id!=student.user_id).first(): abort(409, 'This email is already used by another account.')
        setattr(student.user, key, value)
    elif key=='register_number': student.register_number=value
    elif key in IDENTITY: abort(403, 'Academic information is managed through class assignments.')
    else:
        record=ProfileValue.query.filter_by(student_id=student.id,key=key).first()
        if record: record.value=value
        else: db.session.add(ProfileValue(student_id=student.id,key=key,value=value))
    db.session.add(ProfileVersion(student_id=student.id,key=key,old_value=old,new_value=value,
        actor_id=current_user.id,change_source=source,reason=reason[:300],request_id=request_id,approved_by=approved_by))
    audit('Master profile updated','student',student.id,f'{key} · {source} · {reason[:300]}')
    db.session.flush()
    db.session.expire(student, ['profile'])
    return True

def edit_profile(student, form):
    allowed=set(EDITABLE) | {'csrf_token','action'}
    if set(form)-allowed: abort(403, 'Only the listed personal fields can be edited directly.')
    Student.query.filter_by(id=student.id).with_for_update().first()
    values={key:validate_profile(key,form[key]) for key in EDITABLE if key in form}
    for key,value in values.items():
        update_profile_value(student,key,value,'STUDENT_DIRECT_EDIT','Student edited Master Profile')

def request_profile_change(student, field, value, reason):
    if field not in SENSITIVE: abort(403, 'Use the permitted fields for profile change requests.')
    value=validate_profile(field,value)
    Student.query.filter_by(id=student.id).with_for_update().first()
    existing=profile_data(student).get(field,'')
    if value==existing: abort(400, 'The requested value is already on your profile.')
    if ProfileChangeRequest.query.filter_by(student_id=student.id,field=field,status='PENDING').first(): abort(409, 'A change for this field is already awaiting review.')
    teachers=[u for u in student.academic_class.teachers if u.active]
    if not teachers: abort(400, 'Your institution needs to assign an active class teacher before this change can be reviewed.')
    change=ProfileChangeRequest(student_id=student.id,field=field,existing_value=existing,requested_value=value,reason=reason)
    db.session.add(change);db.session.flush()
    for teacher in teachers:
        notify(teacher.id,'Master Profile Change Request',f'/profile-changes/{change.id}',student.user.name+' · '+field.replace('_',' '),kind='MASTER_PROFILE_CHANGE_REQUEST')
    audit('Student requested profile change','profile_change',change.id,field)
    return change

def review_profile_change(change, action, note):
    student_access(change.student_id)
    if current_user.role!='TEACHER': abort(403)
    change=ProfileChangeRequest.query.filter_by(id=change.id).populate_existing().with_for_update().one()
    Student.query.filter_by(id=change.student_id).with_for_update().first()
    if change.status!='PENDING': abort(409, 'This profile change has already been reviewed.')
    if action not in ('APPROVED','REJECTED'): abort(400)
    if action=='REJECTED' and not note.strip(): abort(400, 'Explain why the profile change was rejected.')
    if action=='APPROVED':
        db.session.expire(change.student, ['profile'])
        if profile_data(change.student).get(change.field,'') != change.existing_value: abort(409, 'The official value changed since this request. Reject this stale request and ask the student to submit a new one.')
        update_profile_value(change.student,change.field,validate_profile(change.field,change.requested_value),'STUDENT_CHANGE_REQUEST',change.reason,approved_by=current_user.id)
    change.status=action;change.reviewed_by=current_user.id;change.reviewed_at=now();change.reviewer_note=note
    notify(change.student.user_id,'Profile change '+action.lower(),'/student/changes',change.field.replace('_',' ')+' · '+note,kind='PROFILE_CHANGE_'+action)
    audit('Teacher '+action.lower()+' profile change','profile_change',change.id,note)
