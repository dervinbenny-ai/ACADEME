from collections import Counter
from services.common import completion,request_stats

def charts(students,requirements,requests):
    distributions=[('Students by department',Counter(s.academic_class.department.name for s in students)),
                   ('Students by class',Counter(s.academic_class.name for s in students)),
                   ('Requirements by status',Counter(r.status.replace('_',' ').title() for r in requirements)),
                   ('Monthly request activity',Counter(r.created_at.strftime('%Y-%m') for r in requests)),
                   ('Profile completion',Counter('Complete' if completion(s)[0]==100 else '50–99%' if completion(s)[0]>=50 else 'Below 50%' for s in students)),
                   ('Submission completion',Counter({'Submitted':sum(request_stats(r)['submitted'] for r in requests),'Pending':sum(request_stats(r)['pending'] for r in requests)}))]
    return [{'title':title,'labels':list(data),'values':list(data.values())} for title,data in distributions]
