from functools import wraps
from flask import abort
from flask_login import current_user, login_required
from sqlalchemy import false
from extensions import db
from models import *

def roles(*allowed):
    def decorator(fn):
        @wraps(fn)
        @login_required
        def wrapped(*args, **kwargs):
            if current_user.role not in allowed: abort(403)
            return fn(*args, **kwargs)
        return wrapped
    return decorator

def my_student():
    return Student.query.filter_by(user_id=current_user.id).first_or_404()

def classes():
    if current_user.role == 'ADMIN':
        return AcademicClass.query.join(Department).filter(Department.admin_id == current_user.id).all()
    if current_user.role == 'TEACHER': return current_user.assigned_classes
    if current_user.role == 'STUDENT': return [my_student().academic_class]
    return []

def class_access(class_id):
    obj = db.get_or_404(AcademicClass, class_id)
    if obj.id not in [c.id for c in classes()]: abort(403)
    return obj

def students_query():
    if current_user.role == 'STUDENT': return Student.query.filter_by(user_id=current_user.id)
    return Student.query.filter(Student.class_id.in_([c.id for c in classes()]))

def student_access(student_id):
    return students_query().filter_by(id=student_id).first_or_404()

def requirements_query():
    if current_user.role == 'ADMIN': return AdminRequirement.query.filter_by(admin_id=current_user.id)
    if current_user.role == 'TEACHER':
        return AdminRequirement.query.filter(AdminRequirement.teacher_id == current_user.id,
                                            AdminRequirement.status != 'DRAFT',
                                            AdminRequirement.class_id.in_([c.id for c in classes()]))
    return AdminRequirement.query.filter(false())

def requests_query():
    allowed = [c.id for c in classes()]
    if current_user.role == 'ADMIN': return DataRequest.query.filter(DataRequest.class_id.in_(allowed))
    if current_user.role == 'TEACHER':
        return DataRequest.query.filter(DataRequest.teacher_id == current_user.id, DataRequest.class_id.in_(allowed))
    if current_user.role == 'STUDENT':
        return DataRequest.query.join(RequestTarget).filter(RequestTarget.student_id == my_student().id, DataRequest.status != 'DRAFT')
    return DataRequest.query.filter(false())

def request_access(request_id):
    return requests_query().filter(DataRequest.id == request_id).first_or_404()

def manage_user(user_id):
    user = db.get_or_404(User, user_id)
    expected = {'SUPER_ADMIN': 'ADMIN', 'ADMIN': 'TEACHER', 'TEACHER': 'STUDENT'}.get(current_user.role)
    if user.role != expected: abort(403)
    if current_user.role == 'TEACHER':
        student = Student.query.filter_by(user_id=user.id).first_or_404()
        class_access(student.class_id)
    elif current_user.role == 'ADMIN' and user.created_by != current_user.id: abort(403)
    return user

def contacts():
    if current_user.role == 'ADMIN': return User.query.filter_by(created_by=current_user.id).filter(User.active.is_(True)).all()
    if current_user.role == 'TEACHER':
        ids = [s.user_id for s in students_query().all()] + [current_user.created_by]
        return User.query.filter(User.id.in_(ids), User.active.is_(True)).all()
    if current_user.role == 'STUDENT': return [u for u in my_student().academic_class.teachers if u.active]
    return []

def navigation():
    common = [('grid', 'Overview', '/dashboard')]
    r = current_user.role
    if r == 'SUPER_ADMIN': common += [('people','Administrators','/users'),('shield-check','System audit','/audit'),('sliders','System settings','/settings')]
    if r == 'ADMIN': common += [('buildings','Departments','/departments'),('collection','Classes & assignments','/classes'),('person-badge','Teachers','/users'),('people','Students','/students'),('clipboard-data','Data requirements','/requirements')]
    if r == 'TEACHER': common += [('collection','My classes','/classes'),('people','My students','/students'),('person-plus','Add student','/students/new'),('clipboard-data','HOD requirements','/requirements'),('ui-checks-grid','Data requests','/requests')]
    if r=='TEACHER': common += [('clipboard-check','Change requests','/change-requests')]
    if r in ('ADMIN','TEACHER'): common += [('calendar-plus','Deadline extensions','/deadline-extensions'),('bar-chart','Reports & analytics','/reports'),('chat-dots','Messages','/messages'),('calendar-event','Academic activities','/activities')]
    if r == 'STUDENT': common += [('person-vcard','Master profile','/profile'),('ui-checks-grid','My requests','/requests'),('folder2-open','Documents','/documents'),('clock-history','Timeline','/timeline'),('chat-dots','Messages','/messages'),('calendar-event','Academic activities','/activities'),('stars','AI assistant','/assistant')]
    if r=='STUDENT': common += [('journal-check','Submitted data','/student/submissions'),('arrow-repeat','Change requests','/student/changes')]
    if r == 'ADMIN': common += [('shield-check','Audit history','/audit')]
    common += [('bell','Notifications','/notifications'),('key','Password & security','/password')]
    return common
