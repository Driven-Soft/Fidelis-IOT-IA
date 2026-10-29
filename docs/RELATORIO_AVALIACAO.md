# Relatório de avaliação — Componente de IA do Fidelis

Gerado por `pipeline/avaliacao_modelo.py`. Reproduzível: semente fixa (`random_state=42`) e mesma divisão treino/teste do treinamento.

## 1. Base de dados

- Registros: **3990** (2995 cães, 995 gatos)
- Raças distintas: **83**
- Divisão: 3192 treino / 798 teste, estratificada por raça
- Origem: datasets públicos do Kaggle, auditados e recalibrados por faixas de referência de peso adulto por raça e sexo (`pipeline/prepare_dataset.py`)

## 2. Métricas do modelo

| Métrica | Valor | Leitura |
|---|---|---|
| MAE (erro absoluto médio) | **1,5 kg** | Erro típico da estimativa de peso mediano |
| Erro relativo médio | **9.8%** | Erro proporcional ao porte do animal |
| R² | **0.975** | Variância do peso explicada pelo perfil |
| Cobertura da faixa P10–P90 | **73.9%** | Pesagens reais dentro da faixa prevista (alvo ~80%) |

Por espécie:

| Espécie | Amostras (teste) | MAE | Erro relativo |
|---|---|---|---|
| Cachorro | 600 | 1,8 kg | 8.9% |
| Gato | 198 | 0,6 kg | 12.4% |

> O MAE em quilos é naturalmente maior para cães, cuja escala de peso vai de ~1,5 kg a ~90 kg; por isso o erro relativo é a métrica comparável entre espécies.

## 3. Personalização: a faixa muda com o perfil

A faixa esperada é calculada por perfil, não por regra genérica. Amostra das faixas aprendidas:

| Espécie | Raça | Sexo | Idade | Faixa esperada (P10–P90) |
|---|---|---|---|---|
| Cachorro | Chihuahua | fêmea | 4 anos | 1,6 – 2,3 kg |
| Cachorro | Yorkshire Terrier | fêmea | 4 anos | 2,1 – 2,7 kg |
| Cachorro | Beagle | macho | 4 anos | 11,3 – 13,4 kg |
| Cachorro | Labrador Retriever | macho | 5 anos | 30,0 – 34,5 kg |
| Cachorro | Great Dane | macho | 3 anos | 67,1 – 88,1 kg |
| Cachorro | Saint Bernard | macho | 4 anos | 68,8 – 86,8 kg |
| Gato | Singapura | fêmea | 4 anos | 2,0 – 2,8 kg |
| Gato | Siamese | fêmea | 4 anos | 2,6 – 3,8 kg |
| Gato | Persian | macho | 4 anos | 4,6 – 6,2 kg |
| Gato | Maine Coon | macho | 5 anos | 8,0 – 10,7 kg |

### O mesmo peso, vereditos opostos

Prova prática de que a avaliação é individualizada: **3,2 kg** submetido a três perfis diferentes.

| Perfil | Faixa esperada | Veredito para 3,2 kg |
|---|---|---|
| Yorkshire Terrier | 2,1 – 2,7 kg | 🟡 Amarelo |
| Beagle | 11,3 – 13,4 kg | 🔴 Vermelho |
| Labrador Retriever | 30,0 – 34,5 kg | 🔴 Vermelho |

## 4. Cenários de uso validados

Execução real do motor de regras sobre os cenários previstos no planejamento, incluindo os casos especiais.

| Cenário | Perfil | Peso | Faixa | Risco | Ações |
|---|---|---|---|---|---|
| Peso adequado | Labrador Retriever | 32,0 kg | 30,0–34,5 kg | 🟢 VERDE | 0 |
| Dentro da tolerância | Yorkshire Terrier | 2,9 kg | 2,1–2,7 kg | 🟢 VERDE | 0 |
| Atenção (excesso) | Yorkshire Terrier | 3,2 kg | 2,1–2,7 kg | 🟡 AMARELO | 2 |
| Alerta (excesso) | Yorkshire Terrier | 5,0 kg | 2,1–2,7 kg | 🔴 VERMELHO | 2 |
| Alerta (déficit) | Labrador Retriever | 18,4 kg | 30,0–34,5 kg | 🔴 VERMELHO | 2 |
| Filhote em crescimento | Great Dane | 25,0 kg | 67,1–88,1 kg | 🟢 VERDE | 0 |
| Gato adequado | Siamese | 3,2 kg | 2,6–3,8 kg | 🟢 VERDE | 0 |
| Gato em alerta | Maine Coon | 15,0 kg | 8,0–10,7 kg | 🔴 VERMELHO | 2 |
| SRD fora da faixa | SRD | 8,5 kg | 2,5–6,5 kg | 🟡 AMARELO | 2 |

Justificativas geradas (texto que chega ao tutor):

- **Peso adequado** 🟢 — 32,0 kg está dentro da faixa esperada de 30,0 a 34,5 kg para um Labrador Retriever macho de 5 anos.
- **Dentro da tolerância** 🟢 — 2,9 kg está 7% acima da faixa esperada de 2,1 a 2,7 kg para uma Yorkshire Terrier fêmea de 4 anos.
- **Atenção (excesso)** 🟡 — 3,2 kg está 19% acima da faixa esperada de 2,1 a 2,7 kg para uma Yorkshire Terrier fêmea de 4 anos.
- **Alerta (excesso)** 🔴 — 5,0 kg está 85% acima da faixa esperada de 2,1 a 2,7 kg para uma Yorkshire Terrier fêmea de 4 anos.
- **Alerta (déficit)** 🔴 — 18,4 kg está 39% abaixo da faixa esperada de 30,0 a 34,5 kg para um Labrador Retriever macho de 5 anos.
- **Filhote em crescimento** 🟢 — 25,0 kg está 63% abaixo da faixa esperada de 67,1 a 88,1 kg para um Great Dane macho de 6 meses. Animal em fase de crescimento — avaliação apenas informativa.
- **Gato adequado** 🟢 — 3,2 kg está dentro da faixa esperada de 2,6 a 3,8 kg para uma Siamese fêmea de 4 anos.
- **Gato em alerta** 🔴 — 15,0 kg está 40% acima da faixa esperada de 8,0 a 10,7 kg para um Maine Coon macho de 5 anos.
- **SRD fora da faixa** 🟡 — 8,5 kg está 31% acima da faixa esperada de 2,5 a 6,5 kg para uma gata SRD de 3 anos. Avaliação baseada na faixa geral da espécie.

## 5. Testes automatizados

Suíte em `servico_ia/tests/`, executada com `pytest`:

- `test_regras.py` — cálculo do desvio, limiares de classificação, casos especiais (filhote e SRD), formatação em português e determinismo da saída
- `test_racas.py` — normalização da raça digitada no app: apelidos em português, acentos, SRD por extenso e separação por espécie
- `test_api.py` — contrato do endpoint, personalização por perfil, fallback de raça desconhecida, validação de entrada e chave de API

## 6. Limitações conhecidas

- A base de treinamento deriva de datasets públicos cuja coluna de peso foi recalibrada por faixas de referência de raça; não substitui uma base clínica real, que é o próximo passo natural do produto.
- Pets sem raça definida são avaliados pela faixa geral da espécie, o que detecta apenas desvios evidentes — por isso a classificação nesses casos é deliberadamente conservadora.
- O componente avalia adequação do peso ao perfil; não é instrumento diagnóstico. A conduta clínica permanece com o veterinário.