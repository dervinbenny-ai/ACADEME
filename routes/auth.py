from datetime import timedelta
from flask import Blueprint, render_template, request, redirect, url_for, flash, session, abort
from flask_login import login_user, logout_user, login_required, current_user
from sqlalchemy import or_
from extensions import db
from models import User, now
from services.common import audit, password_valid

bp = Blueprint('auth', __name__)

@bp.route('/')
def portal():
    if current_user.is_authenticated: return redirect(url_for('core.dashboard'))
    return render_template('portal.html', title='Welcome')

@bp.route('/<portal>/login', methods=['GET','POST'])
def login(portal):
    allowed = {'admin':('SUPER_ADMIN','ADMIN'), 'teacher':('TEACHER',), 'student':('STUDENT',)}
    if portal not in allowed: abort(404)
    if current_user.is_authenticated: return redirect(url_for('core.dashboard'))
    if request.method == 'POST':
        identifier = request.form.get('username','').strip().lower()
        user = User.query.filter(or_(User.username == identifier, User.email == identifier)).first()
        error = None
        if user and user.locked_until and user.locked_until > now(): error = 'Too many attempts. Please try again in 15 minutes.'
        elif not user or not user.check_password(request.form.get('password','')):
            error = 'Invalid username or password.'
            if user:
                user.failed_logins += 1
                if user.failed_logins >= 5: user.locked_until = now() + timedelta(minutes=15)
        elif not user.active: error = 'This account is deactivated. Contact your administrator.'
        elif user.role not in allowed[portal]: error = f'This account is not authorized for the {portal.title()} Portal.'
        if error:
            db.session.commit()
            flash(error,'danger')
        else:
            session.clear()
            login_user(user, remember='remember' in request.form)
            user.last_login = now()
            user.failed_logins = 0
            user.locked_until = None
            audit('Login','user',user.id)
            db.session.commit()
            return redirect(url_for('auth.password' if user.first_login else 'core.dashboard'))
    return render_template('login.html', title=f'{portal.title()} portal', portal=portal)

@bp.post('/logout')
@login_required
def logout():
    audit('Logout','user',current_user.id)
    db.session.commit()
    logout_user()
    session.clear()
    return redirect(url_for('auth.portal'))

@bp.route('/password',methods=['GET','POST'])
@login_required
def password():
    if request.method == 'POST':
        value = request.form.get('password','')
        if not current_user.check_password(request.form.get('current_password','')): flash('Current password is incorrect.','danger')
        elif not password_valid(value): flash('Use at least 12 characters, including letters and numbers.','danger')
        elif value != request.form.get('confirm_password'): flash('Passwords do not match.','danger')
        elif current_user.check_password(value): flash('Choose a different password.','danger')
        else:
            current_user.set_password(value)
            current_user.first_login = False
            audit('Password changed','user',current_user.id)
            db.session.commit()
            flash('Password updated. Your account is ready.','success')
            return redirect(url_for('core.dashboard'))
    return render_template('password.html',title='Password & security')

@bp.route('/forgot-password',methods=['GET','POST'])
def forgot():
    if request.method == 'POST':
        from services.common import notify
        user = User.query.filter_by(email=request.form.get('email','').strip().lower()).first()
        if user and user.created_by:
            notify(user.created_by,'Password reset requested','/users' if user.role != 'STUDENT' else '/students',f'{user.name} requested an account reset.')
            db.session.commit()
        flash('If this account exists, its account manager has been notified. Contact your teacher or administrator to receive new temporary credentials.','success')
    return render_template('forgot.html',title='Account recovery')
