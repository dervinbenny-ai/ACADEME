import io
import json
from datetime import timedelta
from openpyxl import load_workbook
from extensions import db
from models import *
from services.common import profile_data

PASSWORD='Temporary@12345'

def login(client,portal,username,password=PASSWORD,change=False):
    response=client.post(f'/{portal}/login',data={'username':username,'password':password},follow_redirects=True)
    assert response.status_code==200,response.data.decode()[:600]
    if change:
        response=client.post('/password',data={'current_password':password,'password':'ChangedPass@12345','confirm_password':'ChangedPass@12345'},follow_redirects=True)
        assert response.status_code==200
    return response

def logout(client): return client.post('/logout')

def post(client,path,data):
    response=client.post(path,data=data,follow_redirects=True)
    assert response.status_code==200,(path,response.status_code,response.data.decode()[:1200])
    return response

def setup_hierarchy(client):
    login(client,'admin','superadmin','SuperAdmin@123',True)
    post(client,'/users/new',{'name':'HOD','username':'hod','email':'hod@example.com','phone':'+14155550123','password':PASSWORD})
    admin=User.query.filter_by(username='hod').one()
    assert AdminAccount.query.filter_by(user_id=admin.id).one()
    logout(client);login(client,'admin','hod',change=True)
    post(client,'/departments',{'name':'MCA','description':'Computer Applications'})
    post(client,'/users/new',{'name':'Mr. Arun','username':'arun','email':'arun@example.com','phone':'+14155550124','password':PASSWORD})
    teacher=User.query.filter_by(username='arun').one()
    assert TeacherAccount.query.filter_by(user_id=teacher.id).one()
    dept=Department.query.one()
    post(client,'/classes',{'name':'S4 MCA','department_id':dept.id,'semester':'4','batch':'2025–2027','teachers':str(teacher.id)})
    cls=AcademicClass.query.one()
    post(client,'/requirements/new',{'title':'Placement details','requested_information':'CGPA, backlogs, skills, resume and placement status','class_id':cls.id,'teacher_id':teacher.id,'deadline':(now()+timedelta(days=14)).isoformat(timespec='minutes')})
    requirement=AdminRequirement.query.one()
    logout(client);login(client,'teacher','arun',change=True)
    post(client,'/students/new',{'name':'Rahul','username':'rahul','email':'rahul@example.com','password':PASSWORD,'register_number':'MCA001','class_id':cls.id,'phone':'+919876543210'})
    assert Student.query.one().user.username=='rahul'
    return cls,teacher,requirement,Student.query.one()

def create_request(client,cls,requirement,fields=None):
    if fields is None: fields=[{'key':'name','label':'Name','type':'text','required':True},{'key':'email','label':'Email','type':'email','required':True},{'key':'cgpa','label':'CGPA','type':'decimal','required':True},{'key':'resume','label':'Resume','type':'file','required':True}]
    post(client,'/requests/new',{'title':'Placement collection','requirement_id':requirement.id,'class_id':cls.id,'deadline':(now()+timedelta(days=7)).isoformat(timespec='minutes'),'fields_json':json.dumps(fields),'allow_edit':'on'})
    item=DataRequest.query.order_by(DataRequest.id.desc()).first()
    post(client,f'/requests/{item.id}',{'action':'publish'})
    return item

def pdf():
    from pypdf import PdfWriter
    writer=PdfWriter();writer.add_blank_page(width=200,height=200)
    buffer=io.BytesIO();writer.write(buffer);buffer.seek(0)
    return buffer

def test_complete_acceptance_flow(client):
    cls,teacher,requirement,student=setup_hierarchy(client)
    assert Notification.query.filter_by(user_id=teacher.id,title='New requirement from HOD').count()==1
    suggestions=client.post('/api/suggest',json={'prompt':'Placement details'}).get_json()
    assert {'cgpa','backlogs','skills','resume','placement_status'} <= {f['key'] for f in suggestions['fields']}
    item=create_request(client,cls,requirement)
    logout(client);login(client,'student','rahul',change=True)
    page=client.get(f'/requests/{item.id}/submit')
    assert b'Already available' in page.data and b'Rahul' in page.data
    post(client,f'/requests/{item.id}/submit',{'action':'submit','cgpa':'8.6','resume':(pdf(),'resume.pdf')})
    assert not profile_data(student).get('cgpa')
    sub=Submission.query.one()
    logout(client);login(client,'teacher','arun','ChangedPass@12345')
    post(client,f'/submissions/{sub.id}',{'action':'CORRECTION_REQUIRED','feedback':'Please confirm your latest CGPA.'})
    logout(client);login(client,'student','rahul','ChangedPass@12345')
    post(client,f'/requests/{item.id}/submit',{'action':'submit','cgpa':'8.7'})
    logout(client);login(client,'teacher','arun','ChangedPass@12345')
    post(client,f'/submissions/{sub.id}',{'action':'VERIFIED'})
    assert not profile_data(student).get('cgpa')
    post(client,f'/submissions/{sub.id}/profile-review',{'action':'apply','selected':['cgpa','resume'],'baseline_cgpa':'','baseline_resume':''})
    db.session.expire_all()
    assert profile_data(student)['cgpa']=='8.7'
    assert Student.query.count()==1
    assert ProfileVersion.query.filter_by(student_id=student.id,key='cgpa').count()==1
    post(client,f'/requirements/{requirement.id}',{'action':'ready'})
    assert requirement.status=='READY_FOR_REVIEW'
    logout(client);login(client,'admin','hod','ChangedPass@12345')
    response=client.get(f'/reports/{item.id}?format=xlsx')
    assert response.status_code==200
    workbook=load_workbook(io.BytesIO(response.data))
    assert workbook['Collected data']['A8'].value=='Rahul'
    assert workbook['Summary']['B4'].value==1
    post(client,f'/requirements/{requirement.id}',{'action':'complete'})
    assert requirement.status=='COMPLETED'
    assert Notification.query.filter_by(user_id=requirement.admin_id,title='Requirement completed · report ready').count()==1

def test_role_and_class_boundaries(client):
    cls,teacher,req,student=setup_hierarchy(client)
    other=AcademicClass(name='Other class',department_id=cls.department_id);db.session.add(other);db.session.commit()
    response=client.post('/students/new',data={'name':'Intruder','username':'intruder','email':'intruder@example.com','password':PASSWORD,'register_number':'OTHER','class_id':other.id})
    assert response.status_code==403
    assert User.query.filter_by(username='intruder').count()==0
    assert client.get('/departments').status_code==403
    assert client.post('/requirements/new',data={}).status_code==403
    logout(client);login(client,'student','rahul',change=True)
    assert client.get('/students/new').status_code==403
    assert client.get('/users').status_code==403
    assert client.post('/api/suggest',json={'prompt':'placement'}).status_code==403
    assert client.get('/reports').status_code==403

def test_portal_account_controls(client):
    cls,teacher,req,student=setup_hierarchy(client)
    logout(client)
    response=login(client,'teacher','rahul')
    assert b'not authorized for the Teacher Portal' in response.data
    response=login(client,'admin','arun','ChangedPass@12345')
    assert b'not authorized for the Admin Portal' in response.data
    response=login(client,'student','rahul','wrong')
    assert b'Invalid username or password' in response.data
    student.user.active=False;db.session.commit()
    assert b'deactivated' in login(client,'student','rahul').data

def test_conflicts_require_explicit_decision(client):
    cls,teacher,req,student=setup_hierarchy(client)
    item=create_request(client,cls,req,[{'key':'phone','label':'Phone','type':'phone','reuse':'update','required':True}])
    logout(client);login(client,'student','rahul',change=True)
    post(client,f'/requests/{item.id}/submit',{'phone':'+919123456780','action':'submit'})
    sub=Submission.query.one()
    logout(client);login(client,'teacher','arun','ChangedPass@12345')
    post(client,f'/submissions/{sub.id}',{'action':'VERIFIED'})
    assert client.post(f'/submissions/{sub.id}/profile-review',data={'action':'apply','selected':'phone','baseline_phone':'+919876543210'}).status_code==400
    db.session.rollback()
    assert profile_data(student)['phone']=='+919876543210'
    post(client,f'/submissions/{sub.id}/profile-review',{'action':'apply','selected':'phone','baseline_phone':'+919876543210','decision_phone':'accept'})
    db.session.expire_all()
    assert profile_data(student)['phone']=='+919123456780'

def test_expired_and_unverified_completion_blocked(client):
    cls,teacher,req,student=setup_hierarchy(client)
    item=create_request(client,cls,req,[{'key':'cgpa','label':'CGPA','type':'decimal','required':True}])
    assert client.post(f'/requirements/{req.id}',data={'action':'ready'}).status_code==400
    item.deadline=now()-timedelta(days=1);db.session.commit()
    logout(client);login(client,'student','rahul',change=True)
    assert client.post(f'/requests/{item.id}/submit',data={'cgpa':'8.6','action':'submit'}).status_code==403

def test_documents_assistant_messages_activities(client):
    cls,teacher,req,student=setup_hierarchy(client)
    logout(client);login(client,'student','rahul',change=True)
    response=post(client,'/assistant',{'prompt':'Who is my class teacher?'})
    assert b'Mr. Arun' in response.data
    post(client,'/messages',{'recipient_id':teacher.id,'subject':'Help with profile','body':'Please check my CGPA.'})
    thread=MessageThread.query.one()
    assert client.post('/documents',data={'document':(io.BytesIO(b'evil'),'resume.exe')}).status_code==400
    post(client,'/documents',{'document':(pdf(),'certificate.pdf')})
    assert client.get(f'/documents/{Document.query.one().id}').status_code==200
    assert client.get(f'/students/{student.id}/qr').mimetype=='image/png'
    logout(client);login(client,'teacher','arun','ChangedPass@12345')
    post(client,f'/messages/{thread.id}',{'body':'I will review it.'})
    logout(client);login(client,'admin','hod','ChangedPass@12345')
    post(client,'/activities',{'title':'Career workshop','department_id':cls.department_id,'category':'Workshop','event_date':(now()+timedelta(days=2)).isoformat(timespec='minutes'),'description':'Prepare for interviews.'})
    activity=AcademicActivity.query.one()
    logout(client);login(client,'student','rahul','ChangedPass@12345')
    post(client,'/activities',{'id':activity.id})
    assert ActivityRegistration.query.count()==1

def test_empty_pages_and_seed_is_idempotent(client):
    from services.seed import seed
    seed();seed()
    assert User.query.count()==1 and Role.query.count()==4 and Student.query.count()==0 and AcademicClass.query.count()==0
    login(client,'admin','superadmin','SuperAdmin@123',True)
    for path in ['/dashboard','/users','/users/new','/settings','/audit','/notifications','/password']:
        response=client.get(path)
        assert response.status_code==200,(path,response.data[:600])

def test_csrf_protection(app,client):
    app.config['WTF_CSRF_ENABLED']=True
    assert client.post('/admin/login',data={'username':'superadmin','password':'SuperAdmin@123'}).status_code==400
