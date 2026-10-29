# -*- coding: utf-8 -*-
"""
Testes da normalização de raça — Fidelis
========================================
Valida que a raça digitada em texto livre no app chega ao modelo com o
nome da base de referência, e que SRD e raças fora da base seguem para o
fallback da espécie.

Executar:  pytest -v
"""
from pathlib import Path

import joblib
import pytest

from racas import APELIDOS, normalizar_raca

ARTEFATO = Path(__file__).resolve().parents[1] / "modelo" / "modelo_faixa_peso.joblib"
RACAS = joblib.load(ARTEFATO)["racas_conhecidas"]


def normalizar(raca, especie="Cachorro"):
    return normalizar_raca(raca, especie, RACAS[especie])


@pytest.mark.parametrize("especie", ["Cachorro", "Gato"])
def test_todo_apelido_aponta_para_raca_da_base(especie):
    """Um apelido para raça inexistente seria um fallback silencioso."""
    assert set(APELIDOS[especie].values()) <= set(RACAS[especie])


def test_nome_oficial_e_mantido():
    assert normalizar("Yorkshire Terrier") == "Yorkshire Terrier"


def test_ignora_maiusculas_acentos_hifens_e_espacos():
    assert normalizar("  yorkshire   TERRIER ") == "Yorkshire Terrier"
    assert normalizar("Pastor-Alemão") == "German Shepherd"
    assert normalizar("shih-tzu") == "Shih Tzu"


@pytest.mark.parametrize("digitado,oficial", [
    ("Yorkshire", "Yorkshire Terrier"),
    ("Labrador", "Labrador Retriever"),
    ("Buldogue Francês", "French Bulldog"),
    ("Spitz Alemão", "Pomeranian"),
    ("Salsicha", "Dachshund"),
    ("Westie", "West Highland White Terrier"),
])
def test_apelidos_de_caes(digitado, oficial):
    assert normalizar(digitado) == oficial


@pytest.mark.parametrize("digitado,oficial", [
    ("Siamês", "Siamese"),
    ("Persa", "Persian"),
    ("Azul Russo", "Russian Blue"),
    ("Angorá", "Turkish Angora"),
])
def test_apelidos_de_gatos(digitado, oficial):
    assert normalizar(digitado, "Gato") == oficial


def test_apelido_respeita_a_especie():
    """"Siberiano" é raça de gato; para cão não pode virar Siberian."""
    assert normalizar("Siberiano", "Gato") == "Siberian"
    assert normalizar("Siberiano", "Cachorro") == "Siberiano"


@pytest.mark.parametrize("digitado", [
    None, "", "   ", "SRD", "srd", "Sem raça definida", "Vira-lata", "Mestiço"])
def test_sem_raca_definida_vira_nulo(digitado):
    assert normalizar(digitado) is None


def test_raca_fora_da_base_e_devolvida_como_digitada():
    assert normalizar(" Pinscher ") == "Pinscher"
