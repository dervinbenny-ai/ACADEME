"""Small, authenticated UI adapters using the existing access scopes."""
from flask import Blueprint, jsonify, request, abort
from flask_login import login_required, current_user
from sqlalchemy import or_
from extensions import db
from models import User, Role, Student, DataRequest, Notification, AdminRequirement, Submission
from services.access import classes, students_query, requests_query, requirements_query, my_student
from services.common import completion, profile_data

bp = Blueprint('workspace', __name__)

@bp.app_context_processor
def dashboard_context():
    if request.endpoint != 'core.dashboard' or not current_user.is_authenticated:
        return {}
    reqs = requirements_query().all()
    scoped_requests = requests_query().all()
    return {'workspace': {
        'new_requirements': sum(item.status == 'ASSIGNED' for item in reqs),
        'active_requirements': sum(item.status not in ('DRAFT', 'COMPLETED', 'ARCHIVED') for item in reqs),
        'pending_verification': sum(sub.status in ('SUBMITTED', 'RESUBMITTED', 'UNDER_REVIEW') for item in scoped_requests for sub in item.submissions),
        'profile_completion': completion(my_student())[0] if current_user.role == 'STUDENT' else 0,
    }}

@bp.get('/api/workspace/search')
@login_required
def search():
    text = request.args.get('q', '').strip()[:100]
    if len(text) < 2:
        return jsonify(items=[])
    pattern = '%' + text.replace('\\', '\\\\').replace('%', '\\%').replace('_', '\\_') + '%'
    items = []
    def add(label, url, kind, icon):
        items.append(dict(label=label, url=url, kind=kind, icon=icon))
    if current_user.role in ('ADMIN', 'TEACHER'):
        students = students_query().join(User, Student.user_id == User.id).filter(or_(User.name.ilike(pattern, escape='\\'), Student.register_number.ilike(pattern, escape='\\'), User.email.ilike(pattern, escape='\\'))).limit(6).all()
        for student in students:
            add(student.user.name, f'/students/{student.id}', f'Student · {student.register_number}', 'person')
        for academic_class in classes():
            if text.casefold() in academic_class.name.casefold():
                add(academic_class.name, '/classes', 'Class', 'collection')
        for requirement in requirements_query().filter(AdminRequirement.title.ilike(pattern, escape='\\')).limit(5):
            add(requirement.title, f'/requirements/{requirement.id}', 'HOD requirement', 'clipboard-data')
    if current_user.role in ('SUPER_ADMIN', 'ADMIN'):
        role = 'ADMIN' if current_user.role == 'SUPER_ADMIN' else 'TEACHER'
        query = User.query.join(Role).filter(Role.name == role)
        if current_user.role == 'ADMIN':
            query = query.filter(User.created_by == current_user.id)
        for user in query.filter(or_(User.name.ilike(pattern, escape='\\'), User.email.ilike(pattern, escape='\\'))).limit(5):
            add(user.name, f'/users/{user.id}/edit', role.title(), 'person-workspace')
    for item in requests_query().filter(DataRequest.title.ilike(pattern, escape='\\')).limit(6):
        add(item.title, f'/requests/{item.id}', 'Data request', 'ui-checks-grid')
    if current_user.role == 'TEACHER':
        ids = requests_query().with_entities(DataRequest.id).subquery()
        query = Submission.query.join(Student).join(User, Student.user_id == User.id).filter(Submission.request_id.in_(db.select(ids.c.id)), Submission.status != 'DRAFT', User.name.ilike(pattern, escape='\\'))
        for sub in query.limit(4):
            add(sub.student.user.name, f'/submissions/{sub.id}', f'Submission · {sub.data_request.title}', 'clipboard-check')
    if current_user.role == 'STUDENT':
        for key, value in profile_data(my_student()).items():
            if text.casefold() in key.replace('_', ' ').casefold():
                add(key.replace('_', ' ').title(), '/profile', 'My profile field', 'person-vcard')
    return jsonify(items=items[:24])

@bp.get('/api/workspace/notifications')
@login_required
def notifications():
    query = Notification.query.filter_by(user_id=current_user.id)
    items = query.order_by(Notification.created_at.desc(), Notification.id.desc()).limit(8).all()
    return jsonify(unread=query.filter_by(read=False).count(), latest_id=max((n.id for n in items), default=0), items=[dict(id=n.id, title=n.title, body=n.body, link=n.link if n.link.startswith('/') and not n.link.startswith('//') else '/notifications', read=n.read, created_at=n.created_at.isoformat()+'Z') for n in items])

@bp.post('/api/workspace/notifications/read')
@login_required
def read_notifications():
    payload = request.get_json(silent=True)
    if not isinstance(payload, dict):
        abort(400)
    query = Notification.query.filter_by(user_id=current_user.id)
    if 'id' in payload:
        if not isinstance(payload['id'], int) or isinstance(payload['id'], bool):
            abort(400)
        item = query.filter_by(id=payload['id']).first_or_404()
        item.read = True
    else:
        query.update({'read': True})
    db.session.commit()
    return jsonify(ok=True, unread=query.filter_by(read=False).count())
