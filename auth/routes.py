from flask import Blueprint, render_template, request, redirect, url_for, flash, session
from flask_login import login_user, logout_user, login_required, current_user
from auth.models import db, Usuario
from functools import wraps

auth_bp = Blueprint('auth', __name__, url_prefix='/auth')

# Usuários pré-criados (segurança básica)
USUARIOS_PADRAO = {
    'admin': 'senha123',  # MUDE ISSO EM PRODUÇÃO
    'teste': 'teste123'
}

def init_usuarios_padrao():
    """Cria usuários padrão se não existirem"""
    for username, password in USUARIOS_PADRAO.items():
        if not Usuario.query.filter_by(username=username).first():
            usuario = Usuario(
                username=username,
                email=f'{username}@auditoria.local'
            )
            usuario.set_password(password)
            db.session.add(usuario)
    db.session.commit()

@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    """Login de usuário"""
    if current_user.is_authenticated:
        return redirect(url_for('main.dashboard'))
    
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        
        usuario = Usuario.query.filter_by(username=username).first()
        
        if usuario and usuario.check_password(password) and usuario.ativo:
            login_user(usuario, remember=request.form.get('remember'))
            next_page = request.args.get('next')
            return redirect(next_page) if next_page else redirect(url_for('main.dashboard'))
        else:
            flash('Usuário ou senha inválidos', 'error')
    
    return render_template('login.html')

@auth_bp.route('/logout')
@login_required
def logout():
    """Logout de usuário"""
    logout_user()
    flash('Você foi desconectado', 'info')
    return redirect(url_for('auth.login'))
