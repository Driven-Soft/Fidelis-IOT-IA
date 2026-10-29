# -*- coding: utf-8 -*-
"""
Fidelis - Avaliação do modelo e do motor de regras
==================================================
Gera as evidências de funcionamento exigidas pela entrega: métricas do
modelo, cobertura da faixa, exemplos de personalização por perfil e a
matriz de cenários do motor de regras.

Uso:    python pipeline/avaliacao_modelo.py
Saída:  docs/RELATORIO_AVALIACAO.md
"""
import sys
from pathlib import Path

import joblib
import pandas as pd
from sklearn.metrics import mean_absolute_error, r2_score
from sklearn.model_selection import train_test_split

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ / "servico_ia"))
from regras import FALLBACK_ESPECIE, avaliar  # noqa: E402

SEED = 42
DATASET = RAIZ / "data" / "fidelis_training_dataset.csv"
ARTEFATO = RAIZ / "servico_ia" / "modelo" / "modelo_faixa_peso.joblib"
SAIDA = RAIZ / "docs" / "RELATORIO_AVALIACAO.md"
FEATURES_CAT = ["Especie", "Breed", "Gender"]
FEATURES_NUM = ["Age (Years)"]


def faixa_do_perfil(art, especie, raca, genero, idade):
    """Reproduz a lógica de seleção de faixa usada pelo serviço."""
    chave = (especie, raca, genero)
    if raca in art["racas_conhecidas"].get(especie, []):
        if chave in art["tabela_faixas"].index:
            p10, p90 = art["tabela_faixas"].loc[chave, ["p10", "p90"]]
            return float(p10), float(p90), False
        perfil = pd.DataFrame([{"Especie": especie, "Breed": raca,
                                 "Gender": genero, "Age (Years)": idade}])
        p50 = float(art["modelo_p50"].predict(perfil)[0])
        return p50 * 0.85, p50 * 1.15, False
    p10, p90 = FALLBACK_ESPECIE[especie]
    return float(p10), float(p90), True


def main() -> None:
    art = joblib.load(ARTEFATO)
    df = pd.read_csv(DATASET)
    X = df[FEATURES_CAT + FEATURES_NUM]
    y = df["Weight (kg)"]
    _, X_te, _, y_te = train_test_split(
        X, y, test_size=0.2, random_state=SEED, stratify=df["Breed"])

    pred = art["modelo_p50"].predict(X_te)
    mae = mean_absolute_error(y_te, pred)
    r2 = r2_score(y_te, pred)
    erro_rel = (abs(y_te - pred) / y_te).mean()

    te = X_te.copy()
    te["w"] = y_te
    te = te.join(art["tabela_faixas"], on=FEATURES_CAT)
    cobertura = ((te["w"] >= te["p10"]) & (te["w"] <= te["p90"])).mean()

    # Métricas por espécie
    por_especie = []
    for esp in sorted(df["Especie"].unique()):
        m = X_te["Especie"] == esp
        por_especie.append((
            esp, int(m.sum()),
            mean_absolute_error(y_te[m], pred[m]),
            (abs(y_te[m] - pred[m]) / y_te[m]).mean(),
        ))

    # Personalização: faixas por perfil
    perfis = [
        ("Cachorro", "Chihuahua", "F", 4), ("Cachorro", "Yorkshire Terrier", "F", 4),
        ("Cachorro", "Beagle", "M", 4), ("Cachorro", "Labrador Retriever", "M", 5),
        ("Cachorro", "Great Dane", "M", 3), ("Cachorro", "Saint Bernard", "M", 4),
        ("Gato", "Singapura", "F", 4), ("Gato", "Siamese", "F", 4),
        ("Gato", "Persian", "M", 4), ("Gato", "Maine Coon", "M", 5),
    ]
    linhas_perfis = []
    for esp, raca, sexo, idade in perfis:
        genero = "Female" if sexo == "F" else "Male"
        p10, p90, _ = faixa_do_perfil(art, esp, raca, genero, idade)
        linhas_perfis.append((esp, raca, "fêmea" if sexo == "F" else "macho",
                               idade, p10, p90))

    # Mesmo peso, perfis diferentes (prova de personalização)
    contraste = []
    for esp, raca, sexo, idade in [("Cachorro", "Yorkshire Terrier", "F", 4),
                                     ("Cachorro", "Beagle", "M", 4),
                                     ("Cachorro", "Labrador Retriever", "M", 5)]:
        genero = "Female" if sexo == "F" else "Male"
        p10, p90, fb = faixa_do_perfil(art, esp, raca, genero, idade)
        r = avaliar(peso_kg=3.2, p10=p10, p90=p90, especie=esp, raca=raca,
                     sexo=sexo, idade_anos=idade, usou_fallback=fb)
        contraste.append((raca, p10, p90, r["risco"]))

    # Matriz de cenários do motor de regras
    cenarios = [
        ("Peso adequado", "Cachorro", "Labrador Retriever", "M", 5.0, 32.0),
        ("Dentro da tolerância", "Cachorro", "Yorkshire Terrier", "F", 4.0, 2.9),
        ("Atenção (excesso)", "Cachorro", "Yorkshire Terrier", "F", 4.0, 3.2),
        ("Alerta (excesso)", "Cachorro", "Yorkshire Terrier", "F", 4.0, 5.0),
        ("Alerta (déficit)", "Cachorro", "Labrador Retriever", "M", 5.0, 18.4),
        ("Filhote em crescimento", "Cachorro", "Great Dane", "M", 0.5, 25.0),
        ("Gato adequado", "Gato", "Siamese", "F", 4.0, 3.2),
        ("Gato em alerta", "Gato", "Maine Coon", "M", 5.0, 15.0),
        ("SRD fora da faixa", "Gato", None, "F", 3.0, 8.5),
    ]
    linhas_cenarios = []
    for nome, esp, raca, sexo, idade, peso in cenarios:
        genero = "Female" if sexo == "F" else "Male"
        p10, p90, fb = faixa_do_perfil(art, esp, raca, genero, idade)
        r = avaliar(peso_kg=peso, p10=p10, p90=p90, especie=esp,
                     raca=raca if not fb else None, sexo=sexo,
                     idade_anos=idade, usou_fallback=fb)
        linhas_cenarios.append((nome, raca or "SRD", peso, p10, p90,
                                 r["risco"], len(r["acoes"]), r["justificativa"]))

    # ---------------- Montagem do relatório ----------------
    def kg(v):
        return f"{v:.1f}".replace(".", ",")

    emoji = {"VERDE": "🟢", "AMARELO": "🟡", "VERMELHO": "🔴"}
    out = []
    A = out.append

    A("# Relatório de avaliação — Componente de IA do Fidelis\n")
    A("Gerado por `pipeline/avaliacao_modelo.py`. Reproduzível: semente fixa "
      f"(`random_state={SEED}`) e mesma divisão treino/teste do treinamento.\n")

    A("## 1. Base de dados\n")
    A(f"- Registros: **{len(df)}** ({len(df[df.Especie=='Cachorro'])} cães, "
      f"{len(df[df.Especie=='Gato'])} gatos)")
    A(f"- Raças distintas: **{df['Breed'].nunique()}**")
    A(f"- Divisão: {len(X)-len(X_te)} treino / {len(X_te)} teste, "
      "estratificada por raça")
    A("- Origem: datasets públicos do Kaggle, auditados e recalibrados por "
      "faixas de referência de peso adulto por raça e sexo "
      "(`pipeline/prepare_dataset.py`)\n")

    A("## 2. Métricas do modelo\n")
    A("| Métrica | Valor | Leitura |")
    A("|---|---|---|")
    A(f"| MAE (erro absoluto médio) | **{kg(mae)} kg** | Erro típico da "
      "estimativa de peso mediano |")
    A(f"| Erro relativo médio | **{erro_rel:.1%}** | Erro proporcional ao "
      "porte do animal |")
    A(f"| R² | **{r2:.3f}** | Variância do peso explicada pelo perfil |")
    A(f"| Cobertura da faixa P10–P90 | **{cobertura:.1%}** | Pesagens reais "
      "dentro da faixa prevista (alvo ~80%) |")
    A("")
    A("Por espécie:\n")
    A("| Espécie | Amostras (teste) | MAE | Erro relativo |")
    A("|---|---|---|---|")
    for esp, n, m, er in por_especie:
        A(f"| {esp} | {n} | {kg(m)} kg | {er:.1%} |")
    A("")
    A("> O MAE em quilos é naturalmente maior para cães, cuja escala de peso "
      "vai de ~1,5 kg a ~90 kg; por isso o erro relativo é a métrica "
      "comparável entre espécies.\n")

    A("## 3. Personalização: a faixa muda com o perfil\n")
    A("A faixa esperada é calculada por perfil, não por regra genérica. "
      "Amostra das faixas aprendidas:\n")
    A("| Espécie | Raça | Sexo | Idade | Faixa esperada (P10–P90) |")
    A("|---|---|---|---|---|")
    for esp, raca, sexo, idade, p10, p90 in linhas_perfis:
        A(f"| {esp} | {raca} | {sexo} | {idade} anos | "
          f"{kg(p10)} – {kg(p90)} kg |")
    A("")
    A("### O mesmo peso, vereditos opostos\n")
    A("Prova prática de que a avaliação é individualizada: **3,2 kg** "
      "submetido a três perfis diferentes.\n")
    A("| Perfil | Faixa esperada | Veredito para 3,2 kg |")
    A("|---|---|---|")
    for raca, p10, p90, risco in contraste:
        A(f"| {raca} | {kg(p10)} – {kg(p90)} kg | "
          f"{emoji[risco]} {risco.capitalize()} |")
    A("")

    A("## 4. Cenários de uso validados\n")
    A("Execução real do motor de regras sobre os cenários previstos no "
      "planejamento, incluindo os casos especiais.\n")
    A("| Cenário | Perfil | Peso | Faixa | Risco | Ações |")
    A("|---|---|---|---|---|---|")
    for nome, raca, peso, p10, p90, risco, n_acoes, _ in linhas_cenarios:
        A(f"| {nome} | {raca} | {kg(peso)} kg | {kg(p10)}–{kg(p90)} kg | "
          f"{emoji[risco]} {risco} | {n_acoes} |")
    A("")
    A("Justificativas geradas (texto que chega ao tutor):\n")
    for nome, _, _, _, _, risco, _, just in linhas_cenarios:
        A(f"- **{nome}** {emoji[risco]} — {just}")
    A("")

    A("## 5. Testes automatizados\n")
    A("Suíte em `servico_ia/tests/`, executada com `pytest`:\n")
    A("- `test_regras.py` — cálculo do desvio, limiares de classificação, "
      "casos especiais (filhote e SRD), formatação em português e "
      "determinismo da saída")
    A("- `test_racas.py` — normalização da raça digitada no app: apelidos "
      "em português, acentos, SRD por extenso e separação por espécie")
    A("- `test_api.py` — contrato do endpoint, personalização por perfil, "
      "fallback de raça desconhecida, validação de entrada e chave de API")
    A("")

    A("## 6. Limitações conhecidas\n")
    A("- A base de treinamento deriva de datasets públicos cuja coluna de "
      "peso foi recalibrada por faixas de referência de raça; não substitui "
      "uma base clínica real, que é o próximo passo natural do produto.")
    A("- Pets sem raça definida são avaliados pela faixa geral da espécie, "
      "o que detecta apenas desvios evidentes — por isso a classificação "
      "nesses casos é deliberadamente conservadora.")
    A("- O componente avalia adequação do peso ao perfil; não é instrumento "
      "diagnóstico. A conduta clínica permanece com o veterinário.")

    Path(SAIDA).write_text("\n".join(out), encoding="utf-8")
    print(f"Relatório gerado: {SAIDA.relative_to(RAIZ)}")
    print(f"MAE {kg(mae)} kg | erro relativo {erro_rel:.1%} | "
          f"R² {r2:.3f} | cobertura {cobertura:.1%}")


if __name__ == "__main__":
    main()
