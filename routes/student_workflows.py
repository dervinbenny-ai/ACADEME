from flask import Blueprint, render_template, request, redirect, flash, abort
from flask_login import current_user
from extensions import db
from models import *
from services.access import roles, my_student, student_access, students_query, request_access, requests_query, requirements_query
from services.common import profile_data, required, deadline
from services.profile_service import EDITABLE, SENSITIVE, LOCKED, edit_profile, request_profile_change, review_profile_change
from services.submission_service import revisable_fields
from services.change_request_service import request_submission_change, review_submission_change
from services.profile_merge_service import apply_selected_profile_updates
from services.deadline_service import pending_targets, request_deadline_extension, review_deadline_extension
from ai.merge_engine import comparisons

bp=Blueprint('student_workflows',__name__)

@bp.route('/student/profile/edit',methods=['GET','POST'])
@roles('STUDENT')
def profile_edit():
    student=my_student()
    if request.method=='POST':
        edit_profile(student,request.form);db.session.commit()
        flash('Your Master Profile has been updated. Every change is recorded in your profile history.','success')
        return redirect('/profile')
    return render_template('profile_edit.html',title='Edit Master Profile',student=student,data=profile_data(student),editable=EDITABLE,sensitive=SENSITIVE,locked=LOCKED)

@bp.route('/student/profile/change',methods=['GET','POST'])
@roles('STUDENT')
def profile_change_new():
    student=my_student()
    if request.method=='POST':
        request_profile_change(student,required('field',80),required('requested_value',2000),required('reason',3000));db.session.commit()
        flash('Your class teacher has received your profile change request.','success')
        return redirect('/student/changes')
    return render_template('profile_change_form.html',title='Master Profile Change Request',data=profile_data(student),sensitive=SENSITIVE)

@bp.get('/student/submissions')
@roles('STUDENT')
def submission_history():
    query=Submission.query.filter(Submission.student_id==my_student().id,Submission.submitted_at.isnot(None))
    return render_template('submission_history.html',title='Submitted Data',items=query.order_by(Submission.submitted_at.desc(),Submission.id.desc()).paginate(per_page=20))

def own_submission(sub_id):
    sub=Submission.query.filter_by(id=sub_id,student_id=my_student().id).first_or_404()
    if not sub.submitted_at: abort(404)
    return sub

@bp.get('/student/submissions/<int:sub_id>')
@roles('STUDENT')
def submission_detail(sub_id):
    sub=own_submission(sub_id)
    labels={f.key:f.label for f in sub.data_request.fields}
    documents={f'document:{d.id}':d.filename for d in Document.query.filter_by(student_id=sub.student_id).all()}
    return render_template('submission_snapshot.html',title='Submitted Data',submission=sub,labels=labels,documents=documents,revisable=revisable_fields(sub.data_request))

@bp.route('/student/submissions/<int:sub_id>/change',methods=['GET','POST'])
@roles('STUDENT')
def submission_change_new(sub_id):
    sub=own_submission(sub_id)
    if request.method=='POST':
        request_submission_change(sub,request.form.getlist('fields'),required('reason',3000));db.session.commit()
        flash('Your change request has been sent to the request’s teacher.','success')
        return redirect(f'/student/submissions/{sub.id}')
    return render_template('submission_change_form.html',title='Request a Change',submission=sub,allowed=revisable_fields(sub.data_request),values={v.key:v.value for v in sub.values})

@bp.get('/student/changes')
@roles('STUDENT')
def student_changes():
    student=my_student()
    return render_template('change_requests.html',title='My Change Requests',profiles=ProfileChangeRequest.query.filter_by(student_id=student.id).order_by(ProfileChangeRequest.requested_at.desc()).all(),changes=SubmissionChangeRequest.query.filter_by(student_id=student.id).order_by(SubmissionChangeRequest.requested_at.desc()).all())

@bp.get('/change-requests')
@roles('TEACHER')
def teacher_changes():
    ids=students_query().with_entities(Student.id)
    request_ids=requests_query().with_entities(DataRequest.id)
    profiles=ProfileChangeRequest.query.filter(ProfileChangeRequest.student_id.in_(ids)).order_by(ProfileChangeRequest.requested_at.desc()).all()
    changes=SubmissionChangeRequest.query.join(Submission).filter(Submission.request_id.in_(request_ids),SubmissionChangeRequest.student_id.in_(ids)).order_by(SubmissionChangeRequest.requested_at.desc()).all()
    return render_template('change_requests.html',title='Student Change Requests',profiles=profiles,changes=changes)

@bp.route('/profile-changes/<int:change_id>',methods=['GET','POST'])
@roles('TEACHER')
def profile_change_review(change_id):
    change=db.get_or_404(ProfileChangeRequest,change_id);student_access(change.student_id)
    if request.method=='POST':
        review_profile_change(change,request.form.get('action'),request.form.get('note','').strip()[:3000]);db.session.commit()
        flash('Profile change review saved.','success');return redirect('/change-requests')
    return render_template('change_review.html',title='Review Profile Change',change=change,profile_change=True)

@bp.route('/submission-changes/<int:change_id>',methods=['GET','POST'])
@roles('TEACHER')
def submission_change_review(change_id):
    change=db.get_or_404(SubmissionChangeRequest,change_id);request_access(change.submission.request_id);student_access(change.student_id)
    if request.method=='POST':
        review_submission_change(change,request.form.get('action'),request.form.get('note','').strip()[:3000]);db.session.commit()
        flash('Submission change review saved.','success');return redirect('/change-requests')
    return render_template('change_review.html',title='Review Submission Change',change=change,profile_change=False)

@bp.route('/submissions/<int:sub_id>/profile-review',methods=['GET','POST'])
@roles('TEACHER')
def profile_merge_review(sub_id):
    sub=db.get_or_404(Submission,sub_id);request_access(sub.request_id);student_access(sub.student_id)
    if sub.status not in ('VERIFIED','APPROVED'): abort(409,'Verify the submission before reviewing its Master Profile updates.')
    if request.method=='POST':
        if request.form.get('action') not in ('apply','skip'): abort(400)
        decisions={k.removeprefix('decision_'):v for k,v in request.form.items() if k.startswith('decision_')}
        baselines={k.removeprefix('baseline_'):v for k,v in request.form.items() if k.startswith('baseline_')}
        count=apply_selected_profile_updates(sub,request.form.getlist('selected'),decisions,baselines,request.form.get('action')=='skip');db.session.commit()
        flash(f'{count} selected profile field(s) updated.' if count else 'Profile review saved. Unselected information remains in the submission.','success')
        return redirect(f'/submissions/{sub.id}')
    return render_template('profile_merge.html',title='Master Profile Update Review',submission=sub,items=comparisons(sub))

@bp.get('/deadline-extensions')
@roles('ADMIN','TEACHER')
def deadline_extensions():
    query=DeadlineExtensionRequest.query
    if current_user.role=='ADMIN': query=query.filter(DeadlineExtensionRequest.admin_requirement_id.in_(requirements_query().with_entities(AdminRequirement.id)))
    else: query=query.filter(DeadlineExtensionRequest.data_request_id.in_(requests_query().with_entities(DataRequest.id)))
    return render_template('deadline_extensions.html',title='Deadline Extensions',items=query.order_by(DeadlineExtensionRequest.requested_at.desc()).all())

@bp.route('/requests/<int:item_id>/extension',methods=['GET','POST'])
@roles('TEACHER')
def extension_new(item_id):
    item=request_access(item_id)
    if not item.requirement: abort(400,'Independent requests use the direct deadline action on the request page.')
    if request.method=='POST':
        change=request_deadline_extension(item,deadline('proposed_deadline'),required('reason',3000));db.session.commit()
        flash('Your deadline extension request has been sent to HOD.','success');return redirect(f'/deadline-extensions/{change.id}')
    return render_template('deadline_extension.html',title='Request Deadline Extension',item=item,change=None,pending=len(pending_targets(item)))

@bp.route('/deadline-extensions/<int:change_id>',methods=['GET','POST'])
@roles('ADMIN','TEACHER')
def extension_review(change_id):
    change=db.get_or_404(DeadlineExtensionRequest,change_id);item=request_access(change.data_request_id)
    if current_user.role=='ADMIN' and change.requirement.admin_id!=current_user.id: abort(404)
    if request.method=='POST':
        if current_user.role!='ADMIN': abort(403)
        proposed=deadline('approved_deadline') if request.form.get('action')=='APPROVED' and request.form.get('approved_deadline') else None
        review_deadline_extension(change,request.form.get('action'),request.form.get('note','').strip()[:3000],proposed);db.session.commit()
        flash('Deadline extension review saved.','success');return redirect(f'/deadline-extensions/{change.id}')
    return render_template('deadline_extension.html',title='Deadline Extension Review',item=item,change=change,pending=len(pending_targets(item)))
