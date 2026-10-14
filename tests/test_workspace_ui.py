from extensions import db
from models import User, Role, AcademicClass, Student, Notification
from test_workflow import setup_hierarchy, create_request, login, logout

def test_workspace_search_and_notification_isolation(client):
    cls, teacher, requirement, student = setup_hierarchy(client)
    item = create_request(client, cls, requirement, [{'key':'skills','label':'Skills','type':'textarea'}])
    outsider = User(name='Outside Learner',username='outsider',email='outsider@example.com',role_record=Role.query.filter_by(name='STUDENT').one(),first_login=False)
    outsider.set_password('PreviewOnly@12345');db.session.add(outsider)
    other_class=AcademicClass(name='Unassigned',department_id=cls.department_id);db.session.add(other_class);db.session.flush()
    db.session.add(Student(user_id=outsider.id,register_number='OUT001',class_id=other_class.id,created_by=teacher.id))
    foreign_notice=Notification(user_id=outsider.id,title='Private notification',body='Private');db.session.add(foreign_notice);db.session.commit()
    assert client.get('/api/workspace/search?q=Rahul').get_json()['items'][0]['url']==f'/students/{student.id}'
    assert not client.get('/api/workspace/search?q=Outside').get_json()['items']
    assert any(row['url']==f'/requests/{item.id}' for row in client.get('/api/workspace/search?q=Placement').get_json()['items'])
    feed=client.get('/api/workspace/notifications').get_json()
    assert all(row['title']!='Private notification' for row in feed['items'])
    assert client.post('/api/workspace/notifications/read',json={'id':foreign_notice.id}).status_code==404
    assert not db.session.get(Notification,foreign_notice.id).read
    assert client.post('/api/workspace/notifications/read',json={'id':'invalid'}).status_code==400
    assert client.post('/api/workspace/notifications/read',json={}).get_json()['unread']==0
    logout(client);login(client,'student','rahul',change=True)
    assert not any(row['kind'].startswith('Student') for row in client.get('/api/workspace/search?q=Rahul').get_json()['items'])
    assert all(row['url']=='/profile' for row in client.get('/api/workspace/search?q=phone').get_json()['items'])

def test_workspace_endpoints_require_authentication(client):
    for path in ['/api/workspace/search?q=test','/api/workspace/notifications']:
        assert client.get(path).status_code==302
