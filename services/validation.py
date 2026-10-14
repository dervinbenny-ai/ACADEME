import re
from decimal import Decimal, InvalidOperation
from datetime import date
from urllib.parse import urlparse
from flask import abort
from services.common import email, phone, IDENTITY

TYPES = {'text','textarea','number','decimal','date','email','phone','url','select','multiselect','radio','checkbox','file'}

def validate_fields(fields):
    if not isinstance(fields,list) or not 1 <= len(fields) <= 60: abort(400,'Choose between 1 and 60 fields.')
    keys = set()
    result = []
    for index,f in enumerate(fields):
        if not isinstance(f,dict): abort(400,'Invalid field definition.')
        key=str(f.get('key','')).strip().lower()
        kind=f.get('type','text')
        if not re.fullmatch(r'[a-z][a-z0-9_]{0,79}',key) or key in keys or kind not in TYPES or key in {'csrf_token','action','password','role','class_id','student_id','teacher_id','request_id'} or key.startswith('confirm_'): abort(400,'Field keys must be unique lowercase identifiers, must not use system-reserved names, and field types must be supported.')
        keys.add(key)
        options = f.get('options',[])
        if not isinstance(options,list) or len(options)>100 or any(not isinstance(x,str) or len(x)>200 for x in options): abort(400,'Invalid options.')
        if kind in ('select','multiselect','radio') and not options: abort(400,'Choice fields need options.')
        validation = f.get('validation',{})
        if not isinstance(validation,dict): abort(400,'Invalid validation settings.')
        for bound in ('min','max'):
            if validation.get(bound) not in (None,''):
                try: validation[bound] = float(validation[bound])
                except (ValueError,TypeError): abort(400,'Validation bounds must be numbers.')
        reuse = f.get('reuse','auto')
        if reuse not in ('auto','confirm','update'): abort(400,'Invalid reuse policy.')
        if key in IDENTITY: reuse='auto'
        result.append(dict(key=key,label=str(f.get('label',key))[:120],type=kind,required=bool(f.get('required',True)),reuse=reuse,
                           options=options,validation=validation,placeholder=str(f.get('placeholder',''))[:200],help_text=str(f.get('help_text',''))[:300],position=index))
    return result

def validate_value(field, value, draft=False):
    value = str(value).strip()
    if not value:
        if field.required and not draft: abort(400,f'{field.label} is required.')
        return ''
    if len(value)>10000: abort(400,f'{field.label} is too long.')
    if field.type in ('number','decimal'):
        try:
            n=Decimal(value)
            if not n.is_finite() or field.type=='number' and n != n.to_integral_value(): raise InvalidOperation
        except InvalidOperation: abort(400,f'{field.label} must be a valid number.')
        lower=field.validation.get('min',0 if field.key in ('cgpa','backlogs','stipend') else None)
        upper=field.validation.get('max',10 if field.key=='cgpa' else None)
        if lower not in (None,'') and n<Decimal(str(lower)) or upper not in (None,'') and n>Decimal(str(upper)): abort(400,f'{field.label} is outside the allowed range.')
    if field.type=='email': value=email(value)
    if field.type=='date':
        try:
            parsed_date = date.fromisoformat(value)
            if parsed_date.isoformat() != value: raise ValueError
        except ValueError: abort(400,f'{field.label} must be a date.')
    if field.type=='phone': value=phone(value)
    if field.type=='url' and (urlparse(value).scheme not in ('http','https') or not urlparse(value).netloc): abort(400,'Use a full http or https URL.')
    if field.type in ('select','radio') and value not in field.options: abort(400,'Invalid choice.')
    if field.type=='multiselect' and any(v not in field.options for v in value.split(' | ')): abort(400,'Invalid choices.')
    if field.type=='checkbox' and value not in ('Yes','No'): abort(400,'Invalid checkbox value.')
    return value
