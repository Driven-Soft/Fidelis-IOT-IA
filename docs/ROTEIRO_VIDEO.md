# Roteiro — Vídeo Pitch (~5 min) · Fidelis · 4º Sprint

**Objetivo:** mostrar o componente de IA funcionando dentro do Fidelis, com o contexto completo — o que é o app, o que a IA faz, como funciona, por que cada abordagem foi escolhida — e provar o funcionamento no app.

**Formato:** um narrador, gravação de tela, tom técnico. A demonstração é **ao vivo**: uma pesagem nova é registrada pelo Swagger da API durante o vídeo, e o app muda de adequado para atenção na frente do avaliador.

**Telas usadas:** app no navegador (modo celular), Swagger da API .NET, README do repositório e um terminal para os testes.

---

## Antes de gravar (não aparece no vídeo)

### 1. Subir as aplicações

Siga o `FidelisTesteGeral.md` (3 terminais): serviço de IA, API .NET e app **no navegador**. Ligue o CORS temporário descrito lá, senão o login do app web falha.

No navegador, abra o app em modo celular (DevTools → *Toggle device toolbar*, ex.: iPhone 12) para ele aparecer com proporção de celular.

### 2. Criar uma pet limpa para a gravação

Em um 4º terminal, crie um tutor e uma pet "Aurora" com **quatro pesagens dentro da faixa**. A quinta pesagem, que dispara o alerta, é feita ao vivo no Bloco 3.

```bash
API=http://localhost:5232; EMAIL="video.$(date +%m%d%H%M)@fidelis.test"; echo "Login do vídeo: $EMAIL / 123456"
```
```bash
curl -s -X POST $API/api/Tutor -H 'Content-Type: application/json' -d "{\"cpf\":\"8$(date +%m%d%H%M%S | cut -c1-10)\",\"nome\":\"Tutor Demonstração\",\"email\":\"$EMAIL\",\"senha\":\"123456\",\"telefone\":\"11988476632\",\"endereco\":\"Rua Fidelis, 1\"}" > /dev/null
```
```bash
LOGIN=$(curl -s -X POST $API/api/Auth/login -H 'Content-Type: application/json' -d "{\"email\":\"$EMAIL\",\"senha\":\"123456\",\"tipo\":\"TUTOR\"}"); TOKEN=$(echo "$LOGIN" | python3 -c "import sys,json; print(json.load(sys.stdin)['token'])"); TUTOR=$(echo "$LOGIN" | python3 -c "import sys,json; print(json.load(sys.stdin)['tutorId'])")
```
```bash
PET=$(curl -s -X POST $API/api/Pet -H "Authorization: Bearer $TOKEN" -H 'Content-Type: application/json' -d "{\"nome\":\"Aurora\",\"especie\":\"Cão\",\"raca\":\"Yorkshire\",\"sexo\":\"F\",\"dataNascimento\":\"2022-10-26T00:00:00\",\"fotoUrl\":\"https://placedog.net/200/200?id=12\",\"tutorId\":$TUTOR}" | python3 -c "import sys,json; print(json.load(sys.stdin)['data']['id'])"); echo "petId=$PET"
```
```bash
for p in "2.3 2025-11-10" "2.5 2026-02-12" "2.6 2026-05-08" "2.9 2026-08-03"; do set -- $p; curl -s -X POST $API/api/HistoricoPeso -H "Authorization: Bearer $TOKEN" -H 'Content-Type: application/json' -d "{\"pesoKg\":$1,\"dataMedicao\":\"$2T00:00:00\",\"petId\":$PET}" | python3 -c "import sys,json; d=json.load(sys.stdin)['data']; print(d['pesoKg'], d['avaliacaoIa']['risco'])"; done
```

As quatro devem sair `VERDE`. Anote o **email** e o **petId**.

### 3. Preparar os Swaggers

**Swagger da API .NET** (http://localhost:5232/swagger):

1. `POST /api/Auth/login` com o email do vídeo, senha `123456` e `"tipo": "TUTOR"` → copiar o `token`.
2. **Authorize** → colar o token.
3. Deixar aberto o `POST /api/HistoricoPeso` com o corpo pronto (troque `PET_ID` e a data de hoje):

```json
{ "pesoKg": 3.2, "dataMedicao": "2026-10-30T00:00:00", "petId": PET_ID }
```

4. Deixar aberto também `GET /api/Recomendacao` e `GET /api/Lembrete` com o filtro `petId` preenchido.


### 4. Ordem das abas

1. App no navegador, logado com o tutor do vídeo, na tela inicial
2. Swagger da API .NET
3. README do repositório no GitHub
4. Terminal na pasta `~/Code/IOT/FidelisAI/servico_ia`

---

## Bloco 1 — O Fidelis (0:00 – 0:30)

**Na tela:** app na tela inicial do tutor; apontar cada parte enquanto fala.

> "Este é o **Fidelis**, aplicativo de saúde pet da Driven Soft para a CLYVO VET. Estou mostrando no navegador só para facilitar a gravação; é o mesmo app React Native.
>
> O app tem dois portais. No portal do tutor, o dono acompanha seus pets, os próximos cuidados e o histórico. No portal do veterinário, a clínica cadastra os pets e registra os cuidados, que aparecem para o tutor como lembretes com data prevista, como vacinas, consultas e pesagens. O componente de IA atua sobre um desses dados: ele avalia **o peso do pet** automaticamente."

## Bloco 2 — O que a IA resolve (0:30 – 1:00)

**Na tela:** perfil da Aurora → seção "Peso e avaliação da IA"; apontar a faixa, os pontos e o card enquanto fala.

> "O problema é que o peso saudável depende da espécie, da raça, do sexo e da idade. Um Yorkshire adulto pesa cerca de 2,5 kg, enquanto um Labrador passa de 30, e o tutor normalmente não sabe qual é a faixa certa para o seu pet.
>
> Esta é a Aurora, uma Yorkshire de 4 anos. A faixa verde no gráfico é a faixa de peso esperada para o perfil dela, de 2,1 a 2,7 kg, e foi **estimada pela IA**. Os pontos são as pesagens registradas ao longo do tempo, e o card acima mostra a avaliação da IA para a última pesagem, que hoje está adequada."

## Bloco 3 — Demonstração ao vivo (1:00 – 2:00)

**Na tela:** Swagger da API → `POST /api/HistoricoPeso` → **Execute** → destacar `avaliacaoIa` na resposta.

> "Agora vou registrar uma nova pesagem de **3,2 kg**, como a clínica faria. Assim que o peso é salvo, o sistema envia os dados da Aurora para o serviço de IA, que devolve a avaliação: risco **amarelo**, faixa esperada de 2,1 a 2,7 kg e a justificativa — *'3,2 kg está 19% acima da faixa esperada'*."

**Na tela:** voltar ao app → reabrir o perfil da Aurora (card de atenção, ponto novo no gráfico, lembrete de pesagem).

> "No app, sem nenhuma ação do tutor, o card passou para **atenção**, com a recomendação de revisar alimentação e exercícios, o gráfico mostra a curva saindo da faixa e apareceu um **lembrete de nova pesagem em 15 dias**. A IA é transparente para o usuário: roda automaticamente a cada pesagem."

**Na tela:** Swagger da API → `GET /api/Recomendacao` e `GET /api/Lembrete` com `petId`.

> "E a recomendação e o lembrete ficaram gravados no banco de dados do app. Ou seja, a IA está integrada de ponta a ponta: do app até o banco."

**Dica:** se o card demorar a atualizar, volte à lista de pets e abra a Aurora de novo.

## Bloco 4 — Como a IA funciona e por que cada escolha (2:00 – 3:20)

**Na tela:** README, seção "Visão geral" (diagrama App → API .NET → Serviço de IA) → seção 4 (dados).

> "A nossa IA tem duas partes: um modelo de aprendizado de máquina, que estima a faixa de peso, e um motor de regras, que decide o que fazer com ela.
>
> Começando pelos dados. Como o app é novo, não tínhamos histórico próprio, então treinamos o modelo com dados públicos de cães e gatos do Kaggle. Ao analisar esses dados, vimos que os pesos eram aleatórios. Tinha Yorkshire com mais de vinte quilos. Por isso, recalculamos o peso de cada animal com base nos padrões oficiais da sua raça e do seu sexo. No final, ficamos com quase quatro mil animais, de oitenta e três raças.
>
> Agora o modelo. Usamos um **Gradient Boosting**, da biblioteca scikit-learn. Ele aprende o peso típico de um animal a partir da espécie, da raça, do sexo e da idade. Escolhemos esse modelo porque os dados são em tabela, e ele lida bem com informações como raça e sexo e com a combinação entre elas. A faixa saudável é o intervalo onde estão oitenta por cento dos animais daquele perfil. É o mesmo princípio das curvas de crescimento usadas pelos veterinários.
>
> Por fim, as regras. Se o peso passa até dez por cento da faixa, ainda é considerado adequado. Entre dez e vinte por cento, é atenção. Acima de vinte por cento, é alerta, tanto para mais quanto para menos. Filhotes recebem só uma avaliação informativa, porque ganhar peso faz parte do crescimento. E o texto da recomendação é montado com os números da avaliação, nunca inventado. Assim, todo alerta pode ser conferido."

## Bloco 5 — Por que não outras abordagens (3:20 – 3:50)

**Na tela:** README, seção 3 (tabela de alternativas descartadas).

> "Descartamos um **LLM** porque o problema é numérico: modelos de linguagem não são confiáveis em cálculo, têm custo por chamada, dependem de serviço externo e podem responder diferente à mesma entrada — inaceitável para um sinal de saúde. **Sistema de recomendação** pressupõe preferências de muitos usuários sobre itens, o que não é o caso; **NLP** não se aplica, porque a entrada não é texto; e **só regras**, sem modelo, exigiria cadastrar à mão faixas para centenas de combinações. A nossa solução é **determinística, explicável e de custo praticamente zero**, e funciona desde a primeira pesagem."

## Bloco 6 — Arquitetura do componente, validação e resultados (3:50 – 4:35)

**Na tela:** README, seção 5 (diagrama arquitetural).

> "Na arquitetura, a IA é um **serviço próprio, em Python com FastAPI**. O fluxo é simples: o app registra a pesagem, o backend do app envia o perfil e o peso para o serviço de IA, a IA devolve a avaliação, e o backend grava e mostra o resultado.
>
> Por que um serviço separado? Porque a IA usa o ecossistema de ciência de dados do Python, e assim podemos **retreinar e atualizar o modelo sem mexer no resto do sistema**. O serviço também não guarda nenhum dado: recebe o perfil, responde e esquece — o que o deixa simples, seguro e fácil de testar. E não precisamos alterar nenhuma tabela do banco."

**Na tela:** terminal → rodar os testes → README, seção 14 (métricas).

```bash
../.venv/bin/python -m pytest -q
```

> "Para validar, o serviço de IA tem **83 testes automatizados** — rodando aqui —, cobrindo os limiares de risco, os casos especiais, a validação dos dados de entrada e a personalização. Avaliado em 20% dos dados que o modelo nunca viu, ele tem **erro médio de 1,5 kg**, **erro relativo de 9,8%** e **R² de 0,975**."

## Bloco 7 — Fechamento (4:35 – 5:00)

**Na tela:** de volta ao app, card de atenção e lembrete da Aurora.

> "Para o **tutor**, a IA transforma uma pesagem em cuidado: recomendação personalizada, lembrete no momento certo e o acompanhamento contínuo do peso pelo gráfico. Para a **clínica**, cada alerta é uma reconexão com o cliente baseada num sinal clínico real — e a decisão final continua sempre com o veterinário.
>
> Esse é o Fidelis: cuidado contínuo, preventivo e personalizado. Obrigado!"

---

## Checklist rápido

- [ ] IA, API e app rodando; CORS temporário ligado; login do vídeo funcionando no app
- [ ] Aurora com 4 pesagens verdes antes de gravar
- [ ] Swagger da API autorizado, com o `POST /api/HistoricoPeso` pronto (petId e data de hoje)
- [ ] Terminal na pasta `servico_ia`
- [ ] Duração final perto de 5 minutos
- [ ] Vídeo publicado no YouTube como **não listado** e link colocado no topo do README
- [ ] Depois de gravar: desfazer o CORS temporário

## Cobertura dos requisitos do PDF (4º Sprint)

| Requisito | Onde aparece no vídeo |
|---|---|
| Ideia central do projeto | Bloco 1 (o Fidelis) e Bloco 2 (o problema do peso) |
| Funcionamento da IA | Bloco 3 (ao vivo) e Bloco 4 (dados, modelo e regras) |
| Demonstração funcional dos principais recursos | Bloco 3: pesagem real, avaliação, card, gráfico e lembrete no app |
| IA integrada e transparente ao usuário | Bloco 3: roda a cada pesagem, sem ação do tutor |
| Comunicação entre interface, banco, APIs e serviço de IA | Bloco 3 (resultado gravado no banco) e Bloco 6 (fluxo app → backend → IA) |
| Dados preparados, com testes e validação | Bloco 4 (Kaggle, auditoria e recalibração) |
| Testar e validar em cenários de uso | Bloco 6 (testes rodando e cenários cobertos) |
| Avaliar resultados | Bloco 6 (métricas em dados não vistos) |
| Personalização da experiência do tutor | Bloco 2 (faixa estimada para o perfil da Aurora) e Bloco 4 (modelo por espécie, raça, sexo e idade) |
| Acompanhamento contínuo da saúde do pet | Bloco 2 e Bloco 7 (gráfico de evolução) |
| Benefícios para tutor e clínica | Bloco 7 |
| Integração com os demais componentes | Bloco 6 (app, backend, serviço de IA e banco) |
| Escolha justificada de cada abordagem | Blocos 4, 5 e 6 |
| Duração de ~5 minutos | Soma dos blocos: 5:00 |
