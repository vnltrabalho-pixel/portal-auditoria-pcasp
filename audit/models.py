from auth.models import db
from datetime import datetime
from enum import Enum
import json

class StatusAuditoria(Enum):
    """Status da Auditoria"""
    PROCESSANDO = 'processando'
    CONCLUIDA = 'concluida'
    ERRO = 'erro'
    AVISO = 'aviso'

class Auditoria(db.Model):
    """Model de Auditoria"""
    __tablename__ = 'auditorias'
    
    id = db.Column(db.Integer, primary_key=True)
    usuario_id = db.Column(db.Integer, db.ForeignKey('usuarios.id'), nullable=False, index=True)
    
    # Informações da Auditoria
    mes = db.Column(db.Integer, nullable=False)
    ano = db.Column(db.Integer, nullable=False)
    ug = db.Column(db.String(20), nullable=False)
    nome_arquivo = db.Column(db.String(255), nullable=False)
    
    # Status
    status = db.Column(db.String(20), default=StatusAuditoria.PROCESSANDO.value)
    descricao_erro = db.Column(db.Text, nullable=True)
    
    # Resultados
    total_linhas = db.Column(db.Integer, default=0)
    contas_validadas = db.Column(db.Integer, default=0)
    erros_encontrados = db.Column(db.Integer, default=0)
    avisos_encontrados = db.Column(db.Integer, default=0)
    
    # Dados JSON de validação
    resultado_json = db.Column(db.JSON, nullable=True)
    
    # Timestamps
    criado_em = db.Column(db.DateTime, default=datetime.utcnow, index=True)
    processado_em = db.Column(db.DateTime, nullable=True)
    
    def __repr__(self):
        return f'<Auditoria {self.mes}/{self.ano} - {self.status}>'
    
    def to_dict(self):
        """Serializa para dict"""
        return {
            'id': self.id,
            'mes': self.mes,
            'ano': self.ano,
            'ug': self.ug,
            'nome_arquivo': self.nome_arquivo,
            'status': self.status,
            'total_linhas': self.total_linhas,
            'contas_validadas': self.contas_validadas,
            'erros_encontrados': self.erros_encontrados,
            'avisos_encontrados': self.avisos_encontrados,
            'criado_em': self.criado_em.isoformat(),
            'processado_em': self.processado_em.isoformat() if self.processado_em else None
        }
