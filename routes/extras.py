import io
import re
from flask import Blueprint, render_template, request, redirect, flash, abort, jsonify, send_file, current_app, url_for
from flask_login import current_user,login_required
from extensions import db
from models import *
from services.access import *
from services.common import required,integer,deadline,audit,notify,set_profile

bp=Blueprint('extras',__name__)

@bp.post('/api/suggest')
@roles('TEACHER')
def suggest():
    from ai.recommendation_engine import suggest
    payload=request.get_json(silent=True) or {}
    prompt=str(payload.get('prompt',''))[:2000]
    fields=suggest(prompt)
    db.session.add(AIInteraction(user_id=current_user.id,intent='form_recommendation')); db.session.commit()
    return jsonify(fields=fields,title='Internship Details Collection' if 'internship' in prompt.lower() else 'Placement Details Collection' if 'placement' in prompt.lower() else 'Student Information Collection',provider='Local keyword recommendations',message='Review and edit suggestions before publishing.' if fields else 'No matching fields found. Choose fields from the library or add a custom field.')

@bp.route('/assistant',methods=['GET','POST'])
@roles('STUDENT')
def assistant():
    response=None
    prompt=''
    if request.method=='POST':
        from ai.chatbot import answer
        prompt=required('prompt',2000)
        response=answer(prompt)
        db.session.add(AIInteraction(user_id=current_user.id,intent='student_assistant')); db.session.commit()
    return render_template('assistant.html',title='AI assistant',response=response,prompt=prompt)

@bp.route('/documents',methods=['GET','POST'])
@roles('STUDENT')
def documents():
    if request.method=='POST':
        from services.document_service import save_document
        upload=request.files.get('document')
        if not upload or not upload.filename: abort(400,'Choose a document.')
        doc=save_document(my_student(),upload); db.session.commit()
        flash(doc.ocr_status,'success')
        return redirect(f'/documents/{doc.id}/review')
    return render_template('documents.html',title='My documents',items=Document.query.filter_by(student_id=my_student().id).order_by(Document.created_at.desc()).all())

@bp.get('/documents/<int:doc_id>')
@roles('ADMIN','TEACHER','STUDENT')
def download_document(doc_id):
    from pathlib import Path
    doc=db.get_or_404(Document,doc_id); student_access(doc.student_id)
    audit('Document downloaded','document',doc.id); db.session.commit()
    response=send_file(Path(current_app.config['UPLOAD_FOLDER'])/doc.storage_name,as_attachment=True,download_name=doc.filename,mimetype=doc.mime)
    response.headers['X-Content-Type-Options']='nosniff'
    response.headers['Cache-Control']='private, no-store'
    return response

@bp.route('/documents/<int:doc_id>/review',methods=['GET','POST'])
@roles('STUDENT')
def document_review(doc_id):
    doc=Document.query.filter_by(id=doc_id,student_id=my_student().id).first_or_404()
    if request.method=='POST':
        # OCR is evidence for a pending teacher review, never an automatic profile merge.
        if request.form.get('confirmed')!='yes': abort(400,'Confirm that you reviewed the extracted text.')
        doc.extracted_text=required('text',30000)
        doc.ocr_status='Text reviewed by student; use in a data request for teacher verification'
        audit('OCR text confirmed','document',doc.id); db.session.commit()
        flash('Reviewed text saved. Copy the relevant details into your teacher’s request for verification.','success')
    candidates={}
    for key,pattern in {'email':r'[\w.+-]+@[\w.-]+\.[A-Za-z]{2,}', 'cgpa':r'(?i)CGPA\s*[:=]?\s*(\d+(?:\.\d+)?)'}.items():
        match=re.search(pattern,doc.extracted_text or '')
        if match: candidates[key]=match.group(1) if match.lastindex else match.group(0)
    return render_template('document_review.html',title='Review document extraction',doc=doc,candidates=candidates)

@bp.get('/students/<int:student_id>/qr')
@roles('ADMIN','TEACHER','STUDENT')
def qr(student_id):
    import qrcode
    student=student_access(student_id)
    buffer=io.BytesIO()
    qrcode.make(url_for('extras.qr_profile',token=student.qr_token,_external=True)).save(buffer,format='PNG'); buffer.seek(0)
    return send_file(buffer,mimetype='image/png',as_attachment=True,download_name='student-profile-qr.png')

@bp.get('/q/<token>')
@roles('ADMIN','TEACHER','STUDENT')
def qr_profile(token):
    student=Student.query.filter_by(qr_token=token).first_or_404()
    student_access(student.id)
    return redirect(f'/students/{student.id}')

@bp.route('/messages',methods=['GET','POST'])
@roles('ADMIN','TEACHER','STUDENT')
def messages():
    people=contacts()
    if request.method=='POST':
        recipient=integer('recipient_id')
        if recipient not in [p.id for p in people]: abort(403)
        item=MessageThread(sender_id=current_user.id,recipient_id=recipient,subject=required('subject'))
        db.session.add(item); db.session.flush()
        db.session.add(ChatMessage(thread_id=item.id,sender_id=current_user.id,body=required('body',10000)))
        notify(recipient,'New message',f'/messages/{item.id}',item.subject)
        db.session.commit()
        return redirect(f'/messages/{item.id}')
    items=MessageThread.query.filter((MessageThread.sender_id==current_user.id)|(MessageThread.recipient_id==current_user.id)).order_by(MessageThread.created_at.desc()).all()
    allowed={p.id for p in people}
    items=[t for t in items if (t.recipient_id if t.sender_id==current_user.id else t.sender_id) in allowed]
    return render_template('messages.html',title='Messages',items=items,contacts=people)

@bp.route('/messages/<int:thread_id>',methods=['GET','POST'])
@roles('ADMIN','TEACHER','STUDENT')
def thread(thread_id):
    item=db.get_or_404(MessageThread,thread_id)
    if current_user.id not in (item.sender_id,item.recipient_id): abort(403)
    other=item.recipient_id if item.sender_id==current_user.id else item.sender_id
    if other not in [p.id for p in contacts()]: abort(403)
    if request.method=='POST':
        db.session.add(ChatMessage(thread_id=item.id,sender_id=current_user.id,body=required('body',10000)))
        notify(other,'New reply',f'/messages/{item.id}',item.subject)
    for message in item.messages:
        if message.sender_id!=current_user.id: message.read=True
    db.session.commit()
    if request.method=='POST': return redirect(f'/messages/{item.id}')
    return render_template('thread.html',title=item.subject,item=item)

@bp.route('/activities',methods=['GET','POST'])
@roles('ADMIN','TEACHER','STUDENT')
def activities():
    dept_ids={c.department_id for c in classes()}
    if current_user.role=='ADMIN': dept_ids={d.id for d in Department.query.filter_by(admin_id=current_user.id).all()}
    if request.method=='POST':
        action=request.form.get('action')
        if current_user.role=='ADMIN':
            if action=='toggle':
                item=AcademicActivity.query.filter_by(id=integer('id'),admin_id=current_user.id).first_or_404()
                item.registration_open=not item.registration_open
            else:
                dept_id=integer('department_id')
                if dept_id not in dept_ids: abort(403)
                item=AcademicActivity(admin_id=current_user.id,department_id=dept_id,title=required('title'),description=request.form.get('description','')[:10000],event_date=deadline('event_date'),category=required('category',60))
                db.session.add(item)
            audit('Academic activity updated','activity',item.id)
        elif current_user.role=='STUDENT':
            item=db.get_or_404(AcademicActivity,integer('id'))
            if item.department_id not in dept_ids or not item.registration_open or item.event_date<now(): abort(403)
            existing=ActivityRegistration.query.filter_by(activity_id=item.id,student_id=my_student().id).first()
            if existing: db.session.delete(existing)
            else: db.session.add(ActivityRegistration(activity_id=item.id,student_id=my_student().id))
        else: abort(403)
        db.session.commit(); flash('Activity updated.','success'); return redirect('/activities')
    registrations={r.activity_id for r in ActivityRegistration.query.filter_by(student_id=my_student().id).all()} if current_user.role=='STUDENT' else set()
    return render_template('activities.html',title='Academic activities',items=AcademicActivity.query.filter(AcademicActivity.department_id.in_(dept_ids)).order_by(AcademicActivity.event_date).all(),departments=Department.query.filter(Department.id.in_(dept_ids)).all(),registrations=registrations,counts=lambda item:ActivityRegistration.query.filter_by(activity_id=item.id).count())
