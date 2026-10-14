import io
from datetime import timedelta
from openpyxl import load_workbook
from pypdf import PdfReader
from extensions import db
from models import *
from services.common import profile_data
from test_workflow import setup_hierarchy, create_request, login, logout, post, PASSWORD

def as_student(client):
    logout(client);login(client,'student','rahul',change=True)

def as_teacher(client):
    logout(client);login(client,'teacher','arun','ChangedPass@12345')

def as_hod(client):
    logout(client);login(client,'admin','hod','ChangedPass@12345')

def test_direct_profile_edits_locked_fields_and_version_history(client):
    cls,teacher,req,student=setup_hierarchy(client);as_student(client)
    post(client,'/student/profile/edit',{'phone':'+919123456780','skills':'Python, Flask','bio':'Interested in research.'})
    db.session.expire_all()
    assert profile_data(student)['phone']=='+919123456780'
    assert ProfileVersion.query.filter_by(student_id=student.id,key='phone',change_source='STUDENT_DIRECT_EDIT').count()==1
    assert AuditLog.query.filter_by(action='Master profile updated',entity_id=student.id).count()>=1
    for key in ['department','department_id','class','semester','register_number','name','email','student_id']:
        assert client.post('/student/profile/edit',data={key:'forged'}).status_code==403
    assert client.post('/student/profile/edit',data={'portfolio':'javascript:alert(1)'}).status_code==400
    post(client,'/student/profile/edit',{'bio':''})
    assert ProfileVersion.query.filter_by(student_id=student.id,key='bio',new_value='').count()==1

def test_official_profile_change_approval_rejection_and_stale_protection(client):
    cls,teacher,req,student=setup_hierarchy(client);as_student(client)
    post(client,'/student/profile/change',{'field':'name','requested_value':'Rahul Nair','reason':'Use my official full name.'})
    change=ProfileChangeRequest.query.one()
    assert student.user.name=='Rahul'
    assert Notification.query.filter_by(user_id=teacher.id,kind='MASTER_PROFILE_CHANGE_REQUEST').count()==1
    assert client.post('/student/profile/change',data={'field':'name','requested_value':'Another name','reason':'Duplicate'}).status_code==409
    as_teacher(client);post(client,f'/profile-changes/{change.id}',{'action':'APPROVED','note':'Checked college record.'})
    db.session.expire_all();assert student.user.name=='Rahul Nair'
    version=ProfileVersion.query.filter_by(key='name').one()
    assert version.change_source=='STUDENT_CHANGE_REQUEST' and version.approved_by==teacher.id
    assert client.post(f'/profile-changes/{change.id}',data={'action':'APPROVED'}).status_code==409
    logout(client);login(client,'student','rahul','ChangedPass@12345')
    post(client,'/student/profile/change',{'field':'dob','requested_value':'2005-01-02','reason':'Correct date.'})
    second=ProfileChangeRequest.query.order_by(ProfileChangeRequest.id.desc()).first()
    as_teacher(client);post(client,f'/profile-changes/{second.id}',{'action':'REJECTED','note':'Please provide the correct date.'})
    assert not profile_data(student).get('dob')
    assert Notification.query.filter_by(user_id=student.user_id,kind='PROFILE_CHANGE_REJECTED').count()==1

def test_one_time_submission_snapshot_and_selective_merge(client):
    cls,teacher,req,student=setup_hierarchy(client)
    fields=[{'key':key,'label':key,'type':'textarea','reuse':'update'} for key in ['skills','placement_status','temporary_accommodation','event_attendance','internship_company']]
    item=create_request(client,cls,req,fields);as_student(client)
    values={'skills':'Python','placement_status':'Not placed','temporary_accommodation':'Hostel 12','event_attendance':'Yes','internship_company':'ABC'}
    post(client,f'/requests/{item.id}/submit',dict(values,action='submit'))
    sub=Submission.query.one()
    assert client.post(f'/requests/{item.id}/submit',data=dict(values,action='submit')).status_code==403
    assert client.post(f'/requests/{item.id}/submit',data=dict(values,action='draft')).status_code==403
    page=client.get(f'/requests/{item.id}/submit').data
    assert b'Submission Completed' in page and b'View Submitted Data' in page
    assert b'Submit for verification' not in page
    page=client.get(f'/student/submissions/{sub.id}').data
    assert b'Hostel 12' in page and b'Python' in page
    as_teacher(client);post(client,f'/submissions/{sub.id}',{'action':'VERIFIED'})
    assert sub.status=='VERIFIED' and not profile_data(student).get('skills')
    post(client,f'/submissions/{sub.id}/profile-review',{'action':'apply','selected':['skills','placement_status'],'baseline_skills':'','baseline_placement_status':''})
    db.session.expire_all()
    assert sub.profile_merge_status=='PARTIALLY_APPLIED'
    assert profile_data(student)['skills']=='Python' and profile_data(student)['placement_status']=='Not placed'
    assert all(key not in profile_data(student) for key in ('temporary_accommodation','event_attendance','internship_company'))
    assert ProfileMergeDecision.query.filter_by(submission_id=sub.id,decision='accept').count()==2
    logout(client);login(client,'student','rahul','ChangedPass@12345')
    post(client,'/student/profile/edit',{'skills':'Later profile edit'})
    page=client.get(f'/student/submissions/{sub.id}').data
    assert b'Python' in page and b'Later profile edit' not in page
    assert sub.revisions[0].values['skills']=='Python'

def test_approved_submission_change_is_field_scoped_single_use_and_keeps_snapshots(client):
    cls,teacher,req,student=setup_hierarchy(client)
    item=create_request(client,cls,req,[{'key':'skills','label':'Skills','type':'textarea'},{'key':'cgpa','label':'CGPA','type':'decimal'}]);as_student(client)
    post(client,f'/requests/{item.id}/submit',{'skills':'Python','cgpa':'8.3','action':'submit'});sub=Submission.query.one()
    post(client,f'/student/submissions/{sub.id}/change',{'fields':['skills'],'reason':'Add Flask to skills.'});change=SubmissionChangeRequest.query.one()
    assert Notification.query.filter_by(user_id=teacher.id,kind='STUDENT_SUBMISSION_CHANGE_REQUEST').count()==1
    as_teacher(client);post(client,f'/submission-changes/{change.id}',{'action':'APPROVED','note':'Update skills only.'})
    assert sub.revision_allowed and sub.status=='REVISION_ALLOWED'
    logout(client);login(client,'student','rahul','ChangedPass@12345')
    assert client.post(f'/requests/{item.id}/submit',data={'skills':'Flask','cgpa':'10','action':'revise'}).status_code==403
    post(client,f'/requests/{item.id}/submit',{'skills':'Python, Flask','action':'revise'})
    assert sub.status=='RESUBMITTED' and not sub.revision_allowed and change.status=='COMPLETED'
    assert {v.key:v.value for v in sub.values}=={'skills':'Python, Flask','cgpa':'8.3'}
    assert len(sub.revisions)==2 and sub.revisions[0].values['skills']=='Python'
    assert client.post(f'/requests/{item.id}/submit',data={'skills':'Third','action':'revise'}).status_code==403
    as_teacher(client);post(client,f'/submissions/{sub.id}',{'action':'VERIFIED'})
    post(client,f'/submissions/{sub.id}/profile-review',{'action':'skip'})
    assert sub.status=='VERIFIED' and sub.profile_merge_status=='SKIPPED'

def test_rejection_is_locked_and_correction_is_controlled(client):
    cls,teacher,req,student=setup_hierarchy(client)
    item=create_request(client,cls,req,[{'key':'skills','label':'Skills','type':'textarea'}]);as_student(client)
    post(client,f'/requests/{item.id}/submit',{'skills':'Python'});sub=Submission.query.one();as_teacher(client)
    post(client,f'/submissions/{sub.id}',{'action':'REJECTED','feedback':'Incorrect information.'})
    logout(client);login(client,'student','rahul','ChangedPass@12345')
    assert client.post(f'/requests/{item.id}/submit',data={'skills':'Flask'}).status_code==403
    post(client,f'/student/submissions/{sub.id}/change',{'fields':'skills','reason':'Correct my information.'})
    change=SubmissionChangeRequest.query.one();as_teacher(client)
    post(client,f'/submission-changes/{change.id}',{'action':'REJECTED','note':'Please discuss first.'})
    assert not sub.revision_allowed

def test_extension_approval_notifies_only_never_submitted_students_and_exports(client):
    cls,teacher,req,student=setup_hierarchy(client)
    post(client,'/students/new',{'name':'Pending student','username':'pending','email':'pending@example.com','password':PASSWORD,'register_number':'MCA002','class_id':cls.id})
    pending=Student.query.filter_by(register_number='MCA002').one()
    item=create_request(client,cls,req,[{'key':'skills','label':'Skills','type':'textarea'}]);as_student(client)
    post(client,f'/requests/{item.id}/submit',{'skills':'Python'});sub=Submission.query.one()
    item.deadline=now()-timedelta(days=1);db.session.commit();old=item.deadline
    as_teacher(client)
    assert client.post(f'/requests/{item.id}',data={'action':'extend','deadline':(now()+timedelta(days=2)).isoformat(),'reason':'Direct bypass'}).status_code==403
    post(client,f'/requests/{item.id}/extension',{'proposed_deadline':(now()+timedelta(days=2)).isoformat(),'reason':'Training week.'})
    change=DeadlineExtensionRequest.query.one();assert change.pending_student_count==1
    assert item.deadline==old
    as_hod(client);post(client,f'/deadline-extensions/{change.id}',{'action':'APPROVED','note':'Approved.'})
    assert item.deadline==change.proposed_deadline and DeadlineHistory.query.count()==1
    assert Notification.query.filter_by(user_id=teacher.id,kind='DEADLINE_EXTENSION_APPROVED').count()==1
    assert Notification.query.filter_by(user_id=pending.user_id,kind='DEADLINE_EXTENDED').count()==1
    assert Notification.query.filter_by(user_id=student.user_id,kind='DEADLINE_EXTENDED').count()==0
    assert client.post(f'/deadline-extensions/{change.id}',data={'action':'APPROVED'}).status_code==409
    for role in ('hod','teacher'):
        if role=='teacher': as_teacher(client)
        for path in (f'/reports/{item.id}',f'/requirements/{req.id}/report'):
            result=client.get(path+'?format=xlsx&status=SUBMITTED&q=Rahul')
            assert result.status_code==200
            workbook=load_workbook(io.BytesIO(result.data))
            sheet=workbook['Collected data'];assert sheet.max_row==8
            assert 'Rahul' in str([cell.value for cell in sheet[8]])
            result=client.get(path+'?format=pdf&status=SUBMITTED&q=Rahul')
            assert result.status_code==200 and result.mimetype=='application/pdf'
            reader=PdfReader(io.BytesIO(result.data));text=''.join(p.extract_text() for p in reader.pages)
            assert 'Rahul' in text and 'Python' in text and 'Pending student' not in text
            assert 'Page 1' in text

def test_legacy_draft_values_are_not_exported_as_collected_responses():
    from types import SimpleNamespace as Record
    from services.report_service import report_rows, filtered_stats
    student=Record(id=1,register_number='MCA001',user=Record(name='Draft student',email='draft@example.com'),academic_class=Record(name='S4 MCA'))
    draft=Record(student_id=1,status='DRAFT',submitted_at=now(),values=[Record(key='skills',value='Unsent draft information')],revisions=[])
    item=Record(fields=[Record(key='skills')],targets=[Record(student=student)],submissions=[draft])
    keys,rows=report_rows(item)
    assert rows[0]['name']=='Draft student' and rows[0]['skills']==''
    assert filtered_stats(rows)=={'total':1,'submitted':0,'pending':1,'verified':0}


def test_extension_rejection_and_deadline_validation(client):
    cls,teacher,req,student=setup_hierarchy(client);item=create_request(client,cls,req,[{'key':'skills','label':'Skills','type':'text'}])
    old=item.deadline
    for due in [now()-timedelta(days=1),old-timedelta(hours=1),req.deadline+timedelta(days=1)]:
        assert client.post(f'/requests/{item.id}/extension',data={'proposed_deadline':due.isoformat(),'reason':'Invalid'}).status_code==400
    post(client,f'/requests/{item.id}/extension',{'proposed_deadline':(old+timedelta(days=1)).isoformat(),'reason':'Need time.'})
    change=DeadlineExtensionRequest.query.one();as_hod(client)
    post(client,f'/deadline-extensions/{change.id}',{'action':'REJECTED','note':'Final deadline must stand.'})
    assert item.deadline==old and change.status=='REJECTED'
    assert Notification.query.filter_by(user_id=teacher.id,kind='DEADLINE_EXTENSION_REJECTED').count()==1
    assert Notification.query.filter_by(kind='DEADLINE_EXTENDED').count()==0

def test_hod_directory_grouping_order_filters_and_academic_context(client):
    cls,teacher,req,student=setup_hierarchy(client)
    second=AcademicClass(name='S2 MCA',department_id=cls.department_id,teachers=[teacher]);db.session.add(second);db.session.commit()
    post(client,'/students/new',{'name':'Zara','username':'zara','email':'zara@example.com','password':PASSWORD,'register_number':'MCA100','class_id':second.id})
    as_hod(client)
    page=client.get('/students').data.decode()
    # Explicit department/class order puts S2 before S4 despite insertion/name order.
    assert page.index('MCA100')<page.index('MCA001')
    assert 'Browse by class' in page and '1 students' in page
    filtered=client.get(f'/students?class_id={cls.id}&department_id={cls.department_id}&teacher_id={teacher.id}').data
    assert b'MCA001' in filtered and b'MCA100' not in filtered
    profile=client.get(f'/students/{student.id}').data
    assert b'Academic &amp; Institution' in profile or b'Academic & Institution' in profile
    assert b'Mr. Arun' in profile and b'hod@example.com' in profile
    assert b'Submitted Data' in profile and b'Profile version history' in profile

def test_new_routes_and_review_ownership(client):
    cls,teacher,req,student=setup_hierarchy(client)
    item=create_request(client,cls,req,[{'key':'skills','label':'Skills','type':'text'}]);as_student(client)
    post(client,f'/requests/{item.id}/submit',{'skills':'Python'});sub=Submission.query.one()
    post(client,'/student/profile/change',{'field':'name','requested_value':'Rahul Nair','reason':'Official name'})
    pc=ProfileChangeRequest.query.one()
    post(client,f'/student/submissions/{sub.id}/change',{'fields':'skills','reason':'Add tools'})
    sc=SubmissionChangeRequest.query.one()
    assert client.post(f'/profile-changes/{pc.id}',data={'action':'APPROVED'}).status_code==403
    assert client.post(f'/submissions/{sub.id}/profile-review',data={'action':'skip'}).status_code==403
    as_teacher(client)
    other_role=Role.query.filter_by(name='TEACHER').one()
    other=User(username='outsider',email='outsider@example.com',name='Outside teacher',role_record=other_role,first_login=False);other.set_password(PASSWORD);db.session.add(other);db.session.commit()
    logout(client);login(client,'teacher','outsider')
    for path in [f'/profile-changes/{pc.id}',f'/submission-changes/{sc.id}',f'/submissions/{sub.id}/profile-review',f'/requests/{item.id}/extension',f'/reports/{item.id}?format=pdf']:
        assert client.get(path).status_code==404,path
