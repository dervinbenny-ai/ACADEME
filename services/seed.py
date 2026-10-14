import os
from extensions import db
from models import AdminAccount, Role, User, FieldLibrary, SystemSetting

FIELDS = {
 'PERSONAL': [('name','Full name','text'),('dob','Date of birth','date'),('gender','Gender','text'),('blood_group','Blood group','select')],
 'CONTACT': [('email','Email','email'),('phone','Phone','phone'),('address','Address','textarea'),('emergency_contact','Emergency contact','phone')],
 'ACADEMIC': [('register_number','Register number','text'),('roll_number','Roll number','text'),('department','Department','text'),('class','Class','text'),('semester','Semester','text'),('batch','Batch','text'),('admission_year','Admission year','number'),('cgpa','CGPA','decimal'),('backlogs','Backlogs','number')],
 'PLACEMENT': [('skills','Skills','textarea'),('resume','Resume','file'),('linkedin','LinkedIn','url'),('portfolio','Portfolio','url'),('certifications','Certifications','textarea'),('placement_status','Placement status','select')],
 'INTERNSHIP': [('internship_company','Internship company','text'),('internship_role','Internship role','text'),('start_date','Start date','date'),('end_date','End date','date'),('duration','Duration','text'),('stipend','Stipend','decimal'),('skills_learned','Skills learned','textarea'),('certificate','Certificate','file')],
 'OTHER': [('scholarship','Scholarship','text'),('nss','NSS','checkbox'),('ncc','NCC','checkbox'),('sports','Sports','textarea'),('research','Research','textarea'),('hostel','Hostel','text'),('transport','Transport','text')]
}

def seed(superadmin_password=None, superadmin_username=None, superadmin_email=None, superadmin_name='System Administrator'):
    for name in ('SUPER_ADMIN','ADMIN','TEACHER','STUDENT'):
        if not Role.query.filter_by(name=name).first(): db.session.add(Role(name=name))
    db.session.flush()
    for category, items in FIELDS.items():
        for key, label, kind in items:
            if not FieldLibrary.query.filter_by(key=key).first():
                options = ['A+','A-','B+','B-','AB+','AB-','O+','O-'] if key == 'blood_group' else ['Not seeking','Seeking','Placed'] if key == 'placement_status' else []
                db.session.add(FieldLibrary(key=key,label=label,type=kind,category=category,options=options))
    for key, value in {'independent_requests':'true','allow_student_reset':'true'}.items():
        if not db.session.get(SystemSetting,key): db.session.add(SystemSetting(key=key,value=value))
    role = Role.query.filter_by(name='SUPER_ADMIN').one()
    if not User.query.filter_by(role_id=role.id).first():
        password = superadmin_password or os.getenv('SUPERADMIN_PASSWORD')
        if not password: raise RuntimeError('Set SUPERADMIN_PASSWORD in .env before setup.')
        user = User(username=(superadmin_username or os.getenv('SUPERADMIN_USERNAME','superadmin')).lower(), email=(superadmin_email or os.getenv('SUPERADMIN_EMAIL','superadmin@example.com')).lower(), name=superadmin_name,role_record=role,first_login=True)
        user.set_password(password)
        db.session.add(user)
        db.session.flush()
        db.session.add(AdminAccount(user_id=user.id))
    else:
        user = User.query.join(Role).filter(Role.name == 'SUPER_ADMIN').first()
        if user and not user.admin_account:
            db.session.add(AdminAccount(user_id=user.id))
    db.session.commit()
