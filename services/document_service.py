import io
import os
import uuid
from pathlib import Path
from flask import current_app, abort
from werkzeug.utils import secure_filename
from PIL import Image, UnidentifiedImageError
from extensions import db
from models import Document
from services.common import audit

def save_document(student, upload):
    name=secure_filename(upload.filename or '')
    ext=Path(name).suffix.lower()
    if ext not in ('.pdf','.png','.jpg','.jpeg'): abort(400,'Upload a PDF, PNG or JPEG document.')
    data=upload.read(current_app.config['MAX_CONTENT_LENGTH']+1)
    if not data or len(data)>current_app.config['MAX_CONTENT_LENGTH']: abort(400,'Document is empty or exceeds the upload limit.')
    if ext=='.pdf':
        if not data.startswith(b'%PDF-'): abort(400,'Invalid PDF content.')
        from pypdf import PdfReader
        try:
            reader=PdfReader(io.BytesIO(data))
            if reader.is_encrypted: abort(400,'Upload an unencrypted PDF.')
            if len(reader.pages)>100: abort(400,'PDFs are limited to 100 pages.')
        except Exception as error:
            if hasattr(error,'code'): raise
            abort(400,'The PDF could not be read.')
        mime='application/pdf'
    else:
        try:
            with Image.open(io.BytesIO(data)) as picture:
                if picture.width*picture.height>25_000_000: abort(400,'Image is too large.')
                actual=picture.format
                picture.verify()
            if actual not in ('PNG','JPEG') or actual=='PNG' and ext!='.png' or actual=='JPEG' and ext not in ('.jpg','.jpeg'): abort(400,'File content and extension do not match.')
        except (UnidentifiedImageError, OSError, Image.DecompressionBombError): abort(400,'Invalid image content.')
        mime='image/png' if ext=='.png' else 'image/jpeg'
    storage=uuid.uuid4().hex+ext
    path=Path(current_app.config['UPLOAD_FOLDER'])/storage
    path.write_bytes(data)
    doc=Document(student_id=student.id,filename=name,storage_name=storage,mime=mime)
    db.session.add(doc); db.session.flush()
    try:
        if ext=='.pdf':
            doc.extracted_text='\n'.join((p.extract_text() or '') for p in reader.pages)[:30000]
            doc.ocr_status='Text extracted; review before using' if doc.extracted_text else 'Scanned PDF: upload a page image for OCR, or enter details manually.'
        else:
            import pytesseract
            if os.getenv('TESSERACT_CMD'): pytesseract.pytesseract.tesseract_cmd=os.getenv('TESSERACT_CMD')
            doc.extracted_text=pytesseract.image_to_string(Image.open(path),timeout=20)[:30000]
            doc.ocr_status='Text extracted; review before using'
    except Exception:
        doc.ocr_status='OCR unavailable. Document saved; enter details manually.'
    audit('Document uploaded','document',doc.id)
    return doc
