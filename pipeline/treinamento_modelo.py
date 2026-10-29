# -*- coding: utf-8 -*-
"""
Fidelis - Treinamento do modelo de faixa de peso esperada por perfil
====================================================================
Abordagem híbrida, no mesmo princípio dos growth charts veterinários:
  1) Modelo preditivo (Gradient Boosting quantílico, alpha=0.5) estima o
     peso mediano esperado a partir do perfil (espécie, raça, sexo, idade);
  2) Faixa esperada [P10-P90] obtida por quantis empíricos do grupo
     (espécie x raça x sexo) no dataset de treinamento.

Executado uma única vez, offline. O artefato final (joblib) é embarcado
no serviço de IA (servico_ia/), que só faz inferência.

Uso:    python pipeline/treinamento_modelo.py
Saída:  servico_ia/modelo/modelo_faixa_peso.joblib
"""
from pathlib import Path

import joblib
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import GradientBoostingRegressor
from sklearn.metrics import mean_absolute_error
from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder

SEED = 42
RAIZ = Path(__file__).resolve().parent.parent
DATASET = RAIZ / "data" / "fidelis_training_dataset.csv"
SAIDA = RAIZ / "servico_ia" / "modelo" / "modelo_faixa_peso.joblib"
FEATURES_CAT = ["Especie", "Breed", "Gender"]
FEATURES_NUM = ["Age (Years)"]
ALVO = "Weight (kg)"


def main() -> None:
    df = pd.read_csv(DATASET)
    X = df[FEATURES_CAT + FEATURES_NUM]
    y = df[ALVO]
    X_tr, X_te, y_tr, y_te = train_test_split(
        X, y, test_size=0.2, random_state=SEED, stratify=df["Breed"]
    )
    print(f"Treino: {len(X_tr)} | Teste: {len(X_te)}")

    # ---- 1) Modelo da mediana (P50) ----
    pre = ColumnTransformer(
        [("cat", OneHotEncoder(handle_unknown="ignore"), FEATURES_CAT)],
        remainder="passthrough",
    )
    modelo_p50 = Pipeline([
        ("pre", pre),
        ("gbr", GradientBoostingRegressor(
            loss="quantile", alpha=0.5, n_estimators=600, max_depth=5,
            learning_rate=0.1, min_samples_leaf=5, random_state=SEED)),
    ]).fit(X_tr, y_tr)

    # ---- 2) Tabela de faixas empíricas P10-P90 por grupo ----
    tr = X_tr.copy()
    tr["w"] = y_tr
    tabela = tr.groupby(FEATURES_CAT)["w"].quantile([0.10, 0.90]).unstack()
    tabela.columns = ["p10", "p90"]

    # ---- Métricas (resultados parciais para o README) ----
    mae = mean_absolute_error(y_te, modelo_p50.predict(X_te))
    te = X_te.copy()
    te["w"] = y_te
    te = te.join(tabela, on=FEATURES_CAT)
    cobertura = ((te["w"] >= te["p10"]) & (te["w"] <= te["p90"])).mean()
    print(f"MAE do modelo (P50): {mae:.2f} kg")
    print(f"Cobertura da faixa P10-P90 no teste: {cobertura:.1%}")

    # ---- Exemplos de faixa por perfil ----
    exemplos = [("Cachorro", "Yorkshire Terrier", "Female"),
                ("Cachorro", "Labrador Retriever", "Male"),
                ("Cachorro", "Great Dane", "Male"),
                ("Gato", "Siamese", "Female"),
                ("Gato", "Maine Coon", "Male")]
    print("\nFaixas esperadas (P10-P90) por perfil:")
    print(tabela.loc[exemplos].round(1).to_string())

    # ---- Serialização: modelo + tabela + metadados ----
    artefato = {
        "modelo_p50": modelo_p50,
        "tabela_faixas": tabela,
        "racas_conhecidas": {
            esp: sorted(df.loc[df["Especie"] == esp, "Breed"].unique())
            for esp in df["Especie"].unique()
        },
        "metricas": {"mae_p50_kg": round(float(mae), 2),
                      "cobertura_p10_p90": round(float(cobertura), 3)},
    }
    joblib.dump(artefato, SAIDA)
    print(f"\nArtefato salvo em {SAIDA.relative_to(RAIZ)}")


if __name__ == "__main__":
    main()
