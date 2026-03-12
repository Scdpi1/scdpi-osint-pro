#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Módulo de Geolocalização por IP - SCDPI OSINT PRO
Alternativa imediata ao WiGLE usando ip-api.com (gratuito, sem chave)
Autor: Iskender Chanazaroff
Registro: 1411-16-DF
Versão: 1.0.0
"""

import requests
import json
from typing import Dict, Any, Optional
import time

class IPGeolocator:
    """
    Cliente para geolocalização de endereços IP usando ip-api.com.
    Gratuito para uso não-comercial, 45 requisições por minuto [citation:2][citation:4].
    """
    
    def __init__(self):
        self.base_url = "http://ip-api.com/json"
        self.session = requests.Session()
        self.rate_limit_remaining = 45
        self.rate_limit_reset = 60
        
    def localizar_ip(self, ip: str, campos: list = None, idioma: str = "pt-BR") -> Dict[str, Any]:
        """
        Localiza um endereço IP e retorna informações geográficas.
        
        Args:
            ip: Endereço IP (IPv4 ou IPv6) ou domínio
            campos: Lista de campos desejados (None = todos)
            idioma: Idioma para localização (padrão: pt-BR)
        
        Returns:
            Dicionário com informações de localização
        """
        print(f"🔍 [IP-Geo] Consultando IP: {ip}")
        
        # Constrói a URL com parâmetros
        params = {}
        if campos:
            params['fields'] = ','.join(campos)
        if idioma:
            params['lang'] = idioma
            
        try:
            response = self.session.get(
                f"{self.base_url}/{ip}",
                params=params,
                timeout=10
            )
            
            # Verifica rate limit pelos headers [citation:3]
            if 'X-Rl' in response.headers:
                self.rate_limit_remaining = int(response.headers['X-Rl'])
                self.rate_limit_reset = int(response.headers.get('X-Ttl', 60))
                print(f"📊 Rate limit: {self.rate_limit_remaining} requisições restantes")
            
            if response.status_code == 200:
                dados = response.json()
                
                if dados.get('status') == 'success':
                    return {
                        "sucesso": True,
                        "ip": dados.get('query'),
                        "pais": dados.get('country'),
                        "codigo_pais": dados.get('countryCode'),
                        "regiao": dados.get('regionName'),
                        "codigo_regiao": dados.get('region'),
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
                        "mensagem": dados.get('message', 'Erro desconhecido'),
                        "ip": ip
                    }
            else:
                return {
                    "sucesso": False,
                    "mensagem": f"Erro HTTP {response.status_code}",
                    "ip": ip
                }
                
        except requests.exceptions.RequestException as e:
            return {
                "sucesso": False,
                "mensagem": f"Erro de conexão: {str(e)}",
                "ip": ip
            }
    
    def localizar_varios_ips(self, ips: list, campos: list = None) -> list:
        """
        Localiza múltiplos IPs em uma única requisição (batch) [citation:3].
        """
        print(f"🔍 [IP-Geo] Consultando {len(ips)} IPs em lote")
        
        # Endpoint batch: http://ip-api.com/batch
        batch_url = "http://ip-api.com/batch"
        
        # Prepara os dados para requisição POST [citation:2]
        payload = ips
        
        try:
            response = self.session.post(
                batch_url,
                json=payload,
                timeout=30
            )
            
            if response.status_code == 200:
                resultados = response.json()
                
                resultados_processados = []
                for idx, dados in enumerate(resultados):
                    if dados.get('status') == 'success':
                        resultados_processados.append({
                            "sucesso": True,
                            "ip": dados.get('query', ips[idx]),
                            "pais": dados.get('country'),
                            "cidade": dados.get('city'),
                            "latitude": dados.get('lat'),
                            "longitude": dados.get('lon'),
                            "isp": dados.get('isp')
                        })
                    else:
                        resultados_processados.append({
                            "sucesso": False,
                            "ip": ips[idx],
                            "mensagem": dados.get('message', 'Erro')
                        })
                
                return resultados_processados
            else:
                return [{"sucesso": False, "ip": ip, "mensagem": f"Erro HTTP {response.status_code}"} for ip in ips]
                
        except requests.exceptions.RequestException as e:
            return [{"sucesso": False, "ip": ip, "mensagem": f"Erro de conexão: {str(e)}"} for ip in ips]
    
    def meu_ip(self) -> str:
        """
        Retorna o IP público da máquina que está fazendo a requisição.
        """
        try:
            response = self.session.get("http://ip-api.com/json", timeout=10)
            if response.status_code == 200:
                dados = response.json()
                return dados.get('query', 'Não disponível')
            return "Não disponível"
        except:
            return "Não disponível"


# ==============================================
# EXEMPLO DE USO (se executado diretamente)
# ==============================================
if __name__ == "__main__":
    print("="*60)
    print("🔍 TESTE DO MÓDULO DE GEOLOCALIZAÇÃO POR IP")
    print("="*60)
    
    geo = IPGeolocator()
    
    # Teste 1: Meu próprio IP
    print(f"\n📍 Meu IP: {geo.meu_ip()}")
    
    # Teste 2: IP específico (Google DNS)
    print("\n📍 Teste 1: Google DNS (8.8.8.8)")
    resultado = geo.localizar_ip("8.8.8.8")
    if resultado['sucesso']:
        print(f"   País: {resultado['pais']} ({resultado['codigo_pais']})")
        print(f"   Cidade: {resultado['cidade']}, {resultado['regiao']}")
        print(f"   Coordenadas: {resultado['latitude']}, {resultado['longitude']}")
        print(f"   ISP: {resultado['isp']}")
    else:
        print(f"   ❌ Erro: {resultado.get('mensagem')}")
    
    # Teste 3: Domínio
    print("\n📍 Teste 2: Domínio (google.com)")
    resultado = geo.localizar_ip("google.com")
    if resultado['sucesso']:
        print(f"   IP: {resultado['ip']}")
        print(f"   País: {resultado['pais']}")
        print(f"   Cidade: {resultado['cidade']}")
    
    # Teste 4: Vários IPs em lote [citation:3]
    print("\n📍 Teste 3: Consulta em lote")
    ips_teste = ["8.8.8.8", "1.1.1.1", "9.9.9.9"]
    resultados = geo.localizar_varios_ips(ips_teste)
    for r in resultados:
        if r['sucesso']:
            print(f"   ✅ {r['ip']}: {r['cidade']}, {r['pais']}")
        else:
            print(f"   ❌ {r['ip']}: {r.get('mensagem')}")
    
    print("\n" + "="*60)
    print("ℹ️  Este serviço é gratuito, 45 requisições/minuto [citation:4]")
    print("   Uso não-comercial permitido")
    print("="*60)
