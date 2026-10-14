from models import DataRequest, AdminRequirement, Notification, DeadlineExtensionRequest, DeadlineHistory, now
from services.common import notify, audit
from extensions import db
from flask import abort
from flask_login import current_user

def pending_targets(item):
    submitted={s.student_id for s in item.submissions if s.submitted_at is not None or s.status!='DRAFT'}
    return [target for target in item.targets if target.student_id not in submitted and target.student.user.active]

def validate_extension(item, proposed):
    if proposed<=now() or proposed<=item.deadline: abort(400,'The new deadline must be in the future and later than the current deadline.')
    if item.requirement and proposed>item.requirement.deadline: abort(400,'The student deadline must not exceed the HOD final deadline. Ask HOD to extend that deadline first.')

def request_deadline_extension(item, proposed, reason):
    item=DataRequest.query.filter_by(id=item.id).populate_existing().with_for_update().one()
    if current_user.role!='TEACHER' or item.teacher_id!=current_user.id or not item.requirement: abort(403)
    if item.status=='DRAFT' or item.requirement.status in ('COMPLETED','ARCHIVED'): abort(400,'This collection is not open for a deadline extension request.')
    validate_extension(item,proposed)
    if DeadlineExtensionRequest.query.filter_by(data_request_id=item.id,status='PENDING').first(): abort(409,'An extension is already awaiting HOD review.')
    targets=pending_targets(item)
    if not targets: abort(400,'Every targeted active student has already submitted.')
    change=DeadlineExtensionRequest(data_request_id=item.id,admin_requirement_id=item.requirement_id,requested_by_teacher_id=current_user.id,
        current_deadline=item.deadline,proposed_deadline=proposed,reason=reason,pending_student_count=len(targets))
    db.session.add(change);db.session.flush()
    notify(item.requirement.admin_id,'Deadline Extension Requested',f'/deadline-extensions/{change.id}',item.teacher.name+' · '+item.title,kind='DEADLINE_EXTENSION_REQUESTED')
    audit('Teacher requested deadline extension','deadline_extension',change.id,reason)
    return change

def change_deadline(item, proposed, reason, requested_by, extension_id=None):
    validate_extension(item,proposed)
    old=item.deadline;item.deadline=proposed
    if item.status=='CLOSED': item.status='PUBLISHED'
    db.session.add(DeadlineHistory(data_request_id=item.id,extension_id=extension_id,old_deadline=old,new_deadline=proposed,requested_by=requested_by,approved_by=current_user.id,reason=reason))
    for target in pending_targets(item):
        notify(target.student.user_id,'Deadline Extended',f'/requests/{item.id}/submit',f'{item.title}\nPrevious: {old:%d %b %Y %H:%M} UTC\nNew: {proposed:%d %b %Y %H:%M} UTC\nYou have not submitted this request yet.',dedupe=f'extension:{item.id}:{target.student_id}:{proposed.isoformat()}',kind='DEADLINE_EXTENDED')

def review_deadline_extension(change, action, note, proposed=None):
    item=DataRequest.query.filter_by(id=change.data_request_id).populate_existing().with_for_update().one()
    change=DeadlineExtensionRequest.query.filter_by(id=change.id).populate_existing().with_for_update().one()
    if current_user.role!='ADMIN' or change.requirement.admin_id!=current_user.id: abort(403)
    if change.status!='PENDING': abort(409,'This extension has already been reviewed.')
    if action not in ('APPROVED','REJECTED'): abort(400)
    if action=='REJECTED' and not note.strip(): abort(400,'Give a reason for rejecting the extension.')
    if action=='APPROVED':
        if change.current_deadline!=item.deadline: abort(409,'The deadline changed while this request was pending. Reject it and ask for a new request.')
        if item.requirement.status in ('COMPLETED','ARCHIVED'): abort(409,'The requirement has already been completed.')
        proposed=proposed or change.proposed_deadline
        change_deadline(item,proposed,change.reason,change.requested_by_teacher_id,change.id)
        change.approved_deadline=proposed
    change.status=action;change.hod_note=note;change.reviewed_by=current_user.id;change.reviewed_at=now()
    notify(change.requested_by_teacher_id,'Deadline extension '+action.lower(),f'/deadline-extensions/{change.id}',item.title+' · '+note,kind='DEADLINE_EXTENSION_'+action)
    audit('HOD '+action.lower()+' deadline extension','deadline_extension',change.id,note)

def send_reminders():
    sent=0
    for item in DataRequest.query.filter_by(status='PUBLISHED').all():
        days=(item.deadline.date()-now().date()).days
        if days not in (0,1,3): continue
        submitted={s.student_id for s in item.submissions if s.submitted_at is not None or s.status!='DRAFT'}
        for target in item.targets:
            if target.student_id in submitted or not target.student.user.active: continue
            key=f'request:{item.id}:student:{target.student_id}:due:{item.deadline.isoformat()}:days:{days}'
            if Notification.query.filter_by(dedupe_key=key).first(): continue
            notify(target.student.user_id,'Submission deadline reminder',f'/requests/{item.id}/submit',f'{item.title}: due in {days} day(s).',key); sent+=1
    for item in AdminRequirement.query.filter(AdminRequirement.status.in_(['ASSIGNED','ACKNOWLEDGED','IN_PROGRESS','REJECTED'])).all():
        days=(item.deadline.date()-now().date()).days
        key=f'requirement:{item.id}:due:{item.deadline.isoformat()}:days:{days}'
        if days in (0,1,3) and not Notification.query.filter_by(dedupe_key=key).first():
            notify(item.teacher_id,'HOD deadline reminder',f'/requirements/{item.id}',item.title,key); sent+=1
    db.session.commit()
    return sent
