from flask import abort
from flask_login import current_user
from extensions import db
from models import Submission, SubmissionChangeRequest, now
from services.common import notify, audit
from services.access import request_access, student_access
from services.submission_service import grant_revision, revisable_fields

def request_submission_change(sub, fields, reason):
    sub=Submission.query.filter_by(id=sub.id).populate_existing().with_for_update().one()
    if current_user.role!='STUDENT' or sub.student.user_id!=current_user.id: abort(403)
    if not sub.submitted_at or sub.status=='DRAFT': abort(400, 'Submit the request before requesting a change.')
    if sub.revision_allowed or SubmissionChangeRequest.query.filter(SubmissionChangeRequest.submission_id==sub.id,SubmissionChangeRequest.status.in_(('PENDING','APPROVED'))).first(): abort(409, 'A change request is already open.')
    keys=set(fields)
    if not keys or not keys<=revisable_fields(sub.data_request): abort(400, 'Select valid submitted fields. Institutional identifiers remain managed by the institution.')
    existing={v.key:v.value for v in sub.values if v.key in keys}
    change=SubmissionChangeRequest(submission_id=sub.id,student_id=sub.student_id,teacher_id=sub.data_request.teacher_id,reason=reason,requested_fields=sorted(keys),existing_values=existing)
    db.session.add(change);db.session.flush()
    notify(change.teacher_id,'Student submission change request',f'/submission-changes/{change.id}',f'{sub.student.user.name} requested permission to modify {sub.data_request.title}.',kind='STUDENT_SUBMISSION_CHANGE_REQUEST')
    audit('Student requested submission modification','submission_change',change.id,reason)
    return change

def review_submission_change(change, action, note):
    if current_user.role!='TEACHER': abort(403)
    request_access(change.submission.request_id);student_access(change.student_id)
    # Lock parent first, the same order used by student submission writes.
    sub=Submission.query.filter_by(id=change.submission_id).populate_existing().with_for_update().one()
    change=SubmissionChangeRequest.query.filter_by(id=change.id).populate_existing().with_for_update().one()
    if change.status!='PENDING': abort(409,'This change request has already been reviewed.')
    if action not in ('APPROVED','REJECTED'): abort(400)
    if action=='REJECTED' and not note.strip(): abort(400,'Give a reason for rejecting the change.')
    if action=='APPROVED': grant_revision(sub,change.requested_fields,'REVISION_ALLOWED')
    change.status=action;change.reviewed_by=current_user.id;change.reviewed_at=now();change.teacher_note=note
    notify(sub.student.user_id,'Submission change '+action.lower(),f'/student/submissions/{sub.id}',sub.data_request.title+' · '+note,kind='SUBMISSION_CHANGE_'+action)
    audit('Teacher '+action.lower()+' submission modification','submission_change',change.id,note)
