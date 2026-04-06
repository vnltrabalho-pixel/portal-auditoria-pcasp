import os
from datetime import timedelta

class Config:
    """Configuração Base"""
    # Flask
    SECRET_KEY = os.getenv('SECRET_KEY', 'dev-secret-key-change-in-production')
    DEBUG = os.getenv('DEBUG', 'False') == 'True'
    
    # Banco de Dados
    SQLALCHEMY_DATABASE_URI = os.getenv(
        'DATABASE_URL',
        'sqlite:///db/auditoria.db'
    )
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    
    # Sessão
    PERMANENT_SESSION_LIFETIME = timedelta(hours=24)
    SESSION_COOKIE_SECURE = True
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = 'Lax'
    
    # Upload
    UPLOAD_FOLDER = os.path.join(os.path.dirname(__file__), 'uploads')
    MAX_CONTENT_LENGTH = 50 * 1024 * 1024  # 50MB
    ALLOWED_EXTENSIONS = {'csv'}
    
    # Auditoria
    CSV_ENCODING = 'latin1'
    CSV_SEPARATOR = ';'
    DECIMAL_SEPARATOR = ','
    THOUSANDS_SEPARATOR = '.'
    
    # UI - Cores e Tema
    PRIMARY_COLOR = '#2E5A47'  # Verde Alpino
    SECONDARY_COLOR = '#1a1a1a'  # Dark Background
    ACCENT_COLOR = '#4CAF50'  # Verde claro para destaque
    DANGER_COLOR = '#f44336'  # Vermelho para erros
    SUCCESS_COLOR = '#4CAF50'  # Verde para sucesso
    
    # Validação
    TOLERANCE_DIFFERENCE = 0.01  # Tolerância para arredondamento

class DevelopmentConfig(Config):
    """Desenvolvimento"""
    DEBUG = True
    TESTING = False

class ProductionConfig(Config):
    """Produção"""
    DEBUG = False
    TESTING = False
    SESSION_COOKIE_SECURE = True

class TestingConfig(Config):
    """Testes"""
    TESTING = True
    SQLALCHEMY_DATABASE_URI = 'sqlite:///:memory:'

# Selector
config_name = os.getenv('FLASK_ENV', 'development')
config = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
    'testing': TestingConfig,
}
