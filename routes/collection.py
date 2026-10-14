import json
from flask import Blueprint, render_template, request, redirect, flash, abort
from flask_login import current_user
from extensions import db
from models import *
from services.access import *
from services.common import required, integer, deadline, audit, notify, profile_data, request_stats
from services.validation import validate_fields, validate_value
from ai.merge_engine import comparisons
from services.submission_service import can_edit, save_submission, review_submission, revisable_fields
from services.deadline_service import change_deadline

bp=Blueprint('collection',__name__)

@bp.get('/requirements')
@roles('ADMIN','TEACHER')
def requirements():
    query=requirements_query()
    for key in ('status','priority','teacher_id','class_id'):
        if request.args.get(key): query=query.filter(getattr(AdminRequirement,key)==request.args[key])
    if request.args.get('q'): query=query.filter(AdminRequirement.title.ilike('%'+request.args['q']+'%'))
    if request.args.get('date'):
        try: query=query.filter(AdminRequirement.deadline >= __import__('datetime').datetime.fromisoformat(request.args['date']))
        except ValueError: abort(400,'Invalid date filter.')
    return render_template('requirements.html',title='Data requirements',items=query.order_by(AdminRequirement.created_at.desc()).paginate(per_page=20),classes=classes())

@bp.route('/requirements/new',methods=['GET','POST'])
@bp.route('/requirements/<int:edit_id>/edit',methods=['GET','POST'])
@roles('ADMIN')
def requirement_new(edit_id=None):
    edit=requirements_query().filter_by(id=edit_id).first_or_404() if edit_id else None
    if edit and edit.status in ('READY_FOR_REVIEW','COMPLETED','ARCHIVED'): abort(400,'This requirement has reached reporting. Return it for correction before editing.')
    if request.method=='POST':
        cls=class_access(integer('class_id'))
        teacher=db.get_or_404(User,integer('teacher_id'))
        if teacher not in cls.teachers or not teacher.active: abort(400,'Choose an active teacher assigned to this class.')
        due=deadline()
        if due<=now(): abort(400,'The deadline must be in the future.')
        priority=request.form.get('priority','NORMAL')
        if priority not in ('LOW','NORMAL','HIGH','URGENT'): abort(400)
        if edit and edit.requests and (edit.class_id!=cls.id or edit.teacher_id!=teacher.id): abort(400,'Class and teacher cannot change after collection has started.')
        if edit and any(r.deadline>due for r in edit.requests): abort(400,'The HOD deadline cannot precede an existing student deadline.')
        item=edit or AdminRequirement(admin_id=current_user.id,status='DRAFT' if request.form.get('action')=='draft' else 'ASSIGNED')
        item.title=required('title')
        item.description=request.form.get('description','')[:10000]
        item.purpose=request.form.get('purpose','')[:3000]
        item.requested_information=required('requested_information',10000)
        item.notes=request.form.get('notes','')[:3000]
        item.teacher=teacher
        item.academic_class=cls
        item.deadline=due
        item.priority=priority
        if edit and edit.status=='DRAFT' and request.form.get('action')!='draft': item.status='ASSIGNED'
        db.session.add(item); db.session.flush()
        if item.status!='DRAFT': notify(teacher.id,'Requirement updated by HOD' if edit else 'New requirement from HOD',f'/requirements/{item.id}',item.title)
        audit('Requirement updated' if edit else 'Requirement created','requirement',item.id)
        db.session.commit()
        return redirect(f'/requirements/{item.id}')
    return render_template('requirement_form.html',title='Edit data requirement' if edit else 'Create data requirement',classes=classes(),edit=edit)

@bp.route('/requirements/<int:item_id>',methods=['GET','POST'])
@roles('ADMIN','TEACHER')
def requirement_detail(item_id):
    item=requirements_query().filter_by(id=item_id).first_or_404()
    if current_user.role=='TEACHER' and item.status=='DRAFT': abort(404)
    if request.method=='POST':
        action=request.form.get('action')
        if action=='acknowledge' and current_user.role=='TEACHER' and item.status=='ASSIGNED': item.status='ACKNOWLEDGED'
        elif action=='send' and current_user.role=='ADMIN' and item.status=='DRAFT':
            item.status='ASSIGNED'
            notify(item.teacher_id,'New requirement from HOD',f'/requirements/{item.id}',item.title)
        elif action=='ready' and current_user.role=='TEACHER' and item.status in ('ACKNOWLEDGED','IN_PROGRESS','REJECTED'):
            published=[r for r in item.requests if r.status!='DRAFT']
            if not published or any(not r.targets or request_stats(r)['verified'] != len(r.targets) for r in published):
                abort(400,'All targeted students must have verified or approved submissions before sending the report to HOD.')
            item.status='READY_FOR_REVIEW'
            notify(item.admin_id,'Requirement completed · report ready',f'/requirements/{item.id}',item.title)
        elif action=='complete' and current_user.role=='ADMIN' and item.status=='READY_FOR_REVIEW':
            item.status='COMPLETED'; item.completed_at=now()
            notify(item.teacher_id,'HOD accepted your report',f'/requirements/{item.id}',item.title)
        elif action=='reject' and current_user.role=='ADMIN' and item.status=='READY_FOR_REVIEW':
            item.status='REJECTED'; item.notes=required('notes',3000)
            notify(item.teacher_id,'Requirement correction from HOD',f'/requirements/{item.id}',item.notes)
        elif action=='extend' and current_user.role=='ADMIN' and item.status not in ('COMPLETED','ARCHIVED'):
            due=deadline()
            if due <= item.deadline: abort(400,'The new deadline must be later.')
            item.deadline=due
            notify(item.teacher_id,'Requirement deadline extended',f'/requirements/{item.id}',str(due))
        elif action=='archive' and current_user.role=='ADMIN' and item.status=='COMPLETED': item.status='ARCHIVED'
        else: abort(400,'This action is not available for the current status.')
        audit('Requirement '+action,'requirement',item.id)
        db.session.commit()
        flash('Requirement updated.','success')
        return redirect(f'/requirements/{item.id}')
    return render_template('requirement_detail.html',title=item.title,item=item,stats=request_stats)

@bp.get('/requests')
@roles('ADMIN','TEACHER','STUDENT')
def requests_list():
    query=requests_query()
    if request.args.get('q'): query=query.filter(DataRequest.title.ilike('%'+request.args['q']+'%'))
    own={}
    if current_user.role=='STUDENT':
        own={s.request_id:s for s in Submission.query.filter_by(student_id=my_student().id).all()}
        if request.args.get('status'):
            state=request.args['status']
            ids=[key for key,sub in own.items() if sub.status==state]
            query=query.filter(DataRequest.id.notin_(list(own))) if state=='PENDING' else query.filter(DataRequest.id.in_(ids))
    elif request.args.get('status'): query=query.filter(DataRequest.status==request.args['status'])
    return render_template('requests.html',title='My requests' if current_user.role=='STUDENT' else 'Data requests',items=query.order_by(DataRequest.created_at.desc()).paginate(per_page=20),stats=request_stats,own=own)

@bp.route('/requests/new',methods=['GET','POST'])
@bp.route('/requests/<int:draft_id>/edit',methods=['GET','POST'])
@roles('TEACHER')
def request_new(draft_id=None):
    draft=request_access(draft_id) if draft_id else None
    if draft and draft.status!='DRAFT': abort(400,'Published field definitions are locked. Duplicate the template for a new collection.')
    req_id=draft.requirement_id if draft else request.values.get('requirement_id',type=int)
    requirement=requirements_query().filter_by(id=req_id).first_or_404() if req_id else None
    if requirement and requirement.status not in ('ASSIGNED','ACKNOWLEDGED','IN_PROGRESS','REJECTED'): abort(400,'This requirement is not open for collection.')
    policy=db.session.get(SystemSetting,'independent_requests')
    if not requirement and policy and policy.value!='true': abort(403,'Independent requests are disabled by institution policy.')
    if request.method=='POST':
        cls=class_access(integer('class_id'))
        if requirement and cls.id!=requirement.class_id: abort(400,'Use the class from the HOD requirement.')
        due=deadline()
        if due<=now() or requirement and due>requirement.deadline: abort(400,'Set a future student deadline no later than the HOD deadline.')
        try: fields=validate_fields(json.loads(request.form.get('fields_json','[]')))
        except (ValueError,TypeError): abort(400,'Invalid form fields.')
        item=draft or DataRequest(teacher_id=current_user.id)
        item.title=required('title')
        item.description=request.form.get('description','')[:10000]
        item.purpose=request.form.get('purpose','')[:3000]
        item.academic_class=cls
        item.requirement=requirement
        item.deadline=due
        item.allow_late='allow_late' in request.form
        item.allow_edit='allow_edit' in request.form
        db.session.add(item); db.session.flush()
        if draft:
            FormField.query.filter_by(request_id=item.id).delete(synchronize_session='fetch')
            RequestTarget.query.filter_by(request_id=item.id).delete(synchronize_session='fetch')
            db.session.flush()
        for field in fields: db.session.add(FormField(request_id=item.id,**field))
        ids=request.form.getlist('targets',type=int)
        candidates=students_query().join(User,Student.user_id==User.id).filter(Student.class_id==cls.id,User.active.is_(True))
        if ids: candidates=candidates.filter(Student.id.in_(ids))
        targets=candidates.all()
        if ids and len(targets)!=len(set(ids)): abort(403)
        for student in targets: db.session.add(RequestTarget(request_id=item.id,student_id=student.id))
        audit('Request draft created','request',item.id)
        db.session.commit()
        return redirect(f'/requests/{item.id}')
    clone=draft or (request_access(request.args.get('clone',type=int)) if request.args.get('clone') else None)
    initial=[{k:getattr(f,k) for k in ('key','label','type','required','reuse','options','validation','placeholder','help_text')} for f in clone.fields] if clone else []
    library=[{'key':f.key,'label':f.label,'type':f.type,'category':f.category,'options':f.options,'required':True,'reuse':'auto','validation':{}} for f in FieldLibrary.query.order_by(FieldLibrary.category,FieldLibrary.label).all()]
    return render_template('builder.html',title='Edit draft' if draft else 'Create data request',requirement=requirement,classes=classes(),students=students_query().all(),library=library,initial=initial,clone=clone,draft=draft)

@bp.route('/requests/<int:item_id>',methods=['GET','POST'])
@roles('ADMIN','TEACHER','STUDENT')
def request_detail(item_id):
    item=request_access(item_id)
    if current_user.role=='STUDENT': return redirect(f'/requests/{item.id}/submit')
    if request.method=='POST':
        if current_user.role!='TEACHER': abort(403)
        action=request.form.get('action')
        if action=='publish' and item.status=='DRAFT':
            if not item.fields or not item.targets: abort(400,'Add at least one field and an active student before publishing.')
            if item.deadline<=now(): abort(400,'Extend the deadline before publishing.')
            if item.requirement and item.requirement.status in ('READY_FOR_REVIEW','COMPLETED','ARCHIVED'): abort(400,'Requirement is no longer collecting data.')
            item.status='PUBLISHED'; item.published_at=now()
            for target in item.targets: notify(target.student.user_id,'New data request',f'/requests/{item.id}/submit',item.title)
            if item.requirement:
                item.requirement.status='IN_PROGRESS'
                notify(item.requirement.admin_id,'Requirement started',f'/requirements/{item.requirement_id}',item.title)
        elif action=='close' and item.status=='PUBLISHED': item.status='CLOSED'
        elif action=='extend' and item.status in ('DRAFT','PUBLISHED','CLOSED'):
            due=deadline()
            if due<=item.deadline or item.requirement and due>item.requirement.deadline: abort(400,'Extend to a later date within the HOD deadline.')
            if item.requirement and item.status!='DRAFT': abort(403,'Request a deadline extension from HOD for this linked collection.')
            change_deadline(item,due,required('reason',3000),current_user.id)
        else: abort(400,'Invalid request action.')
        audit('Request '+action,'request',item.id)
        db.session.commit()
        flash('Request updated.','success')
        return redirect(f'/requests/{item.id}')
    submissions={s.student_id:s for s in item.submissions}
    targets=item.targets
    term=request.args.get('q','').lower()
    if term: targets=[t for t in targets if term in (t.student.user.name+' '+t.student.register_number).lower()]
    status=request.args.get('status')
    if status: targets=[t for t in targets if (submissions[t.student_id].status if t.student_id in submissions else 'PENDING')==status]
    return render_template('request_detail.html',title=item.title,item=item,stats=request_stats(item),submissions=submissions,targets=targets)

@bp.route('/requests/<int:item_id>/submit',methods=['GET','POST'])
@roles('STUDENT')
def submit(item_id):
    item=request_access(item_id)
    student=my_student()
    if request.method=='POST':
        sub=save_submission(item,student,request.form,request.files)
        db.session.commit()
        flash('Draft saved.' if sub.status=='DRAFT' else 'Submission received. Your teacher will review it; profile updates are selected separately.','success')
        return redirect(f'/requests/{item.id}/submit')
    sub=Submission.query.filter_by(request_id=item.id,student_id=student.id).first()
    return render_template('submit.html',title=item.title,item=item,student=student,data=profile_data(student),
        previous={v.key:v.value for v in sub.values} if sub else {},submission=sub,editable=can_edit(item,sub),
        revising=bool(sub and sub.revision_allowed),revision_fields=set(sub.revision_fields or []) if sub else set())

@bp.route('/submissions/<int:sub_id>',methods=['GET','POST'])
@roles('TEACHER')
def review(sub_id):
    sub=db.get_or_404(Submission,sub_id)
    request_access(sub.request_id);student_access(sub.student_id)
    if request.method=='POST':
        review_submission(sub,request.form.get('action'),request.form.get('feedback','').strip()[:3000],request.form.getlist('correction_fields'))
        db.session.commit()
        flash('Review saved.','success')
        return redirect(f'/submissions/{sub.id}/profile-review' if sub.status in ('VERIFIED','APPROVED') else f'/submissions/{sub.id}')
    return render_template('review.html',title='Review submission',submission=sub,items=comparisons(sub),revisable=revisable_fields(sub.data_request))
