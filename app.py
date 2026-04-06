from flask import Flask, render_template, redirect, url_for
from flask_login import LoginManager, current_user
from config import config
import os

def create_app(config_name='development'):
    """Factory Flask"""
    app = Flask(__name__)
    
    # Config
    app.config.from_object(config[config_name])
    
    # Create folders
    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
    os.makedirs('db', exist_ok=True)
    
    # Database
    from auth.models import db
    db.init_app(app)
    
    # Login Manager
    login_manager = LoginManager()
    login_manager.init_app(app)
    login_manager.login_view = 'auth.login'
    login_manager.login_message = 'Por favor, faça login para acessar.'
    login_manager.login_message_category = 'info'
    
    @login_manager.user_loader
    def load_user(user_id):
        from auth.models import Usuario
        return Usuario.query.get(int(user_id))
    
    # Create database
    with app.app_context():
        db.create_all()
        from auth.routes import init_usuarios_padrao
        init_usuarios_padrao()
    
    # Blueprints
    from auth.routes import auth_bp
    from audit.routes import audit_bp
    
    app.register_blueprint(auth_bp)
    app.register_blueprint(audit_bp)
    
    # Routes
    @app.route('/')
    def index():
        if current_user.is_authenticated:
            return redirect(url_for('dashboard'))
        return redirect(url_for('auth.login'))
    
    @app.route('/dashboard')
    @current_user.is_authenticated
    def dashboard():
        from audit.models import Auditoria
        auditorias = Auditoria.query.filter_by(usuario_id=current_user.id)\
            .order_by(Auditoria.criado_em.desc()).all()
        return render_template('dashboard.html', auditorias=auditorias)
    
    # Error handlers
    @app.errorhandler(404)
    def not_found(error):
        return render_template('404.html'), 404
    
    @app.errorhandler(500)
    def server_error(error):
        return render_template('500.html'), 500
    
    return app

if __name__ == '__main__':
    app = create_app()
    app.run(debug=True, host='0.0.0.0', port=5000)
