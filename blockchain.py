import hashlib
import json
import os
from datetime import datetime

class BlockchainForense:
    """
    Sistema de log imutável - garante que nenhuma consulta seja alterada
    """
    
    def __init__(self, arquivo_log='data/blockchain.json'):
        self.arquivo_log = arquivo_log
        self.cadeia = self._carregar()
        self.chave_mestra = os.getenv('MASTER_KEY', 'SCDPI_1411_16_DF')
    
    def _carregar(self):
        if os.path.exists(self.arquivo_log):
            with open(self.arquivo_log, 'r') as f:
                return json.load(f)
        return []
    
    def _salvar(self):
        os.makedirs(os.path.dirname(self.arquivo_log), exist_ok=True)
        with open(self.arquivo_log, 'w') as f:
            json.dump(self.cadeia, f, indent=2)
    
    def registrar(self, usuario_id, acao, dados):
        """
        Registra uma ação na blockchain forense
        Retorna hash único da transação
        """
        bloco = {
            'index': len(self.cadeia),
            'timestamp': datetime.now().isoformat(),
            'usuario_id': usuario_id,
            'acao': acao,
            'dados': dados,
            'hash_anterior': self.cadeia[-1]['hash'] if self.cadeia else '0' * 64,
            'hash': None
        }
        
        # Calcula hash do bloco (inclui sua chave mestra)
        conteudo = f"{bloco['index']}{bloco['timestamp']}{usuario_id}{acao}{json.dumps(dados)}{bloco['hash_anterior']}{self.chave_mestra}"
        bloco['hash'] = hashlib.sha256(conteudo.encode()).hexdigest()
        
        self.cadeia.append(bloco)
        self._salvar()
        
        return bloco['hash']
    
    def verificar(self, hash_consulta):
        """Verifica se um hash específico ainda é válido"""
        for bloco in self.cadeia:
            if bloco['hash'] == hash_consulta:
                conteudo = f"{bloco['index']}{bloco['timestamp']}{bloco['usuario_id']}{bloco['acao']}{json.dumps(bloco['dados'])}{bloco['hash_anterior']}{self.chave_mestra}"
                return hashlib.sha256(conteudo.encode()).hexdigest() == bloco['hash']
        return False
