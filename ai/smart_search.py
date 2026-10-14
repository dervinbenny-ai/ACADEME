import re
from models import Student,ProfileValue,DataRequest,Submission,RequestTarget

def apply_search(query,text,classes):
    lowered=text.casefold()
    recognized=False
    for cls in classes:
        if cls.name.casefold() in lowered:
            query=query.filter(Student.class_id==cls.id);recognized=True
    missing=re.search(r'(?:without|missing)\s+(blood group|phone|resume|cgpa|emergency contact)',lowered)
    if missing:
        key=missing.group(1).replace(' ','_')
        query=query.filter(~Student.profile.any((ProfileValue.key==key)&(ProfileValue.value!='')));recognized=True
    if 'incomplete' in lowered:
        from sqlalchemy import or_
        keys=['blood_group','phone','resume','cgpa','emergency_contact']
        query=query.filter(or_(*[~Student.profile.any((ProfileValue.key==key)&(ProfileValue.value!='')) for key in keys]));recognized=True
    if "haven't submitted" in lowered or 'not submitted' in lowered:
        keyword='internship' if 'internship' in lowered else 'placement' if 'placement' in lowered else ''
        requests=DataRequest.query.filter(DataRequest.class_id.in_([c.id for c in classes]),DataRequest.status=='PUBLISHED')
        if keyword: requests=requests.filter(DataRequest.title.ilike('%'+keyword+'%'))
        request_ids=[r.id for r in requests.all()]
        pending=db_pending_ids(request_ids)
        query=query.filter(Student.id.in_(pending));recognized=True
    return query,recognized

def db_pending_ids(request_ids):
    submitted={(s.request_id,s.student_id) for s in Submission.query.filter(Submission.request_id.in_(request_ids),Submission.status.notin_(['DRAFT','CORRECTION_REQUIRED','REJECTED'])).all()}
    return {t.student_id for t in RequestTarget.query.filter(RequestTarget.request_id.in_(request_ids)).all() if (t.request_id,t.student_id) not in submitted}
