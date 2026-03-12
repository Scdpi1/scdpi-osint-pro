from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from datetime import datetime

db = SQLAlchemy()

class Usuario(UserMixin, db.Model):
    __tablename__ = 'usuarios'
    
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), unique=True, nullable=False)
    senha_hash = db.Column(db.String(200), nullable=False)
    nome = db.Column(db.String(100))
    registro_profissional = db.Column(db.String(50))  # Nº do detetive
    plano = db.Column(db.String(20), default='basico')  # basico, profissional, enterprise
    status = db.Column(db.String(20), default='ativo')
    consultas_restantes = db.Column(db.Integer, default=50)
    stripe_customer_id = db.Column(db.String(100))
    stripe_subscription_id = db.Column(db.String(100))
    data_cadastro = db.Column(db.DateTime, default=datetime.utcnow)
    
    def __repr__(self):
        return f'<Usuario {self.email}>'

class Consulta(db.Model):
    __tablename__ = 'consultas'
    
    id = db.Column(db.Integer, primary_key=True)
    usuario_id = db.Column(db.Integer, db.ForeignKey('usuarios.id'))
    tipo = db.Column(db.String(50))  # telefone, cpf, cnpj, email
    termo = db.Column(db.String(200))  # o que foi consultado
    resultado = db.Column(db.Text)  # resultado da consulta
    hash_forense = db.Column(db.String(64))  # hash da blockchain
    data_consulta = db.Column(db.DateTime, default=datetime.utcnow)
    
    usuario = db.relationship('Usuario', backref=db.backref('consultas', lazy=True))
