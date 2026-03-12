#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Módulo de Geolocalização Wi-Fi - SCDPI OSINT PRO
Utiliza a API do WiGLE.net para consultar localização por endereço MAC (BSSID)
Autor: Iskender Chanazaroff
Registro: 1411-16-DF
Versão: 1.0.1
Documentação da API: https://api.wigle.net/
"""

import os
import json
import requests
from requests.auth import HTTPBasicAuth
from datetime import datetime
from typing import Dict, Optional, Tuple, Any

class WigleGeolocator:
    """
    Cliente para a API de geolocalização do WiGLE.net.
    Requer credenciais de API (API Name e API Token) obtidas em https://wigle.net/account.
    """

    def __init__(self, api_name: str = None, api_token: str = None):
        """
        Inicializa o cliente com as credenciais da API.
        Se não fornecidas, tenta ler das variáveis de ambiente WIGLE_API_NAME e WIGLE_API_TOKEN.
        """
        self.api_name = api_name or os.getenv('WIGLE_API_NAME')
        self.api_token = api_token or os.getenv('WIGLE_API_TOKEN')
        self.base_url = "https://api.wigle.net/api/v2"
        self.session = requests.Session()

        if not self.api_name or not self.api_token:
            print("⚠️  AVISO: Credenciais WiGLE não configuradas. As consultas falharão.")
            print("   Obtenha suas credenciais em: https://wigle.net/account")
            print("   Defina as variáveis de ambiente WIGLE_API_NAME e WIGLE_API_TOKEN.")
        else:
            # Configura a autenticação básica para todas as requisições da sessão
            self.session.auth = HTTPBasicAuth(self.api_name, self.api_token)

    def _fazer_requisicao(self, endpoint: str, params: Dict = None) -> Dict[str, Any]:
        """
        Faz uma requisição autenticada à API do WiGLE.
        """
        if not self.session.auth:
            return {"success": False, "message": "Credenciais não configuradas", "resultado": None}

        url = f"{self.base_url}/{endpoint}"
        headers = {"Accept": "application/json"}

        try:
            # A autenticação é feita automaticamente pela sessão
            response = self.session.get(url, headers=headers, params=params, timeout=15)
            response.raise_for_status()
            return {"success": True, "data": response.json(), "status_code": response.status_code}
        except requests.exceptions.HTTPError as e:
            error_detail = self._parse_error_response(e.response)
            return {"success": False, "message": f"Erro HTTP {e.response.status_code}: {error_detail}", "status_code": e.response.status_code}
        except requests.exceptions.RequestException as e:
            return {"success": False, "message": f"Erro de conexão: {e}", "status_code": None}

    def _parse_error_response(self, response) -> str:
        """Tenta extrair a mensagem de erro do corpo da resposta."""
        try:
            error_data = response.json()
            return error_data.get('message', response.reason)
        except:
            return response.reason

    def buscar_por_mac(self, mac_address: str) -> Dict[str, Any]:
        """
        Busca a localização de um ponto de acesso pelo seu endereço MAC (BSSID).
        Exemplo de MAC: "00:1C:0E:42:79:43" ou "00:1C:0E:42:79:43"
        """
        mac_formatado = self._formatar_mac(mac_address)
        if not mac_formatado:
            return {"sucesso": False, "mensagem": f"Formato de MAC inválido: '{mac_address}'. Use o formato XX:XX:XX:XX:XX:XX", "resultado": None}

        print(f"🔍 [WiGLE] Consultando MAC: {mac_formatado}")
        endpoint = "network/detail"
        params = {"netid": mac_formatado}

        resposta = self._fazer_requisicao(endpoint, params)

        if not resposta["success"]:
            return {"sucesso": False, "mensagem": resposta.get("message", "Falha na consulta"), "resultado": None}

        dados = resposta.get("data", {})
        if not dados.get("success", False):
            return {"sucesso": False, "mensagem": dados.get("message", "A consulta não foi bem-sucedida"), "resultado": None}

        # Processa os resultados
        resultados = dados.get("results", [])
        if not resultados:
            return {"sucesso": True, "mensagem": "Endereço MAC não encontrado no banco de dados.", "resultado": []}

        pontos_encontrados = []
        for net in resultados:
            pontos_encontrados.append({
                "ssid": net.get("ssid"),
                "mac": net.get("netid"),
                "latitude": net.get("trilat"),
                "longitude": net.get("trilong"),
                "qualidade_sinal": net.get("qos"),
                "primeira_vez": net.get("firsttime"),
                "ultima_vez": net.get("lasttime"),
                "pais": net.get("country"),
                "regiao": net.get("region"),
                "cidade": net.get("city"),
                "endereco_aproximado": f"{net.get('road')}, {net.get('city')} - {net.get('region')}" if net.get('road') else None,
                "fonte": "WiGLE.net"
            })

        return {
            "sucesso": True,
            "mensagem": f"Encontrados {len(pontos_encontrados)} registro(s).",
            "resultado": pontos_encontrados
        }

    def buscar_por_ssid(self, ssid: str, resultados_por_pagina: int = 100) -> Dict[str, Any]:
        """
        Busca pontos de acesso pelo nome da rede (SSID).
        Pode retornar múltiplas localizações para o mesmo nome.
        """
        print(f"🔍 [WiGLE] Consultando SSID: '{ssid}'")
        endpoint = "network/search"
        params = {"ssid": ssid, "freenet": "false", "paynet": "false", "resultsPerPage": resultados_por_pagina}

        resposta = self._fazer_requisicao(endpoint, params)

        if not resposta["success"]:
            return {"sucesso": False, "mensagem": resposta.get("message", "Falha na consulta"), "resultado": None}

        dados = resposta.get("data", {})
        if not dados.get("success", False):
            return {"sucesso": False, "mensagem": dados.get("message", "A consulta não foi bem-sucedida"), "resultado": None}

        resultados = dados.get("results", [])
        if not resultados:
            return {"sucesso": True, "mensagem": f"Nenhum ponto de acesso encontrado para o SSID '{ssid}'.", "resultado": []}

        pontos_encontrados = []
        for net in resultados:
            pontos_encontrados.append({
                "ssid": net.get("ssid"),
                "mac": net.get("netid"),
                "latitude": net.get("trilat"),
                "longitude": net.get("trilong"),
                "pais": net.get("country"),
                "regiao": net.get("region"),
                "cidade": net.get("city"),
                "endereco_aproximado": f"{net.get('road')}, {net.get('city')} - {net.get('region')}" if net.get('road') else None,
                "fonte": "WiGLE.net"
            })

        return {
            "sucesso": True,
            "mensagem": f"Encontrados {len(pontos_encontrados)} ponto(s) de acesso para o SSID '{ssid}'.",
            "resultado": pontos_encontrados
        }

    def _formatar_mac(self, mac: str) -> Optional[str]:
        """Valida e formata o MAC para o padrão da API (XX:XX:XX:XX:XX:XX)."""
        import re
        mac = mac.strip().upper()
        # Remove separadores comuns e valida caracteres hexadecimais
        mac_clean = re.sub(r'[^A-F0-9]', '', mac)
        if len(mac_clean) != 12:
            return None
        # Formata no padrão XX:XX:XX:XX:XX:XX
        mac_formatado = ":".join(mac_clean[i:i+2] for i in range(0, 12, 2))
        return mac_formatado

    def testar_credenciais(self) -> bool:
        """
        Testa se as credenciais fornecidas são válidas consultando o perfil do usuário.
        """
        print("🔐 [WiGLE] Testando credenciais...")
        endpoint = "profile/user"
        resposta = self._fazer_requisicao(endpoint)
        if resposta["success"]:
            dados = resposta.get("data", {})
            print(f"✅ Credenciais OK. Usuário: {dados.get('username', 'Desconhecido')}")
            return True
        else:
            print(f"❌ Credenciais inválidas: {resposta.get('message')}")
            return False

# ==============================================
# EXEMPLO DE USO (se executado diretamente)
# ==============================================
if __name__ == "__main__":
    print("="*60)
    print("🔍 TESTE DO MÓDULO DE GEOLOCALIZAÇÃO WiGLE")
    print("="*60)
    print("Para usar, defina as variáveis de ambiente WIGLE_API_NAME e WIGLE_API_TOKEN.")
    print("Ou edite este script e insira suas credenciais abaixo.")
    print("Credenciais podem ser obtidas em: https://wigle.net/account")
    print("-"*60)

    # COLE SUAS CREDENCIAIS AQUI PARA TESTE (ou use variáveis de ambiente)
    API_NAME = os.getenv('WIGLE_API_NAME', 'COLE_SEU_API_NAME_AQUI')
    API_TOKEN = os.getenv('WIGLE_API_TOKEN', 'COLE_SEU_API_TOKEN_AQUI')

    wigle = WigleGeolocator(api_name=API_NAME, api_token=API_TOKEN)

    if wigle.session.auth:
        wigle.testar_credenciais()
        print("\n" + "-"*60)

        # Teste 1: Buscar por um MAC válido (exemplo público)
        mac_teste = "00:1C:0E:42:79:43"  # Este é um exemplo de MAC usado em documentações
        print(f"\n📍 Teste 1: Buscar MAC {mac_teste}")
        resultado = wigle.buscar_por_mac(mac_teste)
        print(f"   Mensagem: {resultado.get('mensagem')}")
        if resultado['sucesso'] and resultado['resultado']:
            for ponto in resultado['resultado']:
                print(f"   SSID: {ponto['ssid']}")
                print(f"   Lat/Lng: {ponto['latitude']}, {ponto['longitude']}")
                print(f"   Endereço: {ponto.get('endereco_aproximado')}")

        # Teste 2: Buscar por um SSID comum
        print("\n" + "-"*60)
        ssid_teste = "Marriott"  # Rede comum em hotéis
        print(f"\n📍 Teste 2: Buscar SSID '{ssid_teste}'")
        resultado = wigle.buscar_por_ssid(ssid_teste, resultados_por_pagina=5)
        print(f"   Mensagem: {resultado.get('mensagem')}")
        if resultado['sucesso'] and resultado['resultado']:
            for i, ponto in enumerate(resultado['resultado'][:3]):  # Mostra os primeiros 3
                print(f"   {i+1}. SSID: {ponto['ssid']} | MAC: {ponto['mac']}")
                print(f"      Lat/Lng: {ponto['latitude']}, {ponto['longitude']}")
    else:
        print("\n❌ Credenciais não configuradas.")
        print("   Por favor, defina as variáveis de ambiente ou edite o script.")
