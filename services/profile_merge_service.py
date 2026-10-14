from flask import abort
from flask_login import current_user
from extensions import db
from models import Submission, Student, ProfileMergeDecision, SubmissionReview
from ai.merge_engine import comparisons
from services.common import audit, notify
from services.profile_service import update_profile_value
from services.submission_service import ACCEPTED, grant_revision

def apply_selected_profile_updates(sub, selected, decisions, baselines, skip=False):
    sub=Submission.query.filter_by(id=sub.id).populate_existing().with_for_update().one()
    Student.query.filter_by(id=sub.student_id).with_for_update().one()
    db.session.expire(sub.student, ['profile'])
    if sub.status not in ACCEPTED: abort(409, 'Verify this submission before reviewing Master Profile updates.')
    if sub.profile_merge_status!='NOT_REVIEWED': abort(409, 'Profile updates for this revision have already been reviewed.')
    items=comparisons(sub)
    eligible={i['key']:i for i in items if i['eligible'] and i['status'] not in ('SAME','EMPTY')}
    selected=set(selected)
    if not selected<=set(eligible): abort(400, 'Choose eligible new or conflicting fields only.')
    if skip and selected: selected=set()
    if not skip and not selected and not any(value=='clarify' for value in decisions.values()): abort(400,'Select updates or choose Skip Profile Update.')
    clarifications=[];applied=0
    for item in items:
        key=item['key'];decision='keep'
        if item['status']=='SAME': decision='same'
        if not item['eligible']: decision='ineligible'
        if not skip and key in eligible:
            if decisions.get(key)=='clarify': decision='clarify';clarifications.append(key)
            elif key in selected:
                if baselines.get(key) != item['old']: abort(409,'A profile value has changed since you opened this review. Reload and review it again.')
                if item['status']=='CONFLICT' and decisions.get(key) not in ('keep','accept'): abort(400,'Resolve each selected conflict explicitly.')
                if item['status']=='NEW' or decisions.get(key)=='accept':
                    update_profile_value(sub.student,key,item['new'],'VERIFIED_FORM_SUBMISSION','Reviewer selected verified information',sub.request_id,current_user.id)
                    applied+=1;decision='accept'
        db.session.add(ProfileMergeDecision(submission_id=sub.id,revision_number=sub.revision_count,field=key,
            previous_value=item['old'],submitted_value=item['new'],decision=decision,reviewer_id=current_user.id))
    sub.profile_merge_status='NO_ELIGIBLE_FIELDS' if not eligible else 'SKIPPED' if not applied else 'APPLIED' if applied==len(eligible) else 'PARTIALLY_APPLIED'
    audit('Profile merge skipped' if not applied else 'Teacher selected Master Profile updates','submission',sub.id,sub.profile_merge_status+' · '+', '.join(sorted(selected)))
    if clarifications:
        grant_revision(sub,clarifications,'CORRECTION_REQUIRED')
        sub.feedback='Please clarify: '+', '.join(clarifications)
        db.session.add(SubmissionReview(submission_id=sub.id,revision_number=sub.revision_count,status='CORRECTION_REQUIRED',feedback=sub.feedback,fields=clarifications,reviewer_id=current_user.id))
        notify(sub.student.user_id,'Clarification requested',f'/student/submissions/{sub.id}',sub.feedback)
    return applied
