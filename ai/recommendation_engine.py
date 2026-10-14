from models import FieldLibrary

MAP={
 'placement':['cgpa','backlogs','skills','resume','certifications','linkedin','phone','email','placement_status'],
 'internship':['internship_company','internship_role','start_date','end_date','duration','stipend','skills_learned','certificate'],
 'medical':['blood_group','emergency_contact','phone'],
 'blood':['blood_group','emergency_contact'],
 'scholarship':['scholarship','cgpa','certificate'],
 'sport':['sports','certificate'],
 'contact':['phone','email','address','emergency_contact'],
 'academic':['cgpa','backlogs','semester'],
}

def suggest(prompt):
    keys=[]
    for keyword,fields in MAP.items():
        if keyword in prompt.lower(): keys.extend(fields)
    for field in FieldLibrary.query.all():
        if field.label.lower() in prompt.lower(): keys.append(field.key)
    keys=list(dict.fromkeys(keys))
    fields={f.key:f for f in FieldLibrary.query.filter(FieldLibrary.key.in_(keys)).all()}
    return [{'key':k,'label':fields[k].label,'type':fields[k].type,'options':fields[k].options,'required':True,'reuse':'auto','validation':{},'help_text':''} for k in keys if k in fields]
