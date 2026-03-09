import stripe
import os
from flask import Blueprint, request, jsonify, redirect, url_for
from flask_login import current_user, login_required
from models import db, Usuario
from blockchain import BlockchainForense

stripe_bp = Blueprint('stripe', __name__)
blockchain = BlockchainForense()

# SEUS PRICE IDs (copiados da Stripe)
PLANOS = {
    'basico': 'price_1T80amRTkipPzm9yaCnxMa6I',        # R$ 49,00
    'profissional': 'price_1T80cuRTkipPzm9yn05hIpwU',  # R$ 99,90
    'enterprise': 'price_1T80etRTkipPzm9yjoaR3bw1'     # R$ 299,90
}

LIMITES_CONSULTA = {
    'basico': 50,
    'profissional': 200,
    'enterprise': 999999  # "ilimitado"
}

@stripe_bp.route('/criar-checkout/<plano>')
@login_required
def criar_checkout(plano):
    try:
        # Cria sessão de checkout no Stripe
        sessao = stripe.checkout.Session.create(
            success_url=url_for('stripe.sucesso', _external=True) + '?session_id={CHECKOUT_SESSION_ID}',
            cancel_url=url_for('planos', _external=True),
            mode='subscription',
            line_items=[{
                'price': PLANOS[plano],
                'quantity': 1
            }],
            customer_email=current_user.email,
            metadata={
                'usuario_id': current_user.id,
                'plano': plano
            }
        )
        
        return redirect(sessao.url)
    
    except Exception as e:
        return jsonify({'erro': str(e)}), 400

@stripe_bp.route('/webhook', methods=['POST'])
def webhook():
    """Recebe notificações do Stripe quando alguém paga"""
    payload = request.get_data(as_text=True)
    sig_header = request.headers.get('Stripe-Signature')
    
    try:
        evento = stripe.Webhook.construct_event(
            payload, sig_header, os.getenv('STRIPE_WEBHOOK_SECRET')
        )
    except ValueError:
        return 'Payload inválido', 400
    except stripe.error.SignatureVerificationError:
        return 'Assinatura inválida', 400
    
    # Processa pagamento confirmado
    if evento['type'] == 'checkout.session.completed':
        sessao = evento['data']['object']
        usuario_id = sessao['metadata']['usuario_id']
        plano = sessao['metadata']['plano']
        
        # Busca usuário e atualiza plano
        usuario = Usuario.query.get(usuario_id)
        if usuario:
            usuario.plano = plano
            usuario.consultas_restantes = LIMITES_CONSULTA[plano]
            usuario.stripe_customer_id = sessao.get('customer')
            usuario.stripe_subscription_id = sessao.get('subscription')
            db.session.commit()
            
            # Registra na blockchain forense
            blockchain.registrar(
                usuario_id=usuario.id,
                acao='assinatura_ativada',
                dados={'plano': plano, 'session_id': sessao['id']}
            )
    
    return 'OK', 200

@stripe_bp.route('/sucesso')
@login_required
def sucesso():
    return render_template('sucesso.html')
