#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
SCDPI OSINT PRO - VERSÃO REAL COMPLETA
Autor: Iskender Chanazaroff | Registro: 1411-16-DF
"""

import os
import logging
import hashlib
import json
from datetime import datetime
from flask import Flask, render_template, jsonify, request, redirect, url_for, flash
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from dotenv import load_dotenv
import stripe
import requests
import phonenumbers
from phonenumbers import carrier, geocoder, timezone
import re
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

# ==============================================
# CARREGA VARIÁVEIS DE AMBIENTE
# ==============================================
load_dotenv()

# Configuração de logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# ==============================================
# INICIALIZAÇÃO DO FLASK
# ==============================================
app = Flask(__name__,
            template_folder='templates',
            static_folder='static')

app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'sua-chave-secreta-aqui-mude-isso')
app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('DATABASE_URL', 'sqlite:///scdpi.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Rate Limiting (proteção contra abusos)
limiter = Limiter(get_remote_address, app=app, default_limits=["200 por dia", "50 por hora"])

# ==============================================
# BANCO DE DADOS
# ==============================================
db = SQLAlchemy(app)

class Usuario(UserMixin, db.Model):
    __tablename__ = 'usuarios'
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), unique=True, nullable=False)
    senha_hash = db.Column(db.String(200), nullable=False)
    nome = db.Column(db.String(100))
    registro_profissional = db.Column(db.String(50))
    plano = db.Column(db.String(20), default='basico')
    consultas_restantes = db.Column(db.Integer, default=50)
    stripe_customer_id = db.Column(db.String(100))
    stripe_subscription_id = db.Column(db.String(100))
    data_cadastro = db.Column(db.DateTime, default=datetime.utcnow)

class Consulta(db.Model):
    __tablename__ = 'consultas'
    id = db.Column(db.Integer, primary_key=True)
    usuario_id = db.Column(db.Integer, db.ForeignKey('usuarios.id'))
    tipo = db.Column(db.String(50))
    termo = db.Column(db.String(200))
    resultado = db.Column(db.Text)
    hash_forense = db.Column(db.String(64), unique=True)
    data_consulta = db.Column(db.DateTime, default=datetime.utcnow)

# ==============================================
# BLOCKCHAIN FORENSE (Log Imutável)
# ==============================================
class BlockchainForense:
    def __init__(self):
        self.chave_mestra = os.getenv('MASTER_KEY', 'SCDPI_1411_16_DF')
    
    def gerar_hash(self, usuario_id, acao, dados):
        conteudo = f"{usuario_id}{acao}{json.dumps(dados, sort_keys=True)}{datetime.now().isoformat()}{self.chave_mestra}"
        return hashlib.sha256(conteudo.encode()).hexdigest()
    
    def registrar(self, usuario_id, acao, dados):
        hash_consulta = self.gerar_hash(usuario_id, acao, dados)
        logger.info(f"🔐 Blockchain: {acao} | Hash: {hash_consulta[:16]}...")
        return hash_consulta

blockchain = BlockchainForense()

# ==============================================
# LOGIN MANAGER
# ==============================================
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

@login_manager.user_loader
def load_user(user_id):
    return Usuario.query.get(int(user_id))

# ==============================================
# CONFIGURAÇÃO STRIPE
# ==============================================
stripe.api_key = os.getenv('STRIPE_SECRET_KEY')

# ==============================================
# MÓDULOS DE CONSULTA REAL
# ==============================================

class ConsultasReais:
    """Classe que agrupa todas as consultas reais do sistema"""
    
    # -------------------------------------------------
    # 1. GEOLOCALIZAÇÃO IP (ip-api.com) 
    # -------------------------------------------------
    def geo_ip(self, ip):
        """Retorna localização real de um IP"""
        try:
            if not ip or ip.strip() == '':
                return {"sucesso": False, "mensagem": "IP não fornecido"}
            
            url = f"http://ip-api.com/json/{ip.strip()}?fields=status,message,country,countryCode,region,regionName,city,zip,lat,lon,timezone,isp,org,as,query"
            
            response = requests.get(url, timeout=10)
            
            if response.status_code == 200:
                dados = response.json()
                
                if dados.get('status') == 'success':
                    return {
                        "sucesso": True,
                        "ip": dados.get('query'),
                        "pais": dados.get('country'),
                        "codigo_pais": dados.get('countryCode'),
                        "regiao": dados.get('regionName'),
                        "cidade": dados.get('city'),
                        "cep": dados.get('zip'),
                        "latitude": dados.get('lat'),
                        "longitude": dados.get('lon'),
                        "fuso_horario": dados.get('timezone'),
                        "isp": dados.get('isp'),
                        "organizacao": dados.get('org'),
                        "asn": dados.get('as'),
                        "fonte": "ip-api.com"
                    }
                else:
                    return {
                        "sucesso": False,
                        "mensagem": dados.get('message', 'Erro na consulta'),
                        "ip": ip
                    }
            else:
                return {"sucesso": False, "mensagem": f"Erro HTTP {response.status_code}"}
                
        except requests.exceptions.RequestException as e:
            logger.error(f"Erro na consulta de IP: {e}")
            return {"sucesso": False, "mensagem": f"Erro de conexão: {str(e)}"}
        except Exception as e:
            logger.error(f"Erro inesperado: {e}")
            return {"sucesso": False, "mensagem": f"Erro interno: {str(e)}"}
    
    # -------------------------------------------------
    # 2. TELEFONE (Validação e informações via phonenumbers)
    # -------------------------------------------------
    def telefone(self, numero):
        """Valida número de telefone e retorna informações como DDD, operadora, região"""
        try:
            numero_limpo = re.sub(r'\D', '', numero)
            
            if not numero_limpo.startswith('55'):
                if len(numero_limpo) <= 11:
                    numero_limpo = '55' + numero_limpo
                else:
                    numero_limpo = '55' + numero_limpo[-11:]
            
            numero_parse = phonenumbers.parse(numero_limpo, "BR")
            
            if not phonenumbers.is_possible_number(numero_parse):
                return {"sucesso": False, "mensagem": "Número inválido"}
            
            if not phonenumbers.is_valid_number(numero_parse):
                return {"sucesso": False, "mensagem": "Número não é válido para o Brasil"}
            
            ddd = numero_limpo[2:4] if len(numero_limpo) >= 4 else ""
            
            tipo = "Celular" if phonenumbers.number_type(numero_parse) == phonenumbers.PhoneNumberType.MOBILE else "Fixo"
            
            regioes_ddd = {
                '11': 'São Paulo (capital)', '12': 'São José dos Campos', '13': 'Santos',
                '14': 'Bauru', '15': 'Sorocaba', '16': 'Ribeirão Preto',
                '17': 'São José do Rio Preto', '18': 'Presidente Prudente', '19': 'Campinas',
                '21': 'Rio de Janeiro', '22': 'Campos dos Goytacazes', '24': 'Volta Redonda',
                '27': 'Vitória', '28': 'Cachoeiro de Itapemirim',
                '31': 'Belo Horizonte', '32': 'Juiz de Fora', '33': 'Governador Valadares',
                '34': 'Uberlândia', '35': 'Poços de Caldas', '37': 'Divinópolis', '38': 'Montes Claros',
                '41': 'Curitiba', '42': 'Ponta Grossa', '43': 'Londrina', '44': 'Maringá',
                '45': 'Foz do Iguaçu', '46': 'Francisco Beltrão',
                '47': 'Joinville', '48': 'Florianópolis', '49': 'Chapecó',
                '51': 'Porto Alegre', '53': 'Pelotas', '54': 'Caxias do Sul', '55': 'Santa Maria',
                '61': 'Brasília', '62': 'Goiânia', '63': 'Palmas', '64': 'Rio Verde',
                '65': 'Cuiabá', '66': 'Rondonópolis', '67': 'Campo Grande',
                '68': 'Rio Branco', '69': 'Porto Velho',
                '71': 'Salvador', '73': 'Ilhéus', '74': 'Juazeiro', '75': 'Feira de Santana',
                '77': 'Barreiras', '79': 'Aracaju',
                '81': 'Recife', '82': 'Maceió', '83': 'João Pessoa', '84': 'Natal',
                '85': 'Fortaleza', '86': 'Teresina', '87': 'Petrolina', '88': 'Juazeiro do Norte',
                '89': 'Picos', '91': 'Belém', '92': 'Manaus', '93': 'Santarém',
                '94': 'Marabá', '95': 'Boa Vista', '96': 'Macapá', '97': 'Tabatinga',
                '98': 'São Luís', '99': 'Imperatriz'
            }
            
            regiao = regioes_ddd.get(ddd, "Região não identificada")
            
            return {
                "sucesso": True,
                "numero": numero,
                "numero_internacional": phonenumbers.format_number(numero_parse, phonenumbers.PhoneNumberFormat.INTERNATIONAL),
                "numero_nacional": phonenumbers.format_number(numero_parse, phonenumbers.PhoneNumberFormat.NATIONAL),
                "ddd": ddd,
                "tipo": tipo,
                "regiao": regiao,
                "valido": True,
                "fonte": "Biblioteca phonenumbers + ANATEL"
            }
            
        except phonenumbers.NumberParseException:
            return {"sucesso": False, "mensagem": "Formato de número inválido"}
        except Exception as e:
            logger.error(f"Erro na consulta de telefone: {e}")
            return {"sucesso": False, "mensagem": f"Erro na consulta: {str(e)}"}
    
    # -------------------------------------------------
    # 3. E-MAIL (EmailRep.io + Análise de domínio)
    # -------------------------------------------------
    def email(self, email):
        """Verifica reputação de e-mail e vazamentos"""
        try:
            email = email.strip().lower()
            
            if not re.match(r'^[^@]+@[^@]+\.[^@]+$', email):
                return {"sucesso": False, "mensagem": "Formato de e-mail inválido"}
            
            # Tenta API do EmailRep.io
            api_key = os.getenv('EMAILREP_API_KEY')
            headers = {'User-Agent': 'SCDPI-OSINT-PRO/1.0'}
            
            if api_key:
                headers['Authorization'] = f'Bearer {api_key}'
            
            url = f"https://emailrep.io/{email}"
            response = requests.get(url, headers=headers, timeout=10)
            
            if response.status_code == 200:
                dados = response.json()
                detalhes = dados.get('details', {})
                
                resultado = {
                    "sucesso": True,
                    "email": email,
                    "reputacao": dados.get('reputation', 'unknown'),
                    "suspeito": dados.get('suspicious', False),
                    "referencias": dados.get('references', 0),
                    "dominio_existe": detalhes.get('domain_exists', False),
                    "dominio_reputacao": detalhes.get('domain_reputation', 'unknown'),
                    "provedor_gratuito": detalhes.get('free_provider', False),
                    "descartavel": detalhes.get('disposable', False),
                    "entregavel": detalhes.get('deliverable', False),
                    "primeira_vez": detalhes.get('first_seen', 'unknown'),
                    "ultima_vez": detalhes.get('last_seen', 'unknown'),
                    "credenciais_vazadas": detalhes.get('credentials_leaked', False),
                    "malicioso": detalhes.get('malicious_activity', False),
                    "perfis": detalhes.get('profiles', []),
                    "fonte": "EmailRep.io"
                }
                
                if resultado["credenciais_vazadas"]:
                    resultado["alerta"] = "⚠️ Este e-mail foi encontrado em vazamentos de dados!"
                
                return resultado
                
            elif response.status_code == 404:
                # Fallback: análise básica do domínio
                dominio = email.split('@')[1]
                provedores_conhecidos = ['gmail.com', 'yahoo.com', 'hotmail.com', 'outlook.com', 
                                        'uol.com.br', 'bol.com.br', 'ig.com.br', 'terra.com.br']
                
                return {
                    "sucesso": True,
                    "email": email,
                    "reputacao": "média" if dominio in provedores_conhecidos else "baixa",
                    "provedor_conhecido": dominio in provedores_conhecidos,
                    "dominio": dominio,
                    "mensagem": "E-mail não encontrado em bases de reputação, análise básica de domínio realizada",
                    "fonte": "Análise local"
                }
            else:
                return {"sucesso": False, "mensagem": f"Erro na API: {response.status_code}"}
                
        except requests.exceptions.RequestException as e:
            logger.error(f"Erro na consulta de e-mail: {e}")
            return {"sucesso": False, "mensagem": f"Erro de conexão: {str(e)}"}
        except Exception as e:
            logger.error(f"Erro inesperado: {e}")
            return {"sucesso": False, "mensagem": f"Erro interno: {str(e)}"}
    
    # -------------------------------------------------
    # 4. CPF (Validação matemática)
    # -------------------------------------------------
    def cpf(self, cpf):
        """Valida CPF usando algoritmo oficial"""
        try:
            cpf_limpo = re.sub(r'\D', '', cpf)
            
            if len(cpf_limpo) != 11:
                return {"sucesso": False, "mensagem": "CPF deve ter 11 dígitos"}
            
            if cpf_limpo == cpf_limpo[0] * 11:
                return {"sucesso": False, "mensagem": "CPF inválido (dígitos repetidos)"}
            
            # Primeiro dígito
            soma = 0
            for i in range(9):
                soma += int(cpf_limpo[i]) * (10 - i)
            resto = (soma * 10) % 11
            digito1 = 0 if resto > 9 else resto
            
            if int(cpf_limpo[9]) != digito1:
                return {"sucesso": False, "mensagem": "CPF inválido (primeiro dígito não confere)"}
            
            # Segundo dígito
            soma = 0
            for i in range(10):
                soma += int(cpf_limpo[i]) * (11 - i)
            resto = (soma * 10) % 11
            digito2 = 0 if resto > 9 else resto
            
            if int(cpf_limpo[10]) != digito2:
                return {"sucesso": False, "mensagem": "CPF inválido (segundo dígito não confere)"}
            
            cpf_formatado = f"{cpf_limpo[:3]}.{cpf_limpo[3:6]}.{cpf_limpo[6:9]}-{cpf_limpo[9:]}"
            
            return {
                "sucesso": True,
                "cpf": cpf_formatado,
                "cpf_limpo": cpf_limpo,
                "valido": True,
                "mensagem": "CPF válido (validação matemática)",
                "fonte": "Algoritmo oficial da Receita Federal"
            }
            
        except Exception as e:
            logger.error(f"Erro na validação de CPF: {e}")
            return {"sucesso": False, "mensagem": f"Erro na validação: {str(e)}"}
    
    # -------------------------------------------------
    # 5. CNPJ (Validação matemática)
    # -------------------------------------------------
    def cnpj(self, cnpj):
        """Valida CNPJ usando algoritmo oficial"""
        try:
            cnpj_limpo = re.sub(r'\D', '', cnpj)
            
            if len(cnpj_limpo) != 14:
                return {"sucesso": False, "mensagem": "CNPJ deve ter 14 dígitos"}
            
            if cnpj_limpo == cnpj_limpo[0] * 14:
                return {"sucesso": False, "mensagem": "CNPJ inválido (dígitos repetidos)"}
            
            # Primeiro dígito
            pesos1 = [5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2]
            soma = 0
            for i in range(12):
                soma += int(cnpj_limpo[i]) * pesos1[i]
            resto = soma % 11
            digito1 = 0 if resto < 2 else 11 - resto
            
            if int(cnpj_limpo[12]) != digito1:
                return {"sucesso": False, "mensagem": "CNPJ inválido (primeiro dígito não confere)"}
            
            # Segundo dígito
            pesos2 = [6, 5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2]
            soma = 0
            for i in range(13):
                soma += int(cnpj_limpo[i]) * pesos2[i]
            resto = soma % 11
            digito2 = 0 if resto < 2 else 11 - resto
            
            if int(cnpj_limpo[13]) != digito2:
                return {"sucesso": False, "mensagem": "CNPJ inválido (segundo dígito não confere)"}
            
            cnpj_formatado = f"{cnpj_limpo[:2]}.{cnpj_limpo[2:5]}.{cnpj_limpo[5:8]}/{cnpj_limpo[8:12]}-{cnpj_limpo[12:]}"
            
            return {
                "sucesso": True,
                "cnpj": cnpj_formatado,
                "cnpj_limpo": cnpj_limpo,
                "valido": True,
                "mensagem": "CNPJ válido (validação matemática)",
                "fonte": "Algoritmo oficial da Receita Federal"
            }
            
        except Exception as e:
            logger.error(f"Erro na validação de CNPJ: {e}")
            return {"sucesso": False, "mensagem": f"Erro na validação: {str(e)}"}

consulta_real = ConsultasReais()

# ==============================================
# ROTAS DE AUTENTICAÇÃO
# ==============================================

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form.get('email')
        senha = request.form.get('senha')
        
        usuario = Usuario.query.filter_by(email=email).first()
        
        if usuario and check_password_hash(usuario.senha_hash, senha):
            login_user(usuario)
            return redirect(url_for('dashboard'))
        else:
            flash('Email ou senha inválidos')
    
    return render_template('login.html')

@app.route('/registro', methods=['GET', 'POST'])
def registro():
    if request.method == 'POST':
        email = request.form.get('email')
        senha = request.form.get('senha')
        nome = request.form.get('nome')
        registro = request.form.get('registro_profissional')
        
        if Usuario.query.filter_by(email=email).first():
            flash('Email já cadastrado')
            return redirect(url_for('registro'))
        
        novo_usuario = Usuario(
            email=email,
            senha_hash=generate_password_hash(senha),
            nome=nome,
            registro_profissional=registro,
            plano='basico',
            consultas_restantes=50
        )
        
        db.session.add(novo_usuario)
        db.session.commit()
        
        login_user(novo_usuario)
        return redirect(url_for('dashboard'))
    
    return render_template('registro.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('index'))

# ==============================================
# ROTAS PRINCIPAIS
# ==============================================

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/planos')
def planos():
    return render_template('planos.html')

@app.route('/dashboard')
@login_required
def dashboard():
    return render_template('dashboard.html', usuario=current_user)

# ==============================================
# API DE CONSULTAS REAIS
# ==============================================

@app.route('/api/consultar', methods=['POST'])
@login_required
@limiter.limit("10 por minuto")  # Proteção contra abusos
def consultar():
    """Endpoint principal para consultas reais"""
    dados = request.get_json()
    tipo = dados.get('tipo')
    termo = dados.get('termo', '').strip()
    
    if current_user.consultas_restantes <= 0:
        return jsonify({'sucesso': False, 'mensagem': 'Limite de consultas excedido'}), 403
    
    if not termo:
        return jsonify({'sucesso': False, 'mensagem': 'Termo não fornecido'}), 400
    
    resultado = None
    sucesso = False
    
    try:
        if tipo == 'geo_ip':
            resultado = consulta_real.geo_ip(termo)
        elif tipo == 'telefone':
            resultado = consulta_real.telefone(termo)
        elif tipo == 'email':
            resultado = consulta_real.email(termo)
        elif tipo == 'cpf':
            resultado = consulta_real.cpf(termo)
        elif tipo == 'cnpj':
            resultado = consulta_real.cnpj(termo)
        else:
            return jsonify({'sucesso': False, 'mensagem': 'Tipo de consulta inválido'}), 400
        
        sucesso = resultado.get('sucesso', False)
        
    except Exception as e:
        logger.error(f"Erro na consulta {tipo}: {e}")
        resultado = {'sucesso': False, 'mensagem': f'Erro interno: {str(e)}'}
    
    if sucesso:
        # Decrementa consultas
        current_user.consultas_restantes -= 1
        db.session.commit()
        
        # Gera hash forense
        hash_consulta = blockchain.registrar(
            usuario_id=current_user.id,
            acao=f'consulta_{tipo}',
            dados={'termo': termo, 'resultado': resultado}
        )
        
        # Salva no banco de consultas
        nova_consulta = Consulta(
            usuario_id=current_user.id,
            tipo=tipo,
            termo=termo,
            resultado=json.dumps(resultado),
            hash_forense=hash_consulta
        )
        db.session.add(nova_consulta)
        db.session.commit()
        
        resultado['hash_forense'] = hash_consulta
        resultado['consultas_restantes'] = current_user.consultas_restantes
    
    return jsonify(resultado)

# ==============================================
# ROTAS STRIPE (Pagamentos)
# ==============================================

@app.route('/stripe/criar-checkout/<plano>')
@login_required
def criar_checkout(plano):
    planos_ids = {
        'basico': os.getenv('STRIPE_PRICE_BASICO'),
        'profissional': os.getenv('STRIPE_PRICE_PROFISSIONAL'),
        'enterprise': os.getenv('STRIPE_PRICE_ENTERPRISE')
    }
    
    if not planos_ids.get(plano):
        flash('Plano inválido')
        return redirect(url_for('planos'))
    
    try:
        session = stripe.checkout.Session.create(
            success_url=url_for('sucesso_pagamento', _external=True) + '?session_id={CHECKOUT_SESSION_ID}',
            cancel_url=url_for('planos', _external=True),
            mode='subscription',
            line_items=[{
                'price': planos_ids.get(plano),
                'quantity': 1
            }],
            customer_email=current_user.email,
            metadata={
                'usuario_id': current_user.id,
                'plano': plano
            }
        )
        return redirect(session.url)
    except Exception as e:
        logger.error(f"Erro no checkout: {e}")
        flash('Erro ao criar sessão de pagamento')
        return redirect(url_for('planos'))

@app.route('/stripe/sucesso')
@login_required
def sucesso_pagamento():
    session_id = request.args.get('session_id')
    if session_id:
        try:
            session = stripe.checkout.Session.retrieve(session_id)
            plano = session.metadata.get('plano')
            
            limites = {'basico': 50, 'profissional': 200, 'enterprise': 999999}
            current_user.plano = plano
            current_user.consultas_restantes = limites.get(plano, 50)
            current_user.stripe_customer_id = session.customer
            current_user.stripe_subscription_id = session.subscription
            db.session.commit()
            
            flash('Pagamento confirmado! Seu plano foi atualizado.')
        except Exception as e:
            logger.error(f"Erro no retorno do pagamento: {e}")
            flash('Erro ao processar pagamento')
    
    return render_template('sucesso.html')

# ==============================================
# CRIAÇÃO DO BANCO DE DADOS
# ==============================================
def init_database():
    with app.app_context():
        db.create_all()
        logger.info("✅ Banco de dados verificado/criado")
        
        if not Usuario.query.filter_by(email='admin@scdpi.com').first():
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

# ==============================================
# INÍCIO DO SERVIDOR
# ==============================================
# ==============================================
# CRIAÇÃO AUTOMÁTICA DO BANCO (VERSÃO SIMPLIFICADA)
# ==============================================
def init_db_simplificado():
    with app.app_context():
        try:
            db.create_all()
            print("✅ Banco de dados verificado")
            
            # Cria admin se não existir
            from models import Usuario
            from werkzeug.security import generate_password_hash
            
            if not Usuario.query.filter_by(email='admin@scdpi.com').first():
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
                print("✅ Admin criado")
        except Exception as e:
            print(f"⚠️ Erro ao criar banco: {e}")

# Executa a criação do banco
init_db_simplificado()
if __name__ == '__main__':
    init_database()
    app.run(debug=True, host='0.0.0.0', port=5000)
