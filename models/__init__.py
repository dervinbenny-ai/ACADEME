from datetime import datetime, timezone
import secrets
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from extensions import db

def now():
    return datetime.now(timezone.utc).replace(tzinfo=None)

class Role(db.Model):
    __tablename__ = 'roles'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(24), unique=True, nullable=False)

class User(UserMixin, db.Model):
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(254), unique=True, nullable=False)
    phone = db.Column(db.String(16))
    name = db.Column(db.String(120), nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    role_id = db.Column(db.Integer, db.ForeignKey('roles.id'), nullable=False)
    role_record = db.relationship('Role')
    admin_account = db.relationship('AdminAccount', back_populates='user', uselist=False)
    teacher_account = db.relationship('TeacherAccount', back_populates='user', uselist=False)
    created_by = db.Column(db.Integer, db.ForeignKey('users.id'))
    active = db.Column(db.Boolean, default=True, nullable=False)
    first_login = db.Column(db.Boolean, default=True, nullable=False)
    last_login = db.Column(db.DateTime)
    failed_logins = db.Column(db.Integer, default=0)
    locked_until = db.Column(db.DateTime)
    created_at = db.Column(db.DateTime, default=now)
    @property
    def role(self): return self.role_record.name
    @property
    def is_active(self): return self.active
    def set_password(self, password): self.password_hash = generate_password_hash(password)
    def check_password(self, password): return check_password_hash(self.password_hash, password)

class AdminAccount(db.Model):
    __tablename__ = 'admin_accounts'
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), primary_key=True)
    created_at = db.Column(db.DateTime, default=now)
    user = db.relationship('User', back_populates='admin_account')

class TeacherAccount(db.Model):
    __tablename__ = 'teacher_accounts'
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), primary_key=True)
    created_at = db.Column(db.DateTime, default=now)
    user = db.relationship('User', back_populates='teacher_account')

class Department(db.Model):
    __tablename__ = 'departments'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), unique=True, nullable=False)
    admin_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    description = db.Column(db.Text, default='')
    hod = db.relationship('User', foreign_keys=[admin_id])

assignments = db.Table('teacher_class_assignments',
    db.Column('teacher_id', db.Integer, db.ForeignKey('users.id'), primary_key=True),
    db.Column('class_id', db.Integer, db.ForeignKey('academic_classes.id'), primary_key=True))

class AcademicClass(db.Model):
    __tablename__ = 'academic_classes'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    department_id = db.Column(db.Integer, db.ForeignKey('departments.id'), nullable=False)
    department = db.relationship('Department')
    semester = db.Column(db.String(24), default='')
    batch = db.Column(db.String(40), default='')
    teachers = db.relationship('User', secondary=assignments, backref='assigned_classes')
    __table_args__ = (db.UniqueConstraint('department_id', 'name'),)

class Student(db.Model):
    __tablename__ = 'students'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), unique=True, nullable=False)
    user = db.relationship('User', foreign_keys=[user_id])
    register_number = db.Column(db.String(60), unique=True, nullable=False)
    class_id = db.Column(db.Integer, db.ForeignKey('academic_classes.id'), nullable=False)
    academic_class = db.relationship('AcademicClass', backref='students')
    created_by = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    qr_token = db.Column(db.String(100), unique=True, default=lambda: secrets.token_urlsafe(32))
    profile = db.relationship('ProfileValue', backref='student', cascade='all, delete-orphan')

class ProfileValue(db.Model):
    __tablename__ = 'student_profiles'
    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey('students.id'), nullable=False)
    key = db.Column(db.String(80), nullable=False)
    value = db.Column(db.Text, nullable=False)
    updated_at = db.Column(db.DateTime, default=now, onupdate=now)
    __table_args__ = (db.UniqueConstraint('student_id', 'key'),)

class FieldLibrary(db.Model):
    __tablename__ = 'field_library'
    id = db.Column(db.Integer, primary_key=True)
    key = db.Column(db.String(80), unique=True, nullable=False)
    label = db.Column(db.String(120), nullable=False)
    category = db.Column(db.String(40), nullable=False)
    type = db.Column(db.String(30), default='text')
    options = db.Column(db.JSON, default=list)

class AdminRequirement(db.Model):
    __tablename__ = 'admin_requirements'
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text, default='')
    purpose = db.Column(db.Text, default='')
    requested_information = db.Column(db.Text, default='')
    notes = db.Column(db.Text, default='')
    admin_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    teacher_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    teacher = db.relationship('User', foreign_keys=[teacher_id])
    class_id = db.Column(db.Integer, db.ForeignKey('academic_classes.id'), nullable=False)
    academic_class = db.relationship('AcademicClass')
    deadline = db.Column(db.DateTime, nullable=False)
    priority = db.Column(db.String(20), default='NORMAL')
    status = db.Column(db.String(30), default='ASSIGNED')
    created_at = db.Column(db.DateTime, default=now)
    completed_at = db.Column(db.DateTime)

class DataRequest(db.Model):
    __tablename__ = 'data_requests'
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text, default='')
    purpose = db.Column(db.Text, default='')
    teacher_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    teacher = db.relationship('User')
    class_id = db.Column(db.Integer, db.ForeignKey('academic_classes.id'), nullable=False)
    academic_class = db.relationship('AcademicClass')
    requirement_id = db.Column(db.Integer, db.ForeignKey('admin_requirements.id'))
    requirement = db.relationship('AdminRequirement', backref='requests')
    deadline = db.Column(db.DateTime, nullable=False)
    allow_late = db.Column(db.Boolean, default=False)
    allow_edit = db.Column(db.Boolean, default=True)
    status = db.Column(db.String(24), default='DRAFT')
    created_at = db.Column(db.DateTime, default=now)
    published_at = db.Column(db.DateTime)
    fields = db.relationship('FormField', backref='data_request', order_by='FormField.position', cascade='all, delete-orphan')

class FormField(db.Model):
    __tablename__ = 'form_fields'
    id = db.Column(db.Integer, primary_key=True)
    request_id = db.Column(db.Integer, db.ForeignKey('data_requests.id'), nullable=False)
    key = db.Column(db.String(80), nullable=False)
    label = db.Column(db.String(120), nullable=False)
    type = db.Column(db.String(30), nullable=False)
    required = db.Column(db.Boolean, default=True)
    reuse = db.Column(db.String(20), default='auto')
    options = db.Column(db.JSON, default=list)
    validation = db.Column(db.JSON, default=dict)
    placeholder = db.Column(db.String(200), default='')
    help_text = db.Column(db.String(300), default='')
    position = db.Column(db.Integer, default=0)
    __table_args__ = (db.UniqueConstraint('request_id', 'key'),)

class RequestTarget(db.Model):
    __tablename__ = 'request_targets'
    id = db.Column(db.Integer, primary_key=True)
    request_id = db.Column(db.Integer, db.ForeignKey('data_requests.id'), nullable=False)
    student_id = db.Column(db.Integer, db.ForeignKey('students.id'), nullable=False)
    student = db.relationship('Student')
    data_request = db.relationship('DataRequest', backref='targets')
    __table_args__ = (db.UniqueConstraint('request_id', 'student_id'),)

class Submission(db.Model):
    __tablename__ = 'submissions'
    id = db.Column(db.Integer, primary_key=True)
    request_id = db.Column(db.Integer, db.ForeignKey('data_requests.id'), nullable=False)
    student_id = db.Column(db.Integer, db.ForeignKey('students.id'), nullable=False)
    student = db.relationship('Student')
    data_request = db.relationship('DataRequest', backref='submissions')
    status = db.Column(db.String(30), default='DRAFT')
    feedback = db.Column(db.Text, default='')
    late = db.Column(db.Boolean, default=False)
    submitted_at = db.Column(db.DateTime)
    reviewed_at = db.Column(db.DateTime)
    reviewer_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    revision_allowed = db.Column(db.Boolean, nullable=False, default=False, server_default=db.false())
    revision_fields = db.Column(db.JSON, default=list)
    revision_count = db.Column(db.Integer, nullable=False, default=0, server_default='0')
    profile_merge_status = db.Column(db.String(30), nullable=False, default='NOT_REVIEWED', server_default='NOT_REVIEWED')
    values = db.relationship('SubmissionValue', backref='submission', cascade='all, delete-orphan')
    __table_args__ = (db.UniqueConstraint('request_id', 'student_id'),)

class SubmissionValue(db.Model):
    __tablename__ = 'submission_values'
    id = db.Column(db.Integer, primary_key=True)
    submission_id = db.Column(db.Integer, db.ForeignKey('submissions.id'), nullable=False)
    key = db.Column(db.String(80), nullable=False)
    value = db.Column(db.Text, nullable=False)
    __table_args__ = (db.UniqueConstraint('submission_id', 'key'),)

class ProfileVersion(db.Model):
    __tablename__ = 'profile_versions'
    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey('students.id'), nullable=False)
    key = db.Column(db.String(80), nullable=False)
    old_value = db.Column(db.Text)
    new_value = db.Column(db.Text)
    actor_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    request_id = db.Column(db.Integer, db.ForeignKey('data_requests.id'))
    reason = db.Column(db.String(300), default='Verified submission')
    change_source = db.Column(db.String(40), nullable=False, default='SYSTEM_UPDATE', server_default='SYSTEM_UPDATE')
    approved_by = db.Column(db.Integer, db.ForeignKey('users.id'))
    actor = db.relationship('User', foreign_keys=[actor_id])
    approver = db.relationship('User', foreign_keys=[approved_by])
    created_at = db.Column(db.DateTime, default=now)

class Document(db.Model):
    __tablename__ = 'documents'
    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey('students.id'), nullable=False)
    student = db.relationship('Student')
    filename = db.Column(db.String(255), nullable=False)
    storage_name = db.Column(db.String(80), nullable=False)
    mime = db.Column(db.String(80), nullable=False)
    extracted_text = db.Column(db.Text, default='')
    ocr_status = db.Column(db.String(200), default='Not processed')
    created_at = db.Column(db.DateTime, default=now)

class Notification(db.Model):
    __tablename__ = 'notifications'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    title = db.Column(db.String(200), nullable=False)
    kind = db.Column(db.String(60), nullable=False, default='GENERAL', server_default='GENERAL')
    body = db.Column(db.Text, default='')
    link = db.Column(db.String(255), default='/dashboard')
    read = db.Column(db.Boolean, default=False)
    dedupe_key = db.Column(db.String(160), unique=True)
    created_at = db.Column(db.DateTime, default=now)

class AuditLog(db.Model):
    __tablename__ = 'audit_logs'
    id = db.Column(db.Integer, primary_key=True)
    actor_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    actor = db.relationship('User')
    action = db.Column(db.String(100), nullable=False)
    entity = db.Column(db.String(80), default='')
    entity_id = db.Column(db.Integer)
    details = db.Column(db.Text, default='')
    ip = db.Column(db.String(64), default='')
    created_at = db.Column(db.DateTime, default=now)

class MessageThread(db.Model):
    __tablename__ = 'message_threads'
    id = db.Column(db.Integer, primary_key=True)
    sender_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    recipient_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    sender = db.relationship('User', foreign_keys=[sender_id])
    recipient = db.relationship('User', foreign_keys=[recipient_id])
    subject = db.Column(db.String(200), nullable=False)
    created_at = db.Column(db.DateTime, default=now)
    messages = db.relationship('ChatMessage', backref='thread', order_by='ChatMessage.created_at')

class ChatMessage(db.Model):
    __tablename__ = 'chat_messages'
    id = db.Column(db.Integer, primary_key=True)
    thread_id = db.Column(db.Integer, db.ForeignKey('message_threads.id'), nullable=False)
    sender_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    sender = db.relationship('User')
    body = db.Column(db.Text, nullable=False)
    read = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=now)

class AcademicActivity(db.Model):
    __tablename__ = 'academic_activities'
    id = db.Column(db.Integer, primary_key=True)
    admin_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    department_id = db.Column(db.Integer, db.ForeignKey('departments.id'), nullable=False)
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text, default='')
    category = db.Column(db.String(60), default='Seminar')
    event_date = db.Column(db.DateTime, nullable=False)
    registration_open = db.Column(db.Boolean, default=True)

class ActivityRegistration(db.Model):
    __tablename__ = 'activity_registrations'
    id = db.Column(db.Integer, primary_key=True)
    activity_id = db.Column(db.Integer, db.ForeignKey('academic_activities.id'), nullable=False)
    student_id = db.Column(db.Integer, db.ForeignKey('students.id'), nullable=False)
    __table_args__ = (db.UniqueConstraint('activity_id', 'student_id'),)

class SystemSetting(db.Model):
    __tablename__ = 'system_settings'
    key = db.Column(db.String(80), primary_key=True)
    value = db.Column(db.Text, nullable=False)

class AIInteraction(db.Model):
    __tablename__ = 'ai_interactions'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    intent = db.Column(db.String(80), nullable=False)
    created_at = db.Column(db.DateTime, default=now)

class Report(db.Model):
    __tablename__ = 'reports'
    id = db.Column(db.Integer, primary_key=True)
    request_id = db.Column(db.Integer, db.ForeignKey('data_requests.id'), nullable=False)
    generated_by = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    format = db.Column(db.String(10), nullable=False)
    created_at = db.Column(db.DateTime, default=now)

class ProfileChangeRequest(db.Model):
    __tablename__ = 'profile_change_requests'
    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey('students.id'), nullable=False, index=True)
    student = db.relationship('Student')
    field = db.Column(db.String(80), nullable=False)
    existing_value = db.Column(db.Text, nullable=False)
    requested_value = db.Column(db.Text, nullable=False)
    reason = db.Column(db.Text, nullable=False)
    status = db.Column(db.String(20), nullable=False, default='PENDING')
    requested_at = db.Column(db.DateTime, default=now, nullable=False)
    reviewed_by = db.Column(db.Integer, db.ForeignKey('users.id'))
    reviewer = db.relationship('User', foreign_keys=[reviewed_by])
    reviewed_at = db.Column(db.DateTime)
    reviewer_note = db.Column(db.Text, default='')

class SubmissionChangeRequest(db.Model):
    __tablename__ = 'submission_change_requests'
    id = db.Column(db.Integer, primary_key=True)
    submission_id = db.Column(db.Integer, db.ForeignKey('submissions.id'), nullable=False, index=True)
    submission = db.relationship('Submission', backref='change_requests')
    student_id = db.Column(db.Integer, db.ForeignKey('students.id'), nullable=False)
    teacher_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    reason = db.Column(db.Text, nullable=False)
    requested_fields = db.Column(db.JSON, nullable=False)
    existing_values = db.Column(db.JSON, nullable=False)
    status = db.Column(db.String(20), nullable=False, default='PENDING')
    requested_at = db.Column(db.DateTime, default=now, nullable=False)
    reviewed_by = db.Column(db.Integer, db.ForeignKey('users.id'))
    reviewed_at = db.Column(db.DateTime)
    teacher_note = db.Column(db.Text, default='')

class SubmissionRevision(db.Model):
    __tablename__ = 'submission_revisions'
    id = db.Column(db.Integer, primary_key=True)
    submission_id = db.Column(db.Integer, db.ForeignKey('submissions.id'), nullable=False)
    submission = db.relationship('Submission', backref=db.backref('revisions', order_by='SubmissionRevision.number'))
    number = db.Column(db.Integer, nullable=False)
    values = db.Column(db.JSON, nullable=False)
    identity = db.Column(db.JSON, nullable=False)
    sources = db.Column(db.JSON, nullable=False)
    source = db.Column(db.String(40), nullable=False)
    created_by = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=now, nullable=False)
    __table_args__ = (db.UniqueConstraint('submission_id', 'number', name='uq_submission_revision'),)

class SubmissionReview(db.Model):
    __tablename__ = 'submission_reviews'
    id = db.Column(db.Integer, primary_key=True)
    submission_id = db.Column(db.Integer, db.ForeignKey('submissions.id'), nullable=False, index=True)
    submission = db.relationship('Submission', backref=db.backref('reviews', order_by='SubmissionReview.created_at'))
    revision_number = db.Column(db.Integer, nullable=False)
    status = db.Column(db.String(30), nullable=False)
    feedback = db.Column(db.Text, default='')
    fields = db.Column(db.JSON, default=list)
    reviewer_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    reviewer = db.relationship('User')
    created_at = db.Column(db.DateTime, default=now, nullable=False)

class ProfileMergeDecision(db.Model):
    __tablename__ = 'profile_merge_decisions'
    id = db.Column(db.Integer, primary_key=True)
    submission_id = db.Column(db.Integer, db.ForeignKey('submissions.id'), nullable=False, index=True)
    submission = db.relationship('Submission', backref='merge_decisions')
    revision_number = db.Column(db.Integer, nullable=False)
    field = db.Column(db.String(80), nullable=False)
    previous_value = db.Column(db.Text, nullable=False)
    submitted_value = db.Column(db.Text, nullable=False)
    decision = db.Column(db.String(20), nullable=False)
    reviewer_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=now, nullable=False)

class DeadlineExtensionRequest(db.Model):
    __tablename__ = 'deadline_extension_requests'
    id = db.Column(db.Integer, primary_key=True)
    data_request_id = db.Column(db.Integer, db.ForeignKey('data_requests.id'), nullable=False, index=True)
    data_request = db.relationship('DataRequest', backref='extension_requests')
    admin_requirement_id = db.Column(db.Integer, db.ForeignKey('admin_requirements.id'), nullable=False)
    requirement = db.relationship('AdminRequirement')
    requested_by_teacher_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    teacher = db.relationship('User', foreign_keys=[requested_by_teacher_id])
    current_deadline = db.Column(db.DateTime, nullable=False)
    proposed_deadline = db.Column(db.DateTime, nullable=False)
    approved_deadline = db.Column(db.DateTime)
    reason = db.Column(db.Text, nullable=False)
    pending_student_count = db.Column(db.Integer, nullable=False)
    status = db.Column(db.String(20), nullable=False, default='PENDING')
    hod_note = db.Column(db.Text, default='')
    requested_at = db.Column(db.DateTime, default=now, nullable=False)
    reviewed_at = db.Column(db.DateTime)
    reviewed_by = db.Column(db.Integer, db.ForeignKey('users.id'))

class DeadlineHistory(db.Model):
    __tablename__ = 'deadline_history'
    id = db.Column(db.Integer, primary_key=True)
    data_request_id = db.Column(db.Integer, db.ForeignKey('data_requests.id'), nullable=False)
    data_request = db.relationship('DataRequest', backref=db.backref('deadline_history', order_by='DeadlineHistory.created_at'))
    extension_id = db.Column(db.Integer, db.ForeignKey('deadline_extension_requests.id'))
    old_deadline = db.Column(db.DateTime, nullable=False)
    new_deadline = db.Column(db.DateTime, nullable=False)
    requested_by = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    approved_by = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    reason = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=now, nullable=False)
