from models import Submission
from services.common import completion
from services.access import my_student, requests_query

def answer(prompt):
    student=my_student()
    items=requests_query().all()
    subs={s.request_id:s for s in Submission.query.filter_by(student_id=student.id).all()}
    pending=[r for r in items if r.id not in subs or not subs[r.id].submitted_at or subs[r.id].revision_allowed]
    text=prompt.lower()
    if any(word in text for word in ('missing','completion','profile')):
        percent,missing=completion(student)
        return f'Your profile is {percent}% complete. Missing: '+(', '.join(k.replace('_',' ') for k in missing) or 'None')+'.'
    if 'teacher' in text: return 'Your class teachers: '+(', '.join(t.name for t in student.academic_class.teachers) or 'No teacher assigned')+'.'
    if 'deadline' in text:
        nearest=min(pending,key=lambda r:r.deadline) if pending else None
        return f'Your next pending deadline is {nearest.deadline:%d %b %Y, %H:%M} UTC for {nearest.title}.' if nearest else 'You have no pending request deadlines.'
    if 'submitted' in text: return 'Submitted requests: '+('; '.join(r.title+' ('+subs[r.id].status.replace('_',' ').lower()+')' for r in items if r.id in subs and subs[r.id].status!='DRAFT') or 'None')+'.'
    if 'pending' in text or 'form' in text: return 'Pending requests: '+('; '.join(r.title for r in pending) or 'None')+'.'
    return "I couldn't find that information in the system. Ask about pending forms, deadlines, submissions, missing profile details, profile completion or your class teacher."
