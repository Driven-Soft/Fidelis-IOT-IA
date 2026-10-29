# -*- coding: utf-8 -*-
"""
Fidelis - Serviço de IA (Python/FastAPI)
========================================
Serviço stateless, sem acesso a banco. Recebe do backend .NET o perfil do
pet e o peso atual, estima a faixa de peso esperada (modelo embarcado) e
devolve a classificação de risco com as ações a persistir.

Autenticação: quando a variável de ambiente FIDELIS_IA_API_KEY está
definida, POST /analise exige o header X-API-Key com o mesmo valor. Sem a
variável (execução local), o endpoint fica aberto. GET /health é sempre
público, para a verificação de saúde do serviço.

Execução local:
    uvicorn main:app --reload --port 8000
"""
import os
import secrets
from pathlib import Path
from typing import Literal, Optional

import joblib
import pandas as pd
from fastapi import Depends, FastAPI, HTTPException, Security, status
from fastapi.security import APIKeyHeader
from pydantic import BaseModel, Field

app = FastAPI(
    title="Fidelis - Serviço de IA",
    description="Avaliação de adequação de peso ao perfil do pet",
    version="1.1.0",
)

ARTEFATO = joblib.load(Path(__file__).parent / "modelo" / "modelo_faixa_peso.joblib")
MODELO_P50 = ARTEFATO["modelo_p50"]
TABELA_FAIXAS = ARTEFATO["tabela_faixas"]
RACAS = ARTEFATO["racas_conhecidas"]

from racas import normalizar_raca  # noqa: E402
from regras import FALLBACK_ESPECIE, avaliar  # noqa: E402

SEXO_MAP = {"M": "Male", "F": "Female"}

api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False,
                              description="Chave compartilhada com a API .NET")


def exigir_chave(chave: Optional[str] = Security(api_key_header)) -> None:
    """Valida o X-API-Key quando o serviço roda com FIDELIS_IA_API_KEY."""
    esperada = os.getenv("FIDELIS_IA_API_KEY")
    if not esperada:
        return
    if chave is None or not secrets.compare_digest(chave, esperada):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED,
                            detail="X-API-Key ausente ou inválida")


class AnaliseRequest(BaseModel):
    """Payload enviado pela API .NET após gravar uma pesagem."""
    pet_id: int = Field(..., description="PETS.Id")
    especie: Literal["Cachorro", "Gato"]
    raca: Optional[str] = Field(None, description="PETS.Raca; null/SRD usa fallback")
    sexo: Literal["M", "F"] = Field(..., description="PETS.Sexo")
    idade_anos: float = Field(..., ge=0, description="Derivada de PETS.DataNascimento")
    peso_kg: float = Field(..., gt=0, description="HISTORICO_PESOS.PesoKg mais recente")


@app.get("/health")
def health() -> dict:
    return {"status": "ok", "metricas_modelo": ARTEFATO["metricas"]}


@app.post("/analise", dependencies=[Depends(exigir_chave)])
def analise(req: AnaliseRequest) -> dict:
    genero = SEXO_MAP[req.sexo]
    raca = normalizar_raca(req.raca, req.especie, RACAS.get(req.especie, []))
    raca_conhecida = raca in RACAS.get(req.especie, [])

    if raca_conhecida:
        chave = (req.especie, raca, genero)
        if chave in TABELA_FAIXAS.index:
            p10, p90 = TABELA_FAIXAS.loc[chave, ["p10", "p90"]]
        else:  # raça na base, mas sem amostra deste sexo: usa o modelo
            perfil = pd.DataFrame([{
                "Especie": req.especie, "Breed": raca,
                "Gender": genero, "Age (Years)": req.idade_anos,
            }])
            p50 = float(MODELO_P50.predict(perfil)[0])
            p10, p90 = p50 * 0.85, p50 * 1.15
        usou_fallback = False
    else:  # SRD ou raça fora da base de referência
        p10, p90 = FALLBACK_ESPECIE[req.especie]
        usou_fallback = True

    resultado = avaliar(
        peso_kg=req.peso_kg, p10=float(p10), p90=float(p90),
        especie=req.especie, raca=raca,
        sexo=req.sexo, idade_anos=req.idade_anos,
        usou_fallback=usou_fallback,
    )
    return {
        "pet_id": req.pet_id,
        "perfil": {"especie": req.especie, "raca": raca,
                    "sexo": req.sexo, "idade_anos": req.idade_anos,
                    "raca_na_base_de_referencia": raca_conhecida},
        "avaliacao": resultado,
    }
