import json
from datetime import timedelta
from extensions import db
from models import *
from services.common import profile_data
from test_workflow import setup_hierarchy,create_request,login,logout,post,PASSWORD

def test_draft_edit_validation_reminders_and_smart_search(client):
    from services.deadline_service import send_reminders
    cls,teacher,req,student=setup_hierarchy(client)
    fields=[{'key':'blood_group','label':'Blood group','type':'select','options':['A+','B+'],'required':True,'reuse':'confirm'}]
    payload={'title':'Health collection','requirement_id':req.id,'class_id':cls.id,'deadline':(now()+timedelta(days=3)).isoformat(timespec='minutes'),'fields_json':json.dumps(fields)}
    post(client,'/requests/new',payload)
    item=DataRequest.query.one()
    assert client.get(f'/requests/{item.id}/edit').status_code==200
    payload['title']='Updated health collection'
    post(client,f'/requests/{item.id}/edit',payload)
    assert DataRequest.query.count()==1 and FormField.query.count()==1
    assert item.title=='Updated health collection'
    post(client,f'/requests/{item.id}',{'action':'publish'})
    assert send_reminders()>=1
    assert send_reminders()==0
    assert b'Rahul' in client.get('/students?q=Show+S4+MCA+students+without+blood+group').data
    logout(client);login(client,'student','rahul',change=True)
    assert client.post(f'/requests/{item.id}/submit',data={'blood_group':'INVALID','action':'submit'}).status_code==400
    assert Submission.query.count()==0
    post(client,f'/requests/{item.id}/submit',{'blood_group':'B+','action':'submit'})
    assert not profile_data(student).get('blood_group')
    assert b'Submitted' in client.get('/requests?status=SUBMITTED').data
    assert b'Updated health collection' not in client.get('/requests?status=PENDING').data

def test_other_teacher_student_document_and_target_access(client):
    cls,teacher,req,student=setup_hierarchy(client)
    item=create_request(client,cls,req,[{'key':'cgpa','label':'CGPA','type':'decimal'}])
    logout(client);login(client,'admin','hod','ChangedPass@12345')
    post(client,'/users/new',{'name':'Other teacher','username':'other','email':'other@example.com','password':PASSWORD})
    other=User.query.filter_by(username='other').one()
    post(client,'/classes',{'name':'S2 MCA','department_id':cls.department_id,'teachers':str(other.id)})
    other_class=AcademicClass.query.filter_by(name='S2 MCA').one()
    logout(client);login(client,'teacher','other',change=True)
    assert client.get(f'/students/{student.id}').status_code==404
    assert client.get(f'/users/{student.user_id}/edit').status_code==403
    assert client.get(f'/requests/{item.id}').status_code==404
    assert client.get(f'/requirements/{req.id}').status_code==404
    post(client,'/students/new',{'name':'Other student','username':'second','email':'second@example.com','password':PASSWORD,'register_number':'MCA002','class_id':other_class.id})
    second=Student.query.filter_by(register_number='MCA002').one()
    logout(client);login(client,'student','second',change=True)
    assert client.get(f'/students/{student.id}').status_code==404
    assert client.get(f'/requests/{item.id}/submit').status_code==404
    assert client.get(f'/q/{student.qr_token}').status_code==404

def test_account_phone_and_date_validation(client):
    cls,teacher,req,student=setup_hierarchy(client)
    assert teacher.phone=='+14155550124'
    assert User.query.filter_by(username='hod').one().phone=='+14155550123'
    logout(client);login(client,'student','rahul',change=True)
    profile_response=client.get(f'/students/{student.id}')
    assert b'href="tel:+14155550124"' in profile_response.data
    assert b'href="tel:+14155550123"' in profile_response.data
    logout(client);login(client,'admin','superadmin','ChangedPass@12345')
    assert b'name="phone"' in client.get('/users/new').data
    logout(client);login(client,'teacher','arun','ChangedPass@12345')
    assert b'name="phone"' in client.get('/users/4/edit').data
    logout(client);login(client,'admin','superadmin','ChangedPass@12345')
    invalid_teacher={'name':'Invalid email','username':'bademail','email':'invalid-email','password':PASSWORD}
    assert client.post('/users/new',data=invalid_teacher).status_code==400
    assert not User.query.filter_by(username='bademail').first()
    logout(client);login(client,'admin','hod','ChangedPass@12345')
    invalid_teacher['username']='badteacher'
    invalid_teacher['email']='still-invalid'
    assert client.post('/users/new',data=invalid_teacher).status_code==400
    assert not User.query.filter_by(username='badteacher').first()
    logout(client);login(client,'teacher','arun','ChangedPass@12345')
    invalid_student={'name':'Invalid phone','username':'badphone','email':'badphone@example.com','password':PASSWORD,'register_number':'BAD001','class_id':cls.id,'phone':'9876543210'}
    assert client.post('/students/new',data=invalid_student).status_code==400
    assert not User.query.filter_by(username='badphone').first()
    item=create_request(client,cls,req,[{'key':'dob','label':'Date of birth','type':'date'}])
    logout(client);login(client,'student','rahul','ChangedPass@12345')
    assert client.post(f'/requests/{item.id}/submit',data={'dob':'2026-02-30','action':'submit'}).status_code==400
    assert client.post(f'/requests/{item.id}/submit',data={'dob':'20260228','action':'submit'}).status_code==400

def test_all_role_pages_render(client):
    cls,teacher,req,student=setup_hierarchy(client)
    item=create_request(client,cls,req,[{'key':'skills','label':'Skills','type':'textarea'}])
    for path in ['/dashboard','/classes','/students','/students/new','/requirements','/requests','/requests/new','/reports','/messages','/activities','/notifications',f'/students/{student.id}',f'/users/{student.user_id}/edit',f'/reports/{item.id}']:
        assert client.get(path).status_code==200,path
    logout(client);login(client,'admin','hod','ChangedPass@12345')
    for path in ['/dashboard','/classes','/departments','/requirements/new','/students','/reports','/audit','/users','/notifications']:
        assert client.get(path).status_code==200,path
    assert b'Add student' not in client.get('/students').data
    logout(client);login(client,'student','rahul',change=True)
    for path in ['/dashboard','/profile','/timeline','/requests','/documents','/assistant','/activities','/messages','/notifications']:
        assert client.get(path,follow_redirects=True).status_code==200,path

def test_export_formula_safety():
    from services.report_service import safe_cell
    assert safe_cell('=HYPERLINK("evil")').startswith("'")
    assert safe_cell('   +SUM(1,2)').startswith("'")
    assert safe_cell('ordinary')=='ordinary'

def test_requirement_edit_and_draft_isolation(client):
    cls,teacher,req,student=setup_hierarchy(client)
    logout(client);login(client,'admin','hod','ChangedPass@12345')
    response=client.get(f'/requirements/{req.id}/edit')
    assert response.status_code==200 and b'Placement details' in response.data
    post(client,f'/requirements/{req.id}/edit',{'title':'Updated requirement','requested_information':'New placement information','class_id':cls.id,'teacher_id':teacher.id,'deadline':(now()+timedelta(days=14)).isoformat(timespec='minutes')})
    assert req.title=='Updated requirement'
    post(client,'/requirements/new',{'title':'Private draft','requested_information':'Not ready to share','class_id':cls.id,'teacher_id':teacher.id,'deadline':(now()+timedelta(days=14)).isoformat(timespec='minutes'),'action':'draft'})
    draft=AdminRequirement.query.filter_by(title='Private draft').one()
    logout(client);login(client,'teacher','arun','ChangedPass@12345')
    assert client.get(f'/requirements/{draft.id}').status_code==404
    assert b'Private draft' not in client.get('/requirements').data
