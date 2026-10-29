# -*- coding: utf-8 -*-
"""Configuração comum dos testes do serviço de IA."""
import pytest


@pytest.fixture(autouse=True)
def sem_chave_de_api(monkeypatch):
    """Os testes rodam com o endpoint aberto, mesmo que a máquina tenha a
    variável definida; os testes de autenticação a configuram por conta."""
    monkeypatch.delenv("FIDELIS_IA_API_KEY", raising=False)
