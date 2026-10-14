from collections import Counter
from flask import Blueprint,render_template,request,redirect,flash,abort,current_app,send_file
from flask_login import current_user,login_required
from extensions import db
from models import *
from services.access import *
from services.common import *

bp=Blueprint('core',__name__)

@bp.get('/dashboard')
@login_required
def dashboard():
    students=students_query().all()
    reqs=requirements_query().all()
    requests_=requests_query().all()
    student=my_student() if current_user.role=='STUDENT' else None
    if current_user.role=='SUPER_ADMIN':
        cards=[('Administrators',User.query.join(Role).filter(Role.name=='ADMIN').count(),'/users','people'),('Active accounts',User.query.filter_by(active=True).count(),'/users','person-check'),('Audit events',AuditLog.query.count(),'/audit','shield-check'),('AI interactions',AIInteraction.query.count(),'/audit','stars')]
        activity=AuditLog.query.order_by(AuditLog.created_at.desc()).limit(6).all()
    else:
        if student:
            subs=Submission.query.filter_by(student_id=student.id).all()
            submitted={s.request_id for s in subs if s.submitted_at is not None}
            cards=[('Profile completion',str(completion(student)[0])+'%','/profile','person-vcard'),('Pending requests',sum(r.id not in submitted for r in requests_),'/requests','ui-checks'),('Submitted',len(submitted),'/student/submissions','check2-circle'),('Documents',Document.query.filter_by(student_id=student.id).count(),'/documents','folder')]
        else:
            cards=[('Students',len(students),'/students','people'),('Assigned classes' if current_user.role=='TEACHER' else 'Classes',len(classes()),'/classes','collection'),('Active requirements',sum(r.status not in ('DRAFT','COMPLETED','ARCHIVED') for r in reqs),'/requirements','clipboard-data'),('Data requests',len(requests_),'/requests','ui-checks-grid')]
        ids=[current_user.id]+[s.user_id for s in students]
        if current_user.role=='ADMIN': ids += [u.id for u in User.query.filter_by(created_by=current_user.id).all()]
        activity=AuditLog.query.filter(AuditLog.actor_id.in_(ids)).order_by(AuditLog.created_at.desc()).limit(6).all()
    if current_user.role=='ADMIN':
        teacher_count=User.query.join(Role).filter(Role.name=='TEACHER',User.created_by==current_user.id).count()
        cards[1]=('Teachers',teacher_count,'/users','person-workspace')
    count=Counter(s.status for r in requests_ for s in r.submissions if not student or s.student_id==student.id)
    due=sorted([r for r in requests_ if r.status=='PUBLISHED'],key=lambda r:r.deadline)[:5]
    missing_blood=sum(not profile_data(s).get('blood_group') for s in students)
    return render_template('dashboard.html',title='Overview',cards=cards,activity=activity,requirements=reqs[-5:][::-1],deadlines=due,chart={'labels':list(count),'values':list(count.values())},missing_blood=missing_blood,student=student,stats=request_stats)

@bp.route('/notifications',methods=['GET','POST'])
@login_required
def notifications():
    if request.method=='POST':
        query=Notification.query.filter_by(user_id=current_user.id)
        if request.form.get('id'): query=query.filter_by(id=integer('id'))
        query.update({'read':True}); db.session.commit()
        return redirect('/notifications')
    items=Notification.query.filter_by(user_id=current_user.id).order_by(Notification.created_at.desc()).paginate(per_page=25)
    return render_template('notifications.html',title='Notifications',items=items)

@bp.get('/profile')
@roles('STUDENT')
def profile(): return redirect(f'/students/{my_student().id}')

@bp.get('/timeline')
@roles('STUDENT')
def timeline(): return redirect(f'/students/{my_student().id}#history')

@bp.get('/audit')
@roles('SUPER_ADMIN','ADMIN')
def audit_view():
    query=AuditLog.query
    if current_user.role=='ADMIN':
        ids=[current_user.id]+[u.id for u in User.query.filter_by(created_by=current_user.id).all()]+[s.user_id for s in students_query().all()]
        query=query.filter(AuditLog.actor_id.in_(ids))
    if request.args.get('q'): query=query.filter(AuditLog.action.ilike('%'+request.args['q']+'%'))
    return render_template('audit.html',title='Audit history',items=query.order_by(AuditLog.created_at.desc()).paginate(per_page=30))

@bp.route('/settings',methods=['GET','POST'])
@roles('SUPER_ADMIN')
def settings():
    if request.method=='POST':
        for key in ('independent_requests','allow_student_reset'):
            setting=db.session.get(SystemSetting,key)
            if not setting: setting=SystemSetting(key=key); db.session.add(setting)
            setting.value='true' if key in request.form else 'false'
        audit('System settings updated'); db.session.commit(); flash('Settings saved.','success')
        return redirect('/settings')
    return render_template('settings.html',title='System settings',settings={s.key:s.value for s in SystemSetting.query.all()})

@bp.get('/reports')
@roles('ADMIN','TEACHER')
def reports():
    from ai.analytics import charts
    query=requests_query().join(AcademicClass,DataRequest.class_id==AcademicClass.id)
    for key,column in [('department_id',AcademicClass.department_id),('class_id',DataRequest.class_id),('teacher_id',DataRequest.teacher_id)]:
        if request.args.get(key,type=int): query=query.filter(column==request.args.get(key,type=int))
    items=query.order_by(AcademicClass.department_id,AcademicClass.name,DataRequest.created_at.desc()).all()
    return render_template('reports.html',title='Reports & analytics',items=items,stats=request_stats,classes=classes(),charts=charts(students_query().all(),requirements_query().all(),items))

@bp.get('/reports/<int:item_id>')
@roles('ADMIN','TEACHER')
def report(item_id):
    from services.report_service import report_rows, export
    item=request_access(item_id)
    filters=dict(search=request.args.get('q',''),status=request.args.get('status',''),columns=request.args.getlist('columns'),sort=request.args.get('sort','name'))
    kind=request.args.get('format')
    if kind in ('xlsx','csv','pdf'):
        output=export(item,current_app.config['INSTITUTION_NAME'],kind,**filters)
        db.session.add(Report(request_id=item.id,generated_by=current_user.id,format=kind))
        audit('PDF export' if kind=='pdf' else 'Excel export' if kind=='xlsx' else 'CSV export','request',item.id,kind); db.session.commit()
        return send_file(output,as_attachment=True,download_name=f'academic-report-{item.id}.{kind}',mimetype='application/pdf' if kind=='pdf' else 'text/csv' if kind=='csv' else 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
    keys,rows=report_rows(item,**filters)
    all_keys=list(dict.fromkeys(['name','register_number','class','email']+[f.key for f in item.fields]))
    from services.report_service import filtered_stats
    return render_template('report.html',title=item.title+' · Report',item=item,keys=keys,rows=rows,all_keys=all_keys,stats=filtered_stats(rows))

@bp.get('/requirements/<int:item_id>/report')
@roles('ADMIN','TEACHER')
def requirement_report(item_id):
    from types import SimpleNamespace
    from services.report_service import requirement_rows, export_dataset, filtered_stats
    requirement=requirements_query().filter_by(id=item_id).first_or_404()
    filters=dict(search=request.args.get('q',''),status=request.args.get('status',''),columns=request.args.getlist('columns'),sort=request.args.get('sort','name'))
    keys,rows=requirement_rows(requirement,**filters)
    all_keys,_=requirement_rows(requirement)
    item=SimpleNamespace(id=requirement.id,title=requirement.title+' · Completion report',academic_class=requirement.academic_class,teacher=requirement.teacher,requirement=requirement)
    kind=request.args.get('format')
    if kind in ('xlsx','pdf','csv'):
        output=export_dataset(item,current_app.config['INSTITUTION_NAME'],kind,keys,rows)
        audit('PDF export' if kind=='pdf' else 'Excel export' if kind=='xlsx' else 'CSV export','requirement',requirement.id,kind);db.session.commit()
        return send_file(output,as_attachment=True,download_name=f'requirement-{item_id}.{kind}',mimetype='application/pdf' if kind=='pdf' else 'text/csv' if kind=='csv' else 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
    return render_template('report.html',title=item.title,item=item,keys=keys,rows=rows,all_keys=all_keys,stats=filtered_stats(rows))
