from pathlib import Path
from datetime import datetime
import sqlalchemy as sa
from flask_migrate import upgrade
from app import create_app
from extensions import db

def test_additive_upgrade_preserves_legacy_data(tmp_path):
    root=Path(__file__).resolve().parents[1]
    app=create_app({'TESTING':True,'SECRET_KEY':'migration-test-only','SQLALCHEMY_DATABASE_URI':'sqlite:///'+(tmp_path/'legacy.db').as_posix(),'UPLOAD_FOLDER':str(tmp_path/'uploads')})
    with app.app_context():
        upgrade(directory=str(root/'migrations'),revision='7471d89f7d7a')
        meta=sa.MetaData();meta.reflect(bind=db.engine)
        with db.engine.begin() as connection:
            def insert(table,**values): connection.execute(meta.tables[table].insert().values(**values))
            insert('roles',id=1,name='STUDENT')
            insert('roles',id=2,name='ADMIN')
            insert('roles',id=3,name='TEACHER')
            insert('users',id=1,username='legacy',email='legacy@example.com',name='Legacy Student',password_hash='preserve-hash',role_id=1,active=True,first_login=False)
            insert('users',id=2,username='legacy-admin',email='admin@example.com',name='Legacy Admin',password_hash='preserve-hash',role_id=2,active=True,first_login=False)
            insert('users',id=3,username='legacy-teacher',email='teacher@example.com',name='Legacy Teacher',password_hash='preserve-hash',role_id=3,active=True,first_login=False)
            insert('departments',id=1,name='Legacy department',admin_id=1)
            insert('academic_classes',id=1,name='Legacy class',department_id=1)
            insert('students',id=1,user_id=1,register_number='LEGACY001',class_id=1,created_by=1)
            insert('student_profiles',student_id=1,key='skills',value='Current profile value')
            insert('data_requests',id=1,title='Legacy request',teacher_id=1,class_id=1,deadline=datetime(2026,1,1),status='PUBLISHED')
            insert('form_fields',request_id=1,key='skills',label='Skills',type='text')
            insert('submissions',id=1,request_id=1,student_id=1,status='VERIFIED',submitted_at=datetime(2025,12,1))
            insert('submission_values',submission_id=1,key='skills',value='Original submitted value')
            insert('profile_versions',student_id=1,key='skills',old_value='Old',new_value='Current profile value',actor_id=1,reason='Verified submission')
            insert('notifications',user_id=1,title='Old notification',read=False)
        upgrade(directory=str(root/'migrations'))
        from models import AdminAccount, TeacherAccount, User, Student, Submission, ProfileValue, SubmissionRevision, ProfileVersion, Notification
        assert User.query.filter_by(id=1).one().password_hash=='preserve-hash'
        assert AdminAccount.query.order_by(AdminAccount.user_id).all()[0].user_id==2
        assert TeacherAccount.query.one().user_id==3
        assert Student.query.one().register_number=='LEGACY001'
        assert ProfileValue.query.one().value=='Current profile value'
        sub=Submission.query.one()
        assert sub.status=='VERIFIED' and sub.profile_merge_status=='LEGACY_REVIEWED' and not sub.revision_allowed
        revision=SubmissionRevision.query.one()
        assert revision.values=={'skills':'Original submitted value'}
        assert revision.source=='LEGACY_STORED' and revision.number==1
        assert ProfileVersion.query.one().change_source=='VERIFIED_FORM_SUBMISSION'
        assert Notification.query.one().kind=='GENERAL'
        upgrade(directory=str(root/'migrations'))
        assert SubmissionRevision.query.count()==1
        from alembic.autogenerate import compare_metadata
        from alembic.migration import MigrationContext
        with db.engine.connect() as connection:
            assert compare_metadata(MigrationContext.configure(connection),db.metadata)==[]


def test_database_reset_leaves_only_super_admin(tmp_path):
    root=Path(__file__).resolve().parents[1]
    app=create_app({'TESTING':True,'SECRET_KEY':'reset-test-only','SQLALCHEMY_DATABASE_URI':'sqlite:///'+(tmp_path/'reset.db').as_posix(),'UPLOAD_FOLDER':str(tmp_path/'uploads')})
    from scripts.reset_database import reset_database
    from models import AdminAccount, Role, Student, TeacherAccount, User
    with app.app_context():
        db.create_all()
    reset_database(app,'new-admin','new-admin@example.com','New Admin','StrongPass12345')
    with app.app_context():
        assert User.query.count()==1
        user=User.query.one()
        assert user.username=='new-admin' and user.role=='SUPER_ADMIN'
        assert user.check_password('StrongPass12345')
        assert AdminAccount.query.count()==1
        assert TeacherAccount.query.count()==0 and Student.query.count()==0
        assert Role.query.count()==4
