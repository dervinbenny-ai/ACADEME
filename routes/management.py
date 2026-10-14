from flask import Blueprint, render_template, request, redirect, flash, abort
from flask_login import current_user
from extensions import db
from models import *
from services.access import roles, classes, class_access, students_query, student_access, manage_user
from services.common import required, integer, new_user, audit, email, phone, password_valid, profile_data, completion, set_profile
from services.profile_service import update_profile_value, EDITABLE, SENSITIVE, LOCKED

bp = Blueprint('management', __name__)

@bp.route('/users')
@roles('SUPER_ADMIN','ADMIN')
def users():
    role = 'ADMIN' if current_user.role == 'SUPER_ADMIN' else 'TEACHER'
    query = User.query.join(Role).filter(Role.name == role)
    if current_user.role == 'ADMIN': query = query.filter(User.created_by == current_user.id)
    term = request.args.get('q','').strip()
    if term: query = query.filter(User.name.ilike(f'%{term}%') | User.email.ilike(f'%{term}%'))
    return render_template('users.html',title='Administrators' if role == 'ADMIN' else 'Teachers', users=query.order_by(User.name).paginate(per_page=20), role=role)

@bp.route('/users/new',methods=['GET','POST'])
@roles('SUPER_ADMIN','ADMIN')
def user_new():
    role = 'ADMIN' if current_user.role == 'SUPER_ADMIN' else 'TEACHER'
    if request.method == 'POST':
        new_user(role)
        db.session.commit()
        flash('Account created. Share the temporary credentials securely. A password change is required on first login.','success')
        return redirect('/users')
    return render_template('user_form.html',title=f'Create {role.lower()}', user=None, student=None, classes=[])

@bp.route('/users/<int:user_id>/edit',methods=['GET','POST'])
@roles('SUPER_ADMIN','ADMIN','TEACHER')
def user_edit(user_id):
    user = manage_user(user_id)
    student = Student.query.filter_by(user_id=user.id).first() if user.role == 'STUDENT' else None
    if request.method == 'POST':
        name=required('name',120);email_value=email(required('email',254))
        if student:
            update_profile_value(student,'name',name,'TEACHER_UPDATE','Teacher account edit')
            update_profile_value(student,'email',email_value,'TEACHER_UPDATE','Teacher account edit')
        else:
            user.name=name;user.email=email_value
            phone_value=request.form.get('phone','').strip()
            user.phone=phone(phone_value) if phone_value else None
        user.username = required('username',80).lower()
        if student:
            update_profile_value(student,'register_number',required('register_number',60).upper(),'TEACHER_UPDATE','Teacher account edit')
            # Class transfers are deliberately separate from profile edits.
            for key in ('phone','roll_number','admission_year'):
                update_profile_value(student,key,request.form.get(key,'').strip(),'TEACHER_UPDATE','Teacher profile edit')
        audit('Account updated','user',user.id)
        db.session.commit()
        flash('Account updated.','success')
        return redirect('/students' if student else '/users')
    return render_template('user_form.html',title='Edit account',user=user,student=student,classes=classes(), data=profile_data(student) if student else {})

@bp.post('/users/<int:user_id>/toggle')
@roles('SUPER_ADMIN','ADMIN','TEACHER')
def user_toggle(user_id):
    user = manage_user(user_id)
    user.active = not user.active
    audit('Account activated' if user.active else 'Account deactivated','user',user.id)
    db.session.commit()
    flash('Account status updated.','success')
    return redirect('/students' if user.role == 'STUDENT' else '/users')

@bp.post('/users/<int:user_id>/reset')
@roles('SUPER_ADMIN','ADMIN','TEACHER')
def user_reset(user_id):
    user = manage_user(user_id)
    setting = db.session.get(SystemSetting,'allow_student_reset')
    if current_user.role == 'TEACHER' and setting and setting.value != 'true': abort(403)
    password = required('password',128)
    if not password_valid(password): abort(400,'Use at least 12 characters including letters and numbers.')
    user.set_password(password)
    user.first_login = True
    user.failed_logins = 0
    user.locked_until = None
    audit('Password reset','user',user.id)
    db.session.commit()
    flash('Temporary password set. Share it securely with the account owner.','success')
    return redirect('/students' if user.role == 'STUDENT' else '/users')

@bp.route('/departments',methods=['GET','POST'])
@roles('ADMIN')
def departments():
    if request.method == 'POST':
        obj = Department.query.filter_by(id=request.form.get('id',type=int),admin_id=current_user.id).first_or_404() if request.form.get('id') else Department(admin_id=current_user.id)
        obj.name = required('name',120)
        obj.description = request.form.get('description','')[:3000]
        db.session.add(obj)
        audit('Department saved','department',obj.id)
        db.session.commit()
        flash('Department saved.','success')
        return redirect('/departments')
    edit = Department.query.filter_by(id=request.args.get('edit',type=int),admin_id=current_user.id).first_or_404() if request.args.get('edit') else None
    return render_template('departments.html',title='Departments',items=Department.query.filter_by(admin_id=current_user.id).all(),edit=edit)

@bp.route('/classes',methods=['GET','POST'])
@roles('ADMIN','TEACHER')
def class_list():
    if request.method == 'POST':
        if current_user.role != 'ADMIN': abort(403)
        department = Department.query.filter_by(id=integer('department_id'),admin_id=current_user.id).first_or_404()
        obj = class_access(integer('id')) if request.form.get('id') else AcademicClass()
        previous_profiles={student.id:profile_data(student) for student in obj.students} if obj.id else {}
        obj.name = required('name',120)
        obj.department_id = department.id
        obj.semester = request.form.get('semester','')[:24]
        obj.batch = request.form.get('batch','')[:40]
        teacher_ids = request.form.getlist('teachers', type=int)
        teachers = User.query.join(Role).filter(User.id.in_(teacher_ids),Role.name=='TEACHER',User.created_by==current_user.id,User.active.is_(True)).all()
        if len(teachers) != len(set(teacher_ids)): abort(403)
        obj.teachers = teachers
        db.session.add(obj)
        db.session.flush()
        if previous_profiles:
            db.session.expire(obj,['department'])
            for student in obj.students:
                updated=profile_data(student)
                for key in ('class','department','semester','batch'):
                    previous=previous_profiles[student.id].get(key,'')
                    if previous!=updated.get(key,''):
                        db.session.add(ProfileVersion(student_id=student.id,key=key,old_value=previous,new_value=updated.get(key,''),actor_id=current_user.id,change_source='SYSTEM_UPDATE',reason='Institution updated academic class',approved_by=current_user.id))
        audit('Class and teacher assignments saved','class',obj.id)
        db.session.commit()
        flash('Class and assignments saved.','success')
        return redirect('/classes')
    edit = class_access(request.args.get('edit',type=int)) if request.args.get('edit') else None
    teachers = User.query.join(Role).filter(Role.name=='TEACHER',User.created_by==current_user.id,User.active.is_(True)).all() if current_user.role == 'ADMIN' else []
    return render_template('classes.html',title='Classes & assignments' if current_user.role=='ADMIN' else 'My classes',items=classes(),edit=edit,teachers=teachers,departments=Department.query.filter_by(admin_id=current_user.id).all())

@bp.get('/students')
@roles('ADMIN','TEACHER')
def students():
    query = students_query().join(User, Student.user_id==User.id).join(AcademicClass, Student.class_id==AcademicClass.id).join(Department, AcademicClass.department_id==Department.id)
    term = request.args.get('q','').strip()
    if term:
        from ai.smart_search import apply_search
        query,recognized=apply_search(query,term,classes())
        if not recognized: query = query.filter(User.name.ilike(f'%{term}%') | User.email.ilike(f'%{term}%') | Student.register_number.ilike(f'%{term}%'))
    if request.args.get('class_id',type=int): query = query.filter(Student.class_id==request.args.get('class_id',type=int))
    if request.args.get('department_id',type=int): query=query.filter(AcademicClass.department_id==request.args.get('department_id',type=int))
    if request.args.get('teacher_id',type=int): query=query.filter(AcademicClass.teachers.any(User.id==request.args.get('teacher_id',type=int)))
    if request.args.get('active') in ('true','false'): query=query.filter(User.active == (request.args['active']=='true'))
    if request.args.get('missing'):
        key = request.args['missing']
        if key in ('name','email','register_number'): query = query.filter(False)
        else: query=query.filter(~Student.profile.any((ProfileValue.key==key) & (ProfileValue.value!='')))
    if request.args.get('completion') in ('complete','incomplete'):
        complete=request.args['completion']=='complete'
        ids=[student.id for student in query.all() if (completion(student)[0]==100)==complete]
        query=query.filter(Student.id.in_(ids))
    scoped_classes=sorted(classes(),key=lambda c:(c.department.name.casefold(),c.name.casefold(),c.id))
    departments={c.department_id:c.department for c in scoped_classes}
    teachers={u.id:u for c in scoped_classes for u in c.teachers}
    counts=dict(db.session.query(Student.class_id,db.func.count(Student.id)).filter(Student.class_id.in_([c.id for c in scoped_classes])).group_by(Student.class_id).all())
    return render_template('students.html',title='Students',items=query.order_by(Department.name,AcademicClass.name,Student.register_number,User.name,Student.id).paginate(per_page=20),classes=scoped_classes,departments=departments.values(),teachers=teachers.values(),counts=counts,completion=completion)

@bp.route('/students/new',methods=['GET','POST'])
@roles('TEACHER')
def student_new():
    if request.method == 'POST':
        obj_class = class_access(integer('class_id'))
        phone_value=request.form.get('phone','').strip()
        if phone_value: phone_value=phone(phone_value)
        user = new_user('STUDENT')
        student = Student(user=user,academic_class=obj_class,register_number=required('register_number',60).upper(),created_by=current_user.id)
        db.session.add(student)
        db.session.flush()
        if phone_value: set_profile(student,'phone',phone_value,'Initial teacher record')
        for key in ('roll_number','admission_year'):
            set_profile(student,key,request.form.get(key,'').strip(),'Initial teacher record')
        audit('Student created','student',student.id)
        db.session.commit()
        flash('Student and master profile created. Share the temporary credentials securely.','success')
        return redirect('/students')
    return render_template('user_form.html',title='Add student',user=None,student=True,classes=classes(),data={})

@bp.get('/students/<int:student_id>')
@roles('ADMIN','TEACHER','STUDENT')
def student_detail(student_id):
    student = student_access(student_id)
    submissions=Submission.query.filter(Submission.student_id==student.id,Submission.submitted_at.isnot(None)).order_by(Submission.submitted_at.desc()).all()
    pending=sum(not any(s.request_id==t.request_id for s in submissions) for t in RequestTarget.query.filter_by(student_id=student.id).all() if t.data_request.status=='PUBLISHED')
    return render_template('profile.html',title='Master student profile',student=student,data=profile_data(student),completion=completion(student),
        history=ProfileVersion.query.filter_by(student_id=student.id).order_by(ProfileVersion.created_at.desc(),ProfileVersion.id.desc()).all(),
        submissions=submissions,pending=pending,documents=Document.query.filter_by(student_id=student.id).all(),
        profile_changes=ProfileChangeRequest.query.filter_by(student_id=student.id).order_by(ProfileChangeRequest.requested_at.desc()).all(),
        submission_changes=SubmissionChangeRequest.query.filter_by(student_id=student.id).order_by(SubmissionChangeRequest.requested_at.desc()).all(),editable_fields=EDITABLE,sensitive_fields=SENSITIVE,locked_fields=LOCKED)
