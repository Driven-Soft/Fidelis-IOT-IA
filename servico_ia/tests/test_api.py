# -*- coding: utf-8 -*-
"""
Testes da API do serviço de IA — Fidelis
========================================
Valida o contrato do endpoint POST /analise (o que o backend .NET consome),
a seleção da faixa por perfil, o fallback para raça desconhecida e a
validação de entrada.

Executar:  pytest -v
"""
import pytest
from fastapi.testclient import TestClient

from main import app

client = TestClient(app)

AURORA = {
    "pet_id": 1,
    "especie": "Cachorro",
    "raca": "Yorkshire Terrier",
    "sexo": "F",
    "idade_anos": 4,
    "peso_kg": 3.2,
}


def analisar(**overrides):
    payload = {**AURORA, **overrides}
    return client.post("/analise", json=payload)


# --------------------------------------------------------------------------
# Health check
# --------------------------------------------------------------------------

def test_health_responde_ok_com_metricas_do_modelo():
    r = client.get("/health")
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "ok"
    assert "mae_p50_kg" in body["metricas_modelo"]


# --------------------------------------------------------------------------
# Contrato da resposta
# --------------------------------------------------------------------------

class TestContrato:
    def test_resposta_tem_a_estrutura_esperada(self):
        body = analisar().json()
        assert set(body) == {"pet_id", "perfil", "avaliacao"}
        assert set(body["avaliacao"]) == {
            "risco", "tipo_recomendacao", "faixa_esperada_kg",
            "peso_informado_kg", "desvio_alem_da_faixa",
            "justificativa", "acoes",
        }

    def test_pet_id_e_devolvido_para_correlacao(self):
        assert analisar(pet_id=4217).json()["pet_id"] == 4217

    def test_risco_e_um_dos_tres_niveis(self):
        assert analisar().json()["avaliacao"]["risco"] in {
            "VERDE", "AMARELO", "VERMELHO"}

    def test_acoes_trazem_a_tabela_de_destino(self):
        acoes = analisar().json()["avaliacao"]["acoes"]
        assert all(a["registro"] in {"RECOMENDACAO", "LEMBRETE"} for a in acoes)


# --------------------------------------------------------------------------
# Personalização: a faixa muda conforme o perfil
# --------------------------------------------------------------------------

class TestPersonalizacao:
    def test_racas_diferentes_recebem_faixas_diferentes(self):
        yorkshire = analisar().json()["avaliacao"]["faixa_esperada_kg"]
        labrador = analisar(raca="Labrador Retriever", sexo="M",
                             peso_kg=32.0).json()["avaliacao"]["faixa_esperada_kg"]
        assert yorkshire["max"] < labrador["min"]

    def test_mesmo_peso_tem_veredito_oposto_em_perfis_diferentes(self):
        """3,2 kg é excesso para Yorkshire e seria déficit para Labrador."""
        y = analisar().json()["avaliacao"]
        l = analisar(raca="Labrador Retriever", sexo="M").json()["avaliacao"]
        assert "acima" in y["justificativa"]
        assert "abaixo" in l["justificativa"]

    def test_gato_e_avaliado_na_escala_felina(self):
        faixa = analisar(especie="Gato", raca="Siamese", peso_kg=4.0
                          ).json()["avaliacao"]["faixa_esperada_kg"]
        assert faixa["max"] < 10


# --------------------------------------------------------------------------
# Raça desconhecida / SRD
# --------------------------------------------------------------------------

class TestFallback:
    def test_raca_nula_marca_fora_da_base(self):
        body = analisar(raca=None, especie="Gato", peso_kg=4.0).json()
        assert body["perfil"]["raca_na_base_de_referencia"] is False

    def test_raca_inexistente_usa_fallback_sem_quebrar(self):
        body = analisar(raca="Raça Que Não Existe", peso_kg=4.0).json()
        assert body["perfil"]["raca_na_base_de_referencia"] is False
        assert body["avaliacao"]["risco"] in {"VERDE", "AMARELO"}

    def test_raca_conhecida_marca_dentro_da_base(self):
        assert analisar().json()["perfil"]["raca_na_base_de_referencia"] is True

    def test_raca_fora_da_base_aparece_na_justificativa(self):
        """Uma raça real fora da base não deve ser descrita como SRD."""
        just = analisar(raca="Pinscher", sexo="M", peso_kg=4.0
                         ).json()["avaliacao"]["justificativa"]
        assert "Pinscher macho" in just
        assert "faixa geral da espécie" in just


# --------------------------------------------------------------------------
# Raça em texto livre (como vem do cadastro do app)
# --------------------------------------------------------------------------

class TestNormalizacaoDaRaca:
    def test_apelido_recebe_a_mesma_faixa_do_nome_oficial(self):
        oficial = analisar().json()
        apelido = analisar(raca="yorkshire").json()
        assert apelido["avaliacao"] == oficial["avaliacao"]
        assert apelido["perfil"]["raca"] == "Yorkshire Terrier"
        assert apelido["perfil"]["raca_na_base_de_referencia"] is True

    def test_srd_por_extenso_usa_fallback(self):
        body = analisar(raca="Vira-lata", peso_kg=10.0).json()
        assert body["perfil"]["raca"] is None
        assert body["perfil"]["raca_na_base_de_referencia"] is False


# --------------------------------------------------------------------------
# Chave de API (comunicação interna com a API .NET)
# --------------------------------------------------------------------------

class TestChaveDeApi:
    CHAVE = "chave-de-teste"

    def test_sem_chave_configurada_o_endpoint_fica_aberto(self, monkeypatch):
        monkeypatch.delenv("FIDELIS_IA_API_KEY", raising=False)
        assert analisar().status_code == 200

    def test_chave_configurada_rejeita_requisicao_sem_header(self, monkeypatch):
        monkeypatch.setenv("FIDELIS_IA_API_KEY", self.CHAVE)
        assert analisar().status_code == 401

    def test_chave_configurada_rejeita_header_errado(self, monkeypatch):
        monkeypatch.setenv("FIDELIS_IA_API_KEY", self.CHAVE)
        r = client.post("/analise", json=AURORA, headers={"X-API-Key": "outra"})
        assert r.status_code == 401

    def test_chave_correta_e_aceita(self, monkeypatch):
        monkeypatch.setenv("FIDELIS_IA_API_KEY", self.CHAVE)
        r = client.post("/analise", json=AURORA, headers={"X-API-Key": self.CHAVE})
        assert r.status_code == 200

    def test_health_dispensa_chave(self, monkeypatch):
        monkeypatch.setenv("FIDELIS_IA_API_KEY", self.CHAVE)
        assert client.get("/health").status_code == 200


# --------------------------------------------------------------------------
# Validação de entrada
# --------------------------------------------------------------------------

class TestValidacao:
    @pytest.mark.parametrize("campo", [
        "especie", "sexo", "idade_anos", "peso_kg", "pet_id"])
    def test_campo_obrigatorio_ausente_e_rejeitado(self, campo):
        payload = {k: v for k, v in AURORA.items() if k != campo}
        assert client.post("/analise", json=payload).status_code == 422

    def test_peso_nao_positivo_e_rejeitado(self):
        assert analisar(peso_kg=0).status_code == 422
        assert analisar(peso_kg=-5).status_code == 422

    def test_idade_negativa_e_rejeitada(self):
        assert analisar(idade_anos=-1).status_code == 422

    def test_especie_invalida_e_rejeitada(self):
        assert analisar(especie="Papagaio").status_code == 422

    def test_sexo_invalido_e_rejeitado(self):
        assert analisar(sexo="X").status_code == 422
