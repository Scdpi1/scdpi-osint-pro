from app import app
from models import db, Usuario
from werkzeug.security import generate_password_hash

with app.app_context():
    # Cria tabelas
    db.create_all()
    print("✅ Tabelas criadas!")
    
    # Verifica se já existe usuário admin
    if not Usuario.query.filter_by(email='teste@scdpi.com').first():
        admin = Usuario(
            email='teste@scdpi.com',
            senha_hash=generate_password_hash('123456'),
            nome='Admin',
            registro_profissional='ADMIN001',
            plano='enterprise',
            consultas_restantes=999999
        )
        db.session.add(admin)
        db.session.commit()
        print("✅ Usuário admin criado!")
    else:
        print("ℹ️ Usuário já existe")
