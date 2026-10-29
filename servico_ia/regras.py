# -*- coding: utf-8 -*-
"""
Fidelis - Motor de regras inteligentes
======================================
Traduz a faixa esperada (estimada pelo modelo) em decisão: classifica o
risco em VERDE / AMARELO / VERMELHO e monta as ações que o backend .NET
deve persistir (RECOMENDACOES e LEMBRETES). Regras parametrizáveis e
auditáveis: cada resposta carrega a justificativa numérica do alerta.

O texto das recomendações é montado por template parametrizado — nunca
gerado livremente — para que a mesma entrada produza sempre a mesma
saída e cada frase seja rastreável até os números que a originaram.
"""
from __future__ import annotations

# ---- Parâmetros das regras (limiares sobre o desvio além da faixa) ----
LIMIAR_ATENCAO = 0.10   # até 10% além da borda: ainda VERDE (tolerância)
LIMIAR_ALERTA = 0.20    # 10-20%: AMARELO | acima de 20%: VERMELHO
IDADE_ADULTO_ANOS = 1.0  # abaixo disso: filhote (nunca eleva além de informativo)

PRAZO_PESAGEM_DIAS = 15   # lembrete de nova pesagem (risco AMARELO)
PRAZO_CONSULTA_DIAS = 7   # lembrete de consulta (risco VERMELHO)

# Fallback por espécie para pets SRD / raça fora da base de referência.
# Faixas conservadoras de peso adulto; para cães, a amplitude entre portes
# é grande demais para uma faixa única útil, então o fallback canino só
# sinaliza extremos evidentes.
FALLBACK_ESPECIE = {
    "Gato": (2.5, 6.5),
    "Cachorro": (3.0, 45.0),
}

# Condutas por nível de risco (parte variável do template)
CONDUTA = {
    "VERDE": "O peso está adequado para o perfil. Continue acompanhando.",
    "AMARELO": ("Vale revisar a alimentação e a rotina de exercícios, "
                "e acompanhar nas próximas semanas."),
    "VERMELHO": "Recomendamos agendar uma consulta de avaliação na clínica.",
}


def _kg(valor: float) -> str:
    """Formata um peso no padrão brasileiro: 3,2 em vez de 3.2."""
    return f"{valor:.1f}".replace(".", ",")


def _descrever_perfil(especie: str, raca: str | None, sexo: str,
                      idade_anos: float) -> str:
    """Monta a descrição do perfil usada na justificativa.

    Ex.: "uma Yorkshire Terrier fêmea de 4 anos" / "um gato SRD de 3 anos".
    """
    femea = sexo == "F"
    artigo = "uma" if femea else "um"
    genero = "fêmea" if femea else "macho"

    if raca:
        nucleo = f"{raca} {genero}"
    else:  # sem raça definida: o substantivo já carrega o gênero
        if especie == "Cachorro":
            nucleo = "cadela SRD" if femea else "cão SRD"
        else:
            nucleo = "gata SRD" if femea else "gato SRD"

    if idade_anos < 1:
        meses = max(1, round(idade_anos * 12))
        idade = f"{meses} {'mês' if meses == 1 else 'meses'}"
    else:
        anos = int(round(idade_anos))
        idade = f"{anos} {'ano' if anos == 1 else 'anos'}"

    return f"{artigo} {nucleo} de {idade}"


def _desvio_alem_da_faixa(peso: float, p10: float, p90: float) -> float:
    """Desvio percentual do peso além da borda mais próxima da faixa.

    0.0 quando dentro da faixa; positivo quando fora (ex.: 0.25 = 25%
    além da borda, para cima ou para baixo).
    """
    if peso < p10:
        return (p10 - peso) / p10
    if peso > p90:
        return (peso - p90) / p90
    return 0.0


def classificar(desvio: float) -> str:
    """Mapeia o desvio para o nível de risco, antes dos casos especiais."""
    if desvio < LIMIAR_ATENCAO:
        return "VERDE"
    if desvio < LIMIAR_ALERTA:
        return "AMARELO"
    return "VERMELHO"


def avaliar(*, peso_kg: float, p10: float, p90: float, especie: str,
            raca: str | None, sexo: str, idade_anos: float,
            usou_fallback: bool) -> dict:
    """Classifica o risco e monta a recomendação e o lembrete sugeridos."""
    desvio = _desvio_alem_da_faixa(peso_kg, p10, p90)
    direcao = "acima" if peso_kg > p90 else "abaixo"
    perfil = _descrever_perfil(especie, raca, sexo, idade_anos)
    risco = classificar(desvio)

    # ---- Parte fixa do template: o diagnóstico numérico ----
    if desvio == 0.0:
        diagnostico = (
            f"{_kg(peso_kg)} kg está dentro da faixa esperada de "
            f"{_kg(p10)} a {_kg(p90)} kg para {perfil}."
        )
    else:
        diagnostico = (
            f"{_kg(peso_kg)} kg está {desvio:.0%} {direcao} da faixa esperada "
            f"de {_kg(p10)} a {_kg(p90)} kg para {perfil}."
        )

    # ---- Casos especiais (podem rebaixar o risco) ----
    sufixos: list[str] = []

    # Filhote em crescimento: avaliação apenas informativa
    if idade_anos < IDADE_ADULTO_ANOS and risco != "VERDE":
        risco = "VERDE"
        sufixos.append(
            "Animal em fase de crescimento — avaliação apenas informativa."
        )

    # Pet SRD / raça fora da base: faixa conservadora, não eleva a VERMELHO
    if usou_fallback and risco == "VERMELHO":
        risco = "AMARELO"
        sufixos.append(
            "Avaliação baseada na faixa geral da espécie."
        )
    elif usou_fallback:
        sufixos.append("Avaliação baseada na faixa geral da espécie.")

    tipo = {"VERDE": "PESO_ADEQUADO", "AMARELO": "PESO_ATENCAO",
            "VERMELHO": "PESO_ALERTA"}[risco]

    justificativa = " ".join([diagnostico] + sufixos)
    descricao = " ".join([diagnostico, CONDUTA[risco]] + sufixos)

    # ---- Ações a persistir pelo backend .NET ----
    acoes: list[dict] = []
    if risco == "AMARELO":
        acoes = [
            {"registro": "RECOMENDACAO", "tipo": tipo, "descricao": descricao},
            {"registro": "LEMBRETE", "tipo": "PESAGEM",
             "prazo_dias": PRAZO_PESAGEM_DIAS,
             "descricao": "Registrar nova pesagem para acompanhamento."},
        ]
    elif risco == "VERMELHO":
        acoes = [
            {"registro": "RECOMENDACAO", "tipo": tipo, "descricao": descricao},
            {"registro": "LEMBRETE", "tipo": "CONSULTA",
             "prazo_dias": PRAZO_CONSULTA_DIAS,
             "descricao": "Agendar consulta de avaliação do peso."},
        ]

    return {
        "risco": risco,
        "tipo_recomendacao": tipo,
        "faixa_esperada_kg": {"min": round(p10, 1), "max": round(p90, 1)},
        "peso_informado_kg": peso_kg,
        "desvio_alem_da_faixa": round(desvio, 3),
        "justificativa": justificativa,
        "acoes": acoes,
    }
