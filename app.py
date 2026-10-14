import os
from pathlib import Path
from flask import Flask, render_template, redirect, url_for, request, session
from flask_login import current_user, logout_user
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from config import Config
from extensions import db, login_manager, migrate, csrf

def create_app(test_config=None):
    app = Flask(__name__)
    app.config.from_object(Config)
    if test_config:
        app.config.update(test_config)
    if not app.config['SECRET_KEY'] or app.config['SECRET_KEY'].startswith('replace-this'):
        if os.getenv('FLASK_ENV') == 'production':
            raise RuntimeError('Set a strong SECRET_KEY before production startup.')
        # Stable development secret, generated once and kept out of source control.
        import secrets
        Path(app.instance_path).mkdir(exist_ok=True)
        secret_path = Path(app.instance_path) / '.secret'
        if not secret_path.exists():
            secret_path.write_text(secrets.token_hex(32))
        app.config['SECRET_KEY'] = secret_path.read_text()
    Path(app.config['UPLOAD_FOLDER']).mkdir(parents=True, exist_ok=True)
    db.init_app(app)
    login_manager.init_app(app)
    login_manager.login_view = 'auth.portal'
    login_manager.session_protection = 'strong'
    migrate.init_app(app, db)
    csrf.init_app(app)
    from models import User, Notification, SystemSetting
    @login_manager.user_loader
    def load_user(user_id):
        user = db.session.get(User, int(user_id))
        return user if user and user.active else None
    from routes.auth import bp as auth
    from routes.core import bp as core
    from routes.management import bp as management
    from routes.collection import bp as collection
    from routes.extras import bp as extras
    from routes.workspace import bp as workspace
    from routes.student_workflows import bp as student_workflows
    for blueprint in (auth, core, management, collection, extras, workspace, student_workflows):
        app.register_blueprint(blueprint)
    @app.before_request
    def password_gate():
        if current_user.is_authenticated:
            session.permanent = True
            if current_user.first_login and request.endpoint not in ('auth.password', 'auth.logout', 'static'):
                return redirect(url_for('auth.password'))
    @app.context_processor
    def context():
        from services.access import navigation
        from urllib.parse import urlencode
        def page_url(page):
            args=request.args.to_dict(flat=False)
            args['page']=[str(page)]
            return request.path+'?'+urlencode(args,doseq=True)
        unread = Notification.query.filter_by(user_id=current_user.id, read=False).count() if current_user.is_authenticated else 0
        return {'nav_items': navigation() if current_user.is_authenticated else [], 'unread': unread,
                'institution': app.config['INSTITUTION_NAME'], 'page_url':page_url}
    @app.after_request
    def response_headers(response):
        response.headers['X-Content-Type-Options']='nosniff'
        response.headers['X-Frame-Options']='SAMEORIGIN'
        response.headers['Referrer-Policy']='same-origin'
        if current_user.is_authenticated:
            response.headers['Cache-Control']='private, no-store'
        return response
    @app.template_filter('human')
    def human(value):
        return str(value or '').replace('_', ' ').title()
    for code in (400, 403, 404, 413, 429, 500):
        app.register_error_handler(code, lambda error: (render_template('error.html', title=str(error.code), error=error), error.code))
    @app.errorhandler(IntegrityError)
    def duplicate(error):
        db.session.rollback()
        return render_template('error.html', title='Duplicate record', error='That username, email, register number or name already exists. Go back and use a unique value.'), 409
    @app.errorhandler(SQLAlchemyError)
    def database_error(error):
        db.session.rollback()
        app.logger.exception('Database operation failed')
        return render_template('error.html', title='Database unavailable', error='Check your database configuration and run scripts/setup_database.py.'), 503
    return app

if __name__ == '__main__':
    create_app().run(host='127.0.0.1', port=int(os.getenv('PORT', '5000')), debug=False)
