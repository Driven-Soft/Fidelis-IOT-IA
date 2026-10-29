# -*- coding: utf-8 -*-
"""
Testes do motor de regras — Fidelis
===================================
Valida a classificação de risco, os limiares, os casos especiais
(filhote e SRD) e a formatação em português das recomendações.

Executar:  pytest -v
"""
import pytest

from regras import (
    LIMIAR_ALERTA,
    LIMIAR_ATENCAO,
    PRAZO_CONSULTA_DIAS,
    PRAZO_PESAGEM_DIAS,
    _descrever_perfil,
    _desvio_alem_da_faixa,
    _kg,
    avaliar,
    classificar,
)

# Perfil adulto padrão usado na maioria dos testes (Yorkshire fêmea, 4 anos)
PERFIL_ADULTO = {
    "especie": "Cachorro",
    "raca": "Yorkshire Terrier",
    "sexo": "F",
    "idade_anos": 4.0,
    "usou_fallback": False,
}
FAIXA = {"p10": 2.1, "p90": 2.7}


def avaliar_peso(peso, **overrides):
    """Atalho: avalia um peso no perfil adulto padrão."""
    kwargs = {**PERFIL_ADULTO, **FAIXA, **overrides}
    return avaliar(peso_kg=peso, **kwargs)


# --------------------------------------------------------------------------
# Cálculo do desvio
# --------------------------------------------------------------------------

class TestDesvio:
    def test_peso_dentro_da_faixa_nao_tem_desvio(self):
        assert _desvio_alem_da_faixa(2.4, 2.1, 2.7) == 0.0

    def test_peso_exatamente_nas_bordas_nao_tem_desvio(self):
        assert _desvio_alem_da_faixa(2.1, 2.1, 2.7) == 0.0
        assert _desvio_alem_da_faixa(2.7, 2.1, 2.7) == 0.0

    def test_desvio_acima_usa_a_borda_superior(self):
        # (3.24 - 2.7) / 2.7 = 0.20
        assert _desvio_alem_da_faixa(3.24, 2.1, 2.7) == pytest.approx(0.20)

    def test_desvio_abaixo_usa_a_borda_inferior(self):
        # (2.1 - 1.68) / 2.1 = 0.20
        assert _desvio_alem_da_faixa(1.68, 2.1, 2.7) == pytest.approx(0.20)


# --------------------------------------------------------------------------
# Classificação de risco e limiares
# --------------------------------------------------------------------------

class TestClassificacao:
    def test_dentro_da_tolerancia_e_verde(self):
        assert classificar(0.0) == "VERDE"
        assert classificar(LIMIAR_ATENCAO - 0.001) == "VERDE"

    def test_limiar_de_atencao_e_inclusivo(self):
        assert classificar(LIMIAR_ATENCAO) == "AMARELO"

    def test_faixa_intermediaria_e_amarela(self):
        assert classificar(0.15) == "AMARELO"
        assert classificar(LIMIAR_ALERTA - 0.001) == "AMARELO"

    def test_limiar_de_alerta_e_inclusivo(self):
        assert classificar(LIMIAR_ALERTA) == "VERMELHO"

    def test_desvio_alto_e_vermelho(self):
        assert classificar(0.85) == "VERMELHO"


# --------------------------------------------------------------------------
# Cenários de uso ponta a ponta
# --------------------------------------------------------------------------

class TestCenarios:
    def test_peso_adequado_nao_gera_acao(self):
        r = avaliar_peso(2.4)
        assert r["risco"] == "VERDE"
        assert r["tipo_recomendacao"] == "PESO_ADEQUADO"
        assert r["acoes"] == []

    def test_desvio_dentro_da_tolerancia_continua_verde(self):
        # 2,9 kg = 7% acima de 2,7 -> abaixo da tolerância de 10%
        r = avaliar_peso(2.9)
        assert r["risco"] == "VERDE"
        assert r["acoes"] == []

    def test_caso_aurora_gera_atencao(self):
        """Caso de referência usado na apresentação: 3,2 kg -> 19% acima."""
        r = avaliar_peso(3.2)
        assert r["risco"] == "AMARELO"
        assert r["tipo_recomendacao"] == "PESO_ATENCAO"
        assert r["desvio_alem_da_faixa"] == pytest.approx(0.185, abs=0.001)
        assert "19% acima" in r["justificativa"]
        assert "2,1 a 2,7 kg" in r["justificativa"]
        assert "Yorkshire Terrier fêmea de 4 anos" in r["justificativa"]

    def test_atencao_gera_recomendacao_e_lembrete_de_pesagem(self):
        acoes = avaliar_peso(3.2)["acoes"]
        assert [a["registro"] for a in acoes] == ["RECOMENDACAO", "LEMBRETE"]
        assert acoes[0]["tipo"] == "PESO_ATENCAO"
        assert acoes[1]["tipo"] == "PESAGEM"
        assert acoes[1]["prazo_dias"] == PRAZO_PESAGEM_DIAS

    def test_desvio_acentuado_gera_alerta_e_consulta(self):
        r = avaliar_peso(5.0)
        assert r["risco"] == "VERMELHO"
        acoes = r["acoes"]
        assert acoes[0]["tipo"] == "PESO_ALERTA"
        assert acoes[1]["tipo"] == "CONSULTA"
        assert acoes[1]["prazo_dias"] == PRAZO_CONSULTA_DIAS
        assert "consulta" in acoes[0]["descricao"].lower()

    def test_baixo_peso_tambem_gera_alerta(self):
        r = avaliar_peso(1.2)
        assert r["risco"] == "VERMELHO"
        assert "abaixo" in r["justificativa"]

    def test_faixa_esperada_vai_na_resposta(self):
        r = avaliar_peso(3.2)
        assert r["faixa_esperada_kg"] == {"min": 2.1, "max": 2.7}


# --------------------------------------------------------------------------
# Casos especiais
# --------------------------------------------------------------------------

class TestFilhote:
    def test_filhote_nao_recebe_alerta(self):
        """Ganho de peso do crescimento não pode virar falso alerta."""
        r = avaliar_peso(5.0, idade_anos=0.5)
        assert r["risco"] == "VERDE"
        assert r["acoes"] == []
        assert "fase de crescimento" in r["justificativa"]

    def test_filhote_mantem_o_diagnostico_numerico(self):
        r = avaliar_peso(5.0, idade_anos=0.5)
        assert "85% acima" in r["justificativa"]

    def test_adulto_no_limite_da_idade_recebe_alerta_normal(self):
        r = avaliar_peso(5.0, idade_anos=1.0)
        assert r["risco"] == "VERMELHO"


class TestSemRacaDefinida:
    def test_srd_nao_escala_para_vermelho(self):
        """Faixa geral da espécie é imprecisa: classificação conservadora."""
        r = avaliar(peso_kg=8.5, p10=2.5, p90=6.5, especie="Gato",
                     raca=None, sexo="F", idade_anos=3.0, usou_fallback=True)
        assert r["risco"] == "AMARELO"
        assert "faixa geral da espécie" in r["justificativa"]

    def test_srd_dentro_da_faixa_continua_verde(self):
        r = avaliar(peso_kg=4.0, p10=2.5, p90=6.5, especie="Gato",
                     raca=None, sexo="M", idade_anos=3.0, usou_fallback=True)
        assert r["risco"] == "VERDE"

    def test_srd_descreve_o_perfil_sem_raca(self):
        r = avaliar(peso_kg=8.5, p10=2.5, p90=6.5, especie="Gato",
                     raca=None, sexo="F", idade_anos=3.0, usou_fallback=True)
        assert "gata SRD" in r["justificativa"]


# --------------------------------------------------------------------------
# Formatação em português
# --------------------------------------------------------------------------

class TestFormatacao:
    def test_peso_usa_virgula_decimal(self):
        assert _kg(3.2) == "3,2"
        assert _kg(32.0) == "32,0"

    def test_justificativa_nao_tem_ponto_decimal_em_peso(self):
        just = avaliar_peso(3.2)["justificativa"]
        assert "3.2 kg" not in just
        assert "3,2 kg" in just

    @pytest.mark.parametrize("especie,raca,sexo,idade,esperado", [
        ("Cachorro", "Yorkshire Terrier", "F", 4, "uma Yorkshire Terrier fêmea de 4 anos"),
        ("Cachorro", "Labrador Retriever", "M", 5, "um Labrador Retriever macho de 5 anos"),
        ("Gato", None, "F", 3, "uma gata SRD de 3 anos"),
        ("Cachorro", None, "M", 2, "um cão SRD de 2 anos"),
        ("Gato", "Siamese", "F", 1, "uma Siamese fêmea de 1 ano"),
        ("Cachorro", "Great Dane", "M", 0.5, "um Great Dane macho de 6 meses"),
    ])
    def test_concordancia_do_perfil(self, especie, raca, sexo, idade, esperado):
        assert _descrever_perfil(especie, raca, sexo, idade) == esperado


# --------------------------------------------------------------------------
# Determinismo — requisito do projeto
# --------------------------------------------------------------------------

def test_mesma_entrada_produz_sempre_a_mesma_saida():
    """Reprodutibilidade é requisito: nada de saída não determinística."""
    assert avaliar_peso(3.2) == avaliar_peso(3.2)
