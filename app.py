from flask import Flask, render_template, jsonify, request
from flask_login import login_required, current_user
import os
from dotenv import load_dotenv
import stripe

# Carrega variáveis de ambiente
load_dotenv()

# Configura Stripe
stripe.api_key = os.getenv('STRIPE_SECRET_KEY')

# Inicializa Flask
app = Flask(__name__, 
            template_folder='templates',
            static_folder='.')

app.config['SECRET_KEY'] = os.getenv('SECRET_KEY')
app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('DATABASE_URL')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Inicializa banco de dados
from models import db, Usuario, Consulta
db.init_app(app)

# Registra blueprints
from auth import auth_bp
from stripe_integration import stripe_bp

app.register_blueprint(auth_bp)
app.register_blueprint(stripe_bp, url_prefix='/stripe')

# Rotas públicas
@app.route('/')
def index():
    return render_template('index.html')

@app.route('/planos')
def planos():
    return render_template('planos.html')

# Rotas protegidas (só para assinantes)
@app.route('/dashboard')
@login_required
def dashboard():
    return render_template('dashboard.html', usuario=current_user)

@app.route('/api/consultar', methods=['POST'])
@login_required
def consultar():
    """Endpoint para realizar consultas OSINT"""
    dados = request.get_json()
    tipo = dados.get('tipo')
    termo = dados.get('termo')
    
    # Verifica se tem consultas restantes
    if current_user.consultas_restantes <= 0:
        return jsonify({'erro': 'Limite de consultas excedido'}), 403
    
    # Aqui você integrará os módulos OSINT reais
    # (telefone, cpf, cnpj, etc.)
    resultado = {'mensagem': f'Consulta simulada de {tipo}: {termo}'}
    
    # Decrementa consultas
    current_user.consultas_restantes -= 1
    db.session.commit()
    
    return jsonify(resultado)

# Cria banco de dados
with app.app_context():
    db.create_all()

if __name__ == '__main__':
    app.run(debug=True)
