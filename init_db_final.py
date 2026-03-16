#!/usr/bin/env python3
import sys
import os
from werkzeug.security import generate_password_hash

# Configuração independente
from db_config import db_app, db

# Define os modelos aqui mesmo (para não depender do app principal)
class Usuario(db.Model):
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
    data_cadastro = db.Column(db.DateTime, default=db.func.current_timestamp())

def init_db():
    with db_app.app_context():
        print("🔄 Criando tabelas...")
        db.create_all()
        print("✅ Tabelas criadas!")
        
        # Verifica se admin já existe
        admin = Usuario.query.filter_by(email='admin@scdpi.com').first()
        if not admin:
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
            print("✅ Usuário admin criado!")
        else:
            print("ℹ️ Usuário admin já existe")
        
        print("✅ Banco de dados inicializado com sucesso!")
        return True

if __name__ == "__main__":
    init_db()
