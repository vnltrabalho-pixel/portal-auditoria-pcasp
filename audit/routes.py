from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify, current_app
from flask_login import login_required, current_user
from werkzeug.utils import secure_filename
import os
from datetime import datetime
from audit.models import db, Auditoria, StatusAuditoria
from audit.parser import ParserCSVFiorilli
from audit.validators import ValidadorPCAsp
import json

audit_bp = Blueprint('audit_bp', __name__, url_prefix='/audit')

def allowed_file(filename):
    """Valida extensão do arquivo"""
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in {'csv'}

@audit_bp.route('/upload', methods=['GET', 'POST'])
@login_required
def upload():
    """Upload de novo CSV para auditoria"""
    if request.method == 'POST':
        # Validar arquivo
        if 'arquivo' not in request.files:
            flash('Nenhum arquivo foi enviado', 'error')
            return redirect(request.url)
        
        file = request.files['arquivo']
        
        if file.filename == '':
            flash('Arquivo não selecionado', 'error')
            return redirect(request.url)
        
        if not allowed_file(file.filename):
            flash('Apenas arquivos CSV são permitidos', 'error')
            return redirect(request.url)
        
        try:
            # Salvar arquivo temporariamente
            filename = secure_filename(file.filename)
            upload_dir = current_app.config['UPLOAD_FOLDER']
            os.makedirs(upload_dir, exist_ok=True)
            
            filepath = os.path.join(upload_dir, f"{datetime.now().timestamp()}_{filename}")
            file.save(filepath)
            
            # Criar registro de auditoria
            auditoria = Auditoria(
                usuario_id=current_user.id,
                mes=int(request.form.get('mes', 0)),
                ano=int(request.form.get('ano', 0)),
                ug=request.form.get('ug', ''),
                nome_arquivo=filename,
                status=StatusAuditoria.PROCESSANDO.value
            )
            db.session.add(auditoria)
            db.session.commit()
            
            # Processar
            processar_auditoria(auditoria.id, filepath)
            
            flash(f'Auditoria #{auditoria.id} processada com sucesso!', 'success')
            return redirect(url_for('audit_bp.resultado', auditoria_id=auditoria.id))
        
        except Exception as e:
            flash(f'Erro ao processar arquivo: {str(e)}', 'error')
            return redirect(request.url)
    
    return render_template('upload.html')

@audit_bp.route('/resultado/<int:auditoria_id>')
@login_required
def resultado(auditoria_id):
    """Exibe resultado da auditoria"""
    auditoria = Auditoria.query.filter_by(
        id=auditoria_id,
        usuario_id=current_user.id
    ).first_or_404()
    
    resultado = json.loads(auditoria.resultado_json) if auditoria.resultado_json else {}
    
    return render_template('resultado.html', auditoria=auditoria, resultado=resultado)

@audit_bp.route('/historico')
@login_required
def historico():
    """Exibe histórico de auditorias do usuário"""
    auditorias = Auditoria.query.filter_by(usuario_id=current_user.id)\
        .order_by(Auditoria.criado_em.desc()).all()
    
    return render_template('historico.html', auditorias=auditorias)

@audit_bp.route('/exportar/<int:auditoria_id>/pdf')
@login_required
def exportar_pdf(auditoria_id):
    """Exporta resultado em PDF"""
    flash('Exportação PDF em desenvolvimento', 'info')
    return redirect(url_for('audit_bp.resultado', auditoria_id=auditoria_id))

@audit_bp.route('/exportar/<int:auditoria_id>/excel')
@login_required
def exportar_excel(auditoria_id):
    """Exporta resultado em Excel"""
    flash('Exportação Excel em desenvolvimento', 'info')
    return redirect(url_for('audit_bp.resultado', auditoria_id=auditoria_id))

def processar_auditoria(auditoria_id: int, filepath: str):
    """Processa a auditoria"""
    auditoria = Auditoria.query.get(auditoria_id)
    
    try:
        # Parser
        parser = ParserCSVFiorilli(filepath)
        df, erros_parse = parser.processar()
        
        if df is None:
            auditoria.status = StatusAuditoria.ERRO.value
            auditoria.descricao_erro = '; '.join(erros_parse)
            db.session.commit()
            return
        
        auditoria.total_linhas = len(df)
        
        # Validar
        validador = ValidadorPCAsp(df)
        resultado = validador.executar_todas_validacoes()
        
        # Atualizar auditoria
        auditoria.contas_validadas = resultado['contas_validadas']
        auditoria.erros_encontrados = resultado['resumo']['total_erros']
        auditoria.avisos_encontrados = resultado['resumo']['total_avisos']
        auditoria.resultado_json = json.dumps(resultado, default=str)
        auditoria.status = resultado['resumo']['status']
        auditoria.processado_em = datetime.utcnow()
        
        db.session.commit()
        
    except Exception as e:
        auditoria.status = StatusAuditoria.ERRO.value
        auditoria.descricao_erro = str(e)
        db.session.commit()
    finally:
        # Limpar arquivo
        if os.path.exists(filepath):
            os.remove(filepath)
