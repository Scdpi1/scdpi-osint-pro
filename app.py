#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
SCDPI OSINT PRO - Aplicação Principal
Autor: Iskender Chanazaroff
Registro: 1411-16-DF
Versão: 2.0.0
"""

import os
import logging
from flask import Flask, render_template, jsonify, request, redirect, url_for
from flask_login import LoginManager, login_required, current_user
from dotenv import load_dotenv
import stripe

# Importações locais
from models import db, Usuario
from blockchain import BlockchainForense
from auth import auth_bp
from stripe_integration import stripe_bp

# Configuração de logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Carrega variáveis de ambiente
load_dotenv()

# ==============================================
# CONFIGURAÇÃO DO BANCO DE DADOS (CRÍTICO PARA O RENDER)
# ==============================================
# Detecta se está rodando no Render
if os.getenv('RENDER'):
    # No Render, usa /tmp que tem permissão de escrita
    DATABASE_URL = 'sqlite:////tmp/scdpi.db'
    logger.info("🌐 Rodando no Render - usando banco em /tmp/scdpi.db")
else:
    # Localmente, usa a variável de ambiente ou arquivo local
    DATABASE_URL = os.getenv('DATABASE_URL', 'sqlite:///scdpi.db')
    logger.info(f"💻 Rodando localmente - usando banco em {DATABASE_URL}")

# ==============================================
# INICIALIZAÇÃO DO FLASK
# ==============================================
app = Flask(__name__,
            template_folder='templates',
            static_folder='.')

# Configurações básicas
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'chave-secreta-padrao-mude-isso')
app.config['SQLALCHEMY_DATABASE_URI'] = DATABASE_URL
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Inicializa extensões
db.init_app(app)

# ==============================================
# CONFIGURAÇÃO DO LOGIN MANAGER
# ==============================================
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'auth.login'
login_manager.login_message = 'Por favor, faça login para acessar esta página.'

@login_manager.user_loader
def load_user(user_id):
    """Carrega usuário do banco de dados pelo ID"""
    return Usuario.query.get(int(user_id))

# ==============================================
# INICIALIZAÇÃO DA BLOCKCHAIN FORENSE
# ==============================================
blockchain = BlockchainForense()

# ==============================================
# CONFIGURAÇÃO DO STRIPE
# ==============================================
stripe.api_key = os.getenv('STRIPE_SECRET_KEY')

# ==============================================
# REGISTRO DOS BLUEPRINTS
# ==============================================
app.register_blueprint(auth_bp)
app.register_blueprint(stripe_bp, url_prefix='/stripe')

# ==============================================
# ROTAS PRINCIPAIS
# ==============================================

@app.route('/')
def index():
    """Página inicial"""
    return render_template('index.html')

@app.route('/planos')
def planos():
    """Página de planos de assinatura"""
    return render_template('planos.html')

@app.route('/dashboard')
@login_required
def dashboard():
    """Dashboard do usuário logado"""
    return render_template('dashboard.html', usuario=current_user)

@app.route('/api/consultar', methods=['POST'])
@login_required
def consultar():
    """Endpoint para realizar consultas OSINT"""
    dados = request.get_json()
    tipo = dados.get('tipo')
    termo = dados.get('termo')
    
    # Verifica limite de consultas
    if current_user.consultas_restantes <= 0:
        return jsonify({'erro': 'Limite de consultas excedido'}), 403
    
    # Simulação de consulta (depois substituiremos por APIs reais)
    resultado = {
        'mensagem': f'Consulta simulada de {tipo}: {termo}',
        'tipo': tipo,
        'termo': termo,
        'status': 'sucesso'
    }
    
    # Decrementa consultas
    current_user.consultas_restantes -= 1
    db.session.commit()
    
    # Registra na blockchain forense
    blockchain.registrar(
        usuario_id=current_user.id,
        acao=f'consulta_{tipo}',
        dados={'termo': termo, 'resultado': resultado}
    )
    
    return jsonify(resultado)

# ==============================================
# CRIAÇÃO AUTOMÁTICA DO BANCO DE DADOS
# ==============================================
def init_database():
    """Inicializa o banco de dados criando as tabelas se necessário"""
    try:
        with app.app_context():
            db.create_all()
            logger.info("✅ Banco de dados verificado/criado com sucesso!")
            
            # Verifica se já existe um usuário admin
            if not Usuario.query.filter_by(email='admin@scdpi.com').first():
                # Cria um usuário admin padrão (opcional)
                from werkzeug.security import generate_password_hash
                admin = Usuario(
                    email='admin@scdpi.com',
                    senha_hash=generate_password_hash('admin123'),
                    nome='Administrador',
                    registro_profissional='ADMIN001',
                    plano='enterprise',
                    consultas_restantes=999999
                )
                db.session.add(admin)
                db.session.commit()
                logger.info("✅ Usuário admin criado (admin@scdpi.com / admin123)")
    except Exception as e:
        logger.error(f"❌ Erro ao criar banco de dados: {e}")

# Executa a criação do banco
init_database()

# ==============================================
# INÍCIO DO SERVIDOR (PARA TESTES LOCAIS)
# ==============================================
if __name__ == '__main__':
    logger.info("🚀 Iniciando servidor de desenvolvimento...")
    app.run(debug=True, host='0.0.0.0', port=5000)
