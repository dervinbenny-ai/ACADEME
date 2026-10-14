"""One response per assignment, with explicit, single-use revisions."""
from flask import abort
from flask_login import current_user
from extensions import db
from models import Submission, SubmissionValue, SubmissionRevision, SubmissionReview, SubmissionChangeRequest, RequestTarget, now
from services.common import profile_data, audit, notify, IDENTITY
from services.validation import validate_value
from services.profile_service import LOCKED

REVIEWABLE = ('SUBMITTED','RESUBMITTED','UNDER_REVIEW')
ACCEPTED = ('VERIFIED','APPROVED')

def revisable_fields(item):
    return {f.key for f in item.fields} - IDENTITY - LOCKED

def can_edit(item, sub):
    if sub and sub.revision_allowed:
        return item.status in ('PUBLISHED','CLOSED') and sub.status in ('REVISION_ALLOWED','CORRECTION_REQUIRED')
    return item.status=='PUBLISHED' and (item.deadline>=now() or item.allow_late) and (not sub or sub.status=='DRAFT' and not sub.submitted_at)

def reopen_requirement(item):
    if item.requirement and item.requirement.status in ('READY_FOR_REVIEW','COMPLETED','ARCHIVED'):
        item.requirement.status='IN_PROGRESS'; item.requirement.completed_at=None
        notify(item.requirement.admin_id,'Submission reopened for revision',f'/requirements/{item.requirement_id}',item.title+' requires another review.')

def grant_revision(sub, fields, status):
    allowed=set(fields)
    if not allowed or not allowed <= revisable_fields(sub.data_request): abort(400, 'Select valid non-institutional fields for correction.')
    if sub.revision_allowed: abort(409, 'A revision is already open for this submission.')
    sub.revision_allowed=True;sub.revision_fields=sorted(allowed);sub.status=status
    reopen_requirement(sub.data_request)

def save_submission(item, student, form, files):
    # The target exists before a first submission and serializes concurrent first
    # POSTs on MySQL. The unique (request, student) constraint is a second guard.
    RequestTarget.query.filter_by(request_id=item.id,student_id=student.id).with_for_update().one()
    sub=Submission.query.filter_by(request_id=item.id,student_id=student.id).populate_existing().with_for_update().first()
    if sub and sub.status!='DRAFT' and not sub.revision_allowed:
        abort(403, 'This request has already been submitted. Request a change to revise it.')
    if not can_edit(item,sub): abort(403, 'This request is currently closed or its deadline has passed.')
    revising=bool(sub and sub.revision_allowed)
    draft=form.get('action')=='draft'
    if form.get('action') not in ('draft','submit','revise',None): abort(400, 'Invalid submission action.')
    if revising and draft: abort(400, 'Review your changes and submit the revised information in one step.')
    previous={v.key:v.value for v in sub.values} if sub else {}
    data=profile_data(student)
    allowed=set(sub.revision_fields or []) if revising else {f.key for f in item.fields}
    payload=set(form) | set(files)
    accepted=allowed | {'confirm_'+key for key in allowed} | {'action','csrf_token'}
    if payload-accepted: abort(403, 'Only the approved fields may be changed.')
    values=dict(previous) if revising else {}
    latest=sorted(sub.revisions,key=lambda r:r.number)[-1] if sub and sub.revisions else None
    sources=dict(latest.sources) if latest else {}
    for field in item.fields:
        if field.key not in allowed: continue
        existing=data.get(field.key,'')
        if not revising and existing and (field.reuse in ('auto','confirm') or field.key in IDENTITY):
            if field.reuse=='confirm' and not draft and form.get('confirm_'+field.key)!='yes': abort(400,f'Confirm {field.label}.')
            value=existing;sources[field.key]='REUSED_PROFILE'
        elif field.type=='file':
            from services.document_service import save_document
            upload=files.get(field.key)
            if upload and upload.filename:
                document=save_document(student,upload);value=f'document:{document.id}'
            else: value=previous.get(field.key,existing if not revising else '')
            sources[field.key]='REVISED' if revising else 'STUDENT_SUBMITTED'
        else:
            value=' | '.join(form.getlist(field.key)) if field.type=='multiselect' else ('Yes' if field.key in form else 'No') if field.type=='checkbox' else form.get(field.key,'')
            sources[field.key]='REVISED' if revising else 'STUDENT_SUBMITTED'
        values[field.key]=validate_value(field,value,draft)
    if values.get('start_date') and values.get('end_date') and values['start_date']>values['end_date']: abort(400,'End date must follow start date.')
    if not sub:
        sub=Submission(request_id=item.id,student_id=student.id)
        db.session.add(sub);db.session.flush()
    existing_values={v.key:v for v in sub.values}
    for key,value in values.items():
        if key in existing_values: existing_values[key].value=value
        else: db.session.add(SubmissionValue(submission_id=sub.id,key=key,value=value))
    sub.status='DRAFT' if draft else 'RESUBMITTED' if revising else 'SUBMITTED'
    sub.late=item.deadline<now()
    if not draft:
        sub.submitted_at=now();sub.revision_count+=1
        sub.profile_merge_status='NOT_REVIEWED';sub.reviewed_at=None;sub.reviewer_id=None
        identity={key:data.get(key,'') for key in ('name','register_number','email','class','department')}
        db.session.add(SubmissionRevision(submission_id=sub.id,number=sub.revision_count,values=values,identity=identity,
            sources=sources,source='REVISION' if revising else 'INITIAL_SUBMISSION',created_by=current_user.id,created_at=sub.submitted_at))
        if revising:
            for change in SubmissionChangeRequest.query.filter_by(submission_id=sub.id,status='APPROVED').all(): change.status='COMPLETED'
        sub.revision_allowed=False;sub.revision_fields=[]
        notify(item.teacher_id,'Student resubmitted' if revising else 'New student submission',f'/submissions/{sub.id}',student.user.name+' · '+item.title)
    audit('Submission saved' if draft else 'Student resubmitted' if revising else 'Student submitted','submission',sub.id)
    return sub

def review_submission(sub, action, feedback, fields):
    sub=Submission.query.filter_by(id=sub.id).populate_existing().with_for_update().one()
    if sub.status not in REVIEWABLE: abort(409, 'This submission is not awaiting review.')
    if action in ACCEPTED:
        sub.status=action
        # Verification is deliberately independent of permanent profile updates.
    elif action in ('CORRECTION_REQUIRED','REJECTED'):
        if not feedback.strip(): abort(400, 'Provide feedback for the student.')
        if action=='CORRECTION_REQUIRED':
            grant_revision(sub,fields or revisable_fields(sub.data_request),'CORRECTION_REQUIRED')
        else: sub.status='REJECTED'
        for change in SubmissionChangeRequest.query.filter_by(submission_id=sub.id,status='PENDING').all():
            change.status='REJECTED';change.teacher_note='Superseded by teacher review: '+feedback
            change.reviewed_by=current_user.id;change.reviewed_at=now()
            notify(sub.student.user_id,'Submission change request closed','/student/changes',change.teacher_note,kind='SUBMISSION_CHANGE_REJECTED')
    elif action=='UNDER_REVIEW': sub.status=action
    else: abort(400, 'Invalid review action.')
    sub.feedback=feedback;sub.reviewer_id=current_user.id;sub.reviewed_at=now()
    db.session.add(SubmissionReview(submission_id=sub.id,revision_number=sub.revision_count,status=sub.status,
        feedback=feedback,fields=sub.revision_fields or [],reviewer_id=current_user.id))
    notify(sub.student.user_id,'Submission '+action.replace('_',' ').lower(),f'/student/submissions/{sub.id}',feedback)
    audit('Submission '+action,'submission',sub.id)
