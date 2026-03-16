from flask import Flask
from flask_sqlalchemy import SQLAlchemy
import os

# Cria uma instância do Flask APENAS para o banco
db_app = Flask(__name__)
db_app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('DATABASE_URL', 'sqlite:///scdpi.db')
db_app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Inicializa o SQLAlchemy com esta instância
db = SQLAlchemy()
db.init_app(db_app)
