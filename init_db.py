from app import app
from models import db, Usuario
from werkzeug.security import generate_password_hash

with app.app_context():
    db.create_all()
    print("✅ Banco criado!")
    
    if not Usuario.query.filter_by(email='admin@scdpi.com').first():
        admin = Usuario(
            email='admin@scdpi.com',
            senha_hash=generate_password_hash('admin123'),
            nome='Admin',
            registro_profissional='ADMIN001',
            plano='enterprise',
            consultas_restantes=999999
        )
        db.session.add(admin)
        db.session.commit()
        print("✅ Admin criado!")
