import io
from datetime import timedelta
from openpyxl import load_workbook
from pypdf import PdfReader
from extensions import db
from models import *
from services.common import profile_data
from test_workflow import setup_hierarchy, create_request, login, logout, post, PASSWORD

def test_complete_rahul_arun_acceptance_scenario(client):
    cls,teacher,requirement,rahul=setup_hierarchy(client)
    post(client,'/students/new',{'name':'Pending classmate','username':'classmate','email':'classmate@example.com','password':PASSWORD,'register_number':'MCA002','class_id':cls.id})
    classmate=Student.query.filter_by(register_number='MCA002').one()
    fields=[{'key':'cgpa','label':'CGPA','type':'decimal'}, {'key':'skills','label':'Skills','type':'textarea'},
            {'key':'placement_status','label':'Placement status','type':'text'}, {'key':'temporary_accommodation','label':'Temporary Accommodation','type':'text'}]
    item=create_request(client,cls,requirement,fields)
    logout(client);login(client,'student','rahul',change=True)
    post(client,f'/requests/{item.id}/submit',{'action':'submit','cgpa':'8.3','skills':'Python','placement_status':'Not Placed','temporary_accommodation':'Hostel Room 12'})
    sub=Submission.query.one()
    page=client.get(f'/requests/{item.id}/submit').data
    assert b'Submit for verification' not in page and b'Submission Completed' in page
    assert client.post(f'/requests/{item.id}/submit',data={'action':'submit','skills':'Injected'}).status_code==403
    assert b'Hostel Room 12' in client.get(f'/student/submissions/{sub.id}').data
    logout(client);login(client,'teacher','arun','ChangedPass@12345')
    page=post(client,f'/submissions/{sub.id}',{'action':'VERIFIED'}).data
    assert b'Update Master Student Profile?' in page
    post(client,f'/submissions/{sub.id}/profile-review',{'action':'apply','selected':['cgpa','skills','placement_status'],'baseline_cgpa':'','baseline_skills':'','baseline_placement_status':''})
    assert profile_data(rahul)['skills']=='Python' and profile_data(rahul)['cgpa']=='8.3'
    assert 'temporary_accommodation' not in profile_data(rahul)
    logout(client);login(client,'student','rahul','ChangedPass@12345')
    post(client,f'/student/submissions/{sub.id}/change',{'fields':'skills','reason':'Add Flask.'})
    change=SubmissionChangeRequest.query.one()
    logout(client);login(client,'teacher','arun','ChangedPass@12345')
    post(client,f'/submission-changes/{change.id}',{'action':'APPROVED'})
    logout(client);login(client,'student','rahul','ChangedPass@12345')
    post(client,f'/requests/{item.id}/submit',{'action':'revise','skills':'Python, Flask'})
    assert client.post(f'/requests/{item.id}/submit',data={'action':'revise','skills':'Repeated'}).status_code==403
    assert sub.revisions[0].values['skills']=='Python' and sub.revisions[1].values['skills']=='Python, Flask'
    logout(client);login(client,'teacher','arun','ChangedPass@12345')
    post(client,f'/submissions/{sub.id}',{'action':'VERIFIED'})
    post(client,f'/submissions/{sub.id}/profile-review',{'action':'apply','selected':'skills','baseline_skills':'Python','decision_skills':'accept'})
    item.deadline=now()-timedelta(hours=1);db.session.commit()
    post(client,f'/requests/{item.id}/extension',{'proposed_deadline':(now()+timedelta(days=2)).isoformat(),'reason':'Placement training.'})
    extension=DeadlineExtensionRequest.query.one()
    logout(client);login(client,'admin','hod','ChangedPass@12345')
    post(client,f'/deadline-extensions/{extension.id}',{'action':'APPROVED','note':'Approved for pending students.'})
    assert Notification.query.filter_by(user_id=classmate.user_id,kind='DEADLINE_EXTENDED').count()==1
    assert Notification.query.filter_by(user_id=rahul.user_id,kind='DEADLINE_EXTENDED').count()==0
    assert b'Browse by class' in client.get('/students').data
    for portal,username in [('admin','hod'),('teacher','arun')]:
        logout(client);login(client,portal,username,'ChangedPass@12345')
        xlsx=client.get(f'/reports/{item.id}?format=xlsx&status=VERIFIED');assert xlsx.status_code==200
        assert load_workbook(io.BytesIO(xlsx.data))['Collected data']['A8'].value=='Rahul'
        pdf=client.get(f'/reports/{item.id}?format=pdf&status=VERIFIED');assert pdf.status_code==200
        assert 'Python, Flask' in ''.join(page.extract_text() for page in PdfReader(io.BytesIO(pdf.data)).pages)
    logout(client);login(client,'student','rahul','ChangedPass@12345')
    profile=client.get('/profile',follow_redirects=True).data
    for label in [b'Class teacher',b'Head of Department',b'Submitted Data',b'Master Profile',b'Documents',b'Change Requests',b'Profile History']:
        assert label in profile,label

def test_profile_merge_stale_conflict_and_clarification(client):
    cls,teacher,req,student=setup_hierarchy(client)
    item=create_request(client,cls,req,[{'key':'phone','label':'Phone','type':'phone','reuse':'update'}])
    logout(client);login(client,'student','rahul',change=True)
    post(client,f'/requests/{item.id}/submit',{'phone':'+919123456780'})
    sub=Submission.query.one()
    logout(client);login(client,'teacher','arun','ChangedPass@12345')
    post(client,f'/submissions/{sub.id}',{'action':'VERIFIED'})
    assert client.post(f'/submissions/{sub.id}/profile-review',data={'action':'apply','selected':'phone','baseline_phone':'stale','decision_phone':'accept'}).status_code==409
    db.session.rollback()
    post(client,f'/submissions/{sub.id}/profile-review',{'action':'apply','decision_phone':'clarify'})
    assert sub.status=='CORRECTION_REQUIRED' and sub.revision_allowed and sub.revision_fields==['phone']
    assert profile_data(student)['phone']=='+919876543210'

def test_profile_change_stale_and_other_student_access(client):
    cls,teacher,req,student=setup_hierarchy(client)
    item=create_request(client,cls,req,[{'key':'skills','label':'Skills','type':'text'}])
    logout(client);login(client,'student','rahul',change=True)
    post(client,f'/requests/{item.id}/submit',{'skills':'Python'});sub=Submission.query.one()
    post(client,'/student/profile/change',{'field':'name','requested_value':'Rahul Nair','reason':'Update full name'})
    change=ProfileChangeRequest.query.one()
    student.user.name='Officially changed meanwhile';db.session.commit()
    logout(client);login(client,'teacher','arun','ChangedPass@12345')
    assert client.post(f'/profile-changes/{change.id}',data={'action':'APPROVED'}).status_code==409
    db.session.rollback()
    other=User(username='otherstudent',email='otherstudent@example.com',name='Other',role_record=Role.query.filter_by(name='STUDENT').one(),first_login=False)
    other.set_password(PASSWORD);db.session.add(other);db.session.flush()
    db.session.add(Student(user=other,academic_class=cls,register_number='MCA999',created_by=teacher.id));db.session.commit()
    logout(client);login(client,'student','otherstudent')
    for path in [f'/student/submissions/{sub.id}',f'/student/submissions/{sub.id}/change',f'/students/{student.id}']:
        assert client.get(path).status_code==404
    assert client.post(f'/student/submissions/{sub.id}/change',data={'fields':'skills','reason':'Tamper'}).status_code==404

def test_teacher_and_institution_identity_edits_create_versions(client):
    cls,teacher,req,student=setup_hierarchy(client)
    post(client,f'/users/{student.user_id}/edit',{'name':'Rahul Official','email':'rahul.updated@example.com','username':'rahul','register_number':'MCA001A','phone':'+919876543210','roll_number':'12','admission_year':'2025'})
    assert {'name','email','register_number','roll_number','admission_year'}<={v.key for v in ProfileVersion.query.filter_by(change_source='TEACHER_UPDATE')}
    logout(client);login(client,'admin','hod','ChangedPass@12345')
    post(client,'/classes',{'id':cls.id,'name':'S5 MCA','department_id':cls.department_id,'semester':'5','batch':'2025-2027','teachers':teacher.id})
    assert ProfileVersion.query.filter_by(student_id=student.id,key='semester',old_value='4',new_value='5',change_source='SYSTEM_UPDATE').count()==1
