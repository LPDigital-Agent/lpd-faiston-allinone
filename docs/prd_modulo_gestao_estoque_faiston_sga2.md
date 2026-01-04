# PRD — SGA 2.0 (Faiston)  
## Módulo 2: Gestão de Estoque (+/–) — AI‑First, Autônomo (Observa → Pensa → Aprende → Executa)

**Status:** Draft (v0.1)  
**Produto:** Faiston SGA 2.0  
**Módulo:** Gestão de Estoque (+/–) — *core* operacional  
**Owner:** Produto (LPDigital)  
**Stakeholders:** Logística (Bruna), Operação (Rodrigo), Financeiro/Fiscal, Técnicos de campo, Gestão (Diretoria), TI/Segurança

---

## 1) Resumo executivo

O Módulo de Gestão de Estoque é o “coração” do SGA 2.0: ele mantém a **fonte única de verdade** sobre **onde está cada ativo**, **qual o saldo** por **base/técnico/projeto**, e **quais movimentações** aconteceram (entrada, saída, transferência, reversa, ajustes).

A refatoração no SGA 2.0 muda o paradigma:

- Sai o modo “planilha + ponte com chamados”.  
- Entra um **motor autônomo** (AI‑First) que:
  1) **Observa** eventos (chamados, envios, reversas, notas fiscais, confirmações de técnicos, inventários);
  2) **Pensa** (planeja o fluxo correto e identifica inconsistências);
  3) **Aprende** (ajusta regras, extrações e previsões com feedback real);
  4) **Executa** (atualiza saldos, cria tarefas, solicita aprovações, notifica pessoas, e mantém auditoria).

O módulo deve ser projetado para operar com **estoque distribuído** (centro logístico, bases, self storage, “estoque avançado” com técnicos e service storages), com rastreio por **Part Number** e, quando aplicável, **Serial Number/RFID**, e com governança rígida (Human‑in‑the‑Loop) nos pontos de risco.

---

## 2) Problema e contexto

Hoje o controle “+ / –” e a visibilidade do estoque não se sustentam de ponta a ponta, principalmente por:

- Estoque distribuído (bases + técnicos + storage) com controle manual e fragmentado.
- Dificuldade de responder perguntas simples em tempo real: “quantos switches existem?”, “onde estão?”, “quantos em trânsito?”, “quantos em reversa?”.
- Movimentações e decisões dependem de *expertise* individual e troca manual de mensagens.
- A entrada de mercadoria depende de processo fiscal (NF/SAP) e depois “espelha” algo no SGA — com risco de divergência e retrabalho.
- O chamado (Tiflux) é o gatilho real de operação, mas o estoque não “fecha o ciclo” automaticamente.

O SGA 2.0 precisa tornar o inventário **auditável, vivo e autocorretivo**.

---

## 3) Objetivos de produto (e como medir)

### 3.1 Objetivos (O)

**O1.** Tornar o estoque distribuído “consultável” e confiável em tempo real (base única de verdade).  
**O2.** Reduzir drasticamente o trabalho manual (planilhas, conferências repetidas, consultas em múltiplas telas).  
**O3.** Garantir rastreabilidade ponta a ponta por ativo (do recebimento à expedição, instalação e reversa).  
**O4.** Permitir operação segura com autonomia (agents executam, humanos aprovam quando necessário).  
**O5.** Preparar base de dados e eventos para expedição, tracking, reversa e fiscal operarem “plug‑and‑play”.

### 3.2 KPIs sugeridos (K)

- **Acuracidade do estoque:** divergência ≤ 2% (global e por base).  
- **Tempo para localizar um item (serial ou PN):** P50 ≤ 30s, P90 ≤ 2 min.  
- **% de movimentações registradas automaticamente** (sem digitação manual): meta incremental por fase.  
- **Redução de inventários manuais** (quantidade e tempo gasto).  
- **Taxa de exceções por 1.000 movimentos** (itens sem serial, duplicidade, “sumiu”, etc.).  
- **Tempo de atualização por movimento** (da evidência → saldo atualizado).  
- **% de movimentos com evidência vinculada** (NF, comprovante, tracking, confirmação técnico, foto).

---

## 4) Princípios do módulo (AI‑First + Safety)

### 4.1 Autonomia por níveis (importante para governança)

- **Nível A — Sugere:** o agente recomenda; humano confirma.  
- **Nível B — Executa com revisão:** o agente executa e coloca na fila de revisão (prazo curto).  
- **Nível C — Executa autonomamente:** permitido apenas quando:
  - risco é baixo,
  - evidência é forte,
  - e há rollback simples.

### 4.2 “Evidência antes de ação”

Toda movimentação deve ter:
- **Evidência mínima** (ex.: NF, comprovante, tracking, foto de recebimento, confirmação de técnico, checklist de inventário).  
- **Trilha de auditoria** (quem/qual agente fez, quando, por qual motivo, com quais dados).

### 4.3 Human‑in‑the‑Loop obrigatório

Obrigatório em:
- Movimentos de alto valor / alto risco.
- Transferência entre projetos/contratos quando houver restrição contratual.
- Ajustes de inventário (diferença entre físico e sistema).
- Baixa/Descarte (BAD → Descarte) e perdas/extravio.
- Criação/alteração de Part Number quando impacta fiscal/contratos.

---

## 5) Escopo

### 5.1 Dentro do escopo (MVP do módulo)

1. Cadastro e catálogo de itens (Part Number) com regras de controle por serial e reversa obrigatória.  
2. Cadastro e rastreio de ativos (serial, RFID, etiqueta patrimonial).  
3. Estrutura de “locais de estoque” (bases, técnicos, storage, CD) e saldo por local.  
4. Movimentações (+/–): entrada, saída, transferência, reserva, reversa (entrada/saída) e ajuste.  
5. Integração conceitual com chamados: vínculo de movimento ↔ chamado (pai/filho) e “projeto”.  
6. Modo AI‑First:
   - leitura de NF por voz/documento,
   - atualização automática do saldo quando evidência existe,
   - detecção de divergências e abertura de tarefas.  
7. Inventário/cycle count com reconciliação assistida por IA.  
8. Permissões, logs e trilhas de auditoria do módulo (mesmo que o “Admin” completo esteja em outro módulo).

### 5.2 Fora do escopo (neste PRD)

- Modelagem completa de expedição (cotação, etiqueta, picking/packing avançado) — apenas o que o estoque precisa para reservar/baixar.
- Tracking automatizado por transportadora — apenas vínculo do tracking code ao movimento.
- Fiscal/contábil completo — aqui focamos em “dados que o fiscal precisa”.
- GeoDispatch e otimização de rota de técnicos — apenas tratar “técnico como local de estoque”.

### 5.3 Futuro (para não perder a trilha)

- Otimização preditiva: previsão de demanda por base/técnico e auto‑reposição.
- Detecção de fraudes/anomalias (compliance avançado).
- Simulação “what‑if” de estoque por contrato e SLA.

---

## 6) Personas e necessidades

### 6.1 Logística (Operação de estoque)

- Precisa saber rapidamente **onde está** e **quantos existem**.
- Precisa registrar entradas/saídas com o mínimo de atrito.
- Precisa de um “inbox” de tarefas e pendências que o sistema gera.

### 6.2 Operação (gestão de chamados)

- Precisa solicitar expedição/reversa com dados completos.
- Precisa visibilidade de disponibilidade antes de acionar logística.

### 6.3 Técnico de campo (estoque avançado)

- Precisa confirmar recebimento/uso/devolução com poucos cliques/WhatsApp.
- Precisa visibilidade do “seu” estoque e do que está pendente de reversa.

### 6.4 Financeiro/Fiscal

- Precisa consistência entre estoque operacional e registros fiscais.
- Precisa rastreabilidade e relatórios auditáveis (NF ↔ movimentos ↔ ativos).

### 6.5 Gestão / Direção

- Precisa KPIs: acuracidade, perdas, custo logístico, eficiência, SLA e tendências.

---

## 7) Glossário (termos do domínio)

- **Projeto:** unidade operacional que, na prática, funciona como “cliente/contrato” dentro do SGA.  
- **Cliente final:** o cliente atendido dentro de um projeto.  
- **Part Number (PN):** cadastro do item (modelo/tipo) — pode ou não exigir serial.  
- **Serial Number:** identificador individual do ativo.  
- **RFID / Etiqueta patrimonial:** identificadores físicos adicionais.  
- **Local (Base):** qualquer lugar onde estoque pode “existir” (CD, base técnica, self storage, service storage, casa do técnico).  
- **Depósito/Status fiscal:** classificação do estoque por tipo/propriedade/condição (ex.: Recebimento, BAD, Itens de terceiros).  
- **Movimentação:** evento que altera (ou reserva) saldo em um local e registra rastreabilidade.  
- **Reserva (Reservation):** separa saldo para um chamado antes de expedir.  
- **Staging:** separação física para expedição (área de preparação).  
- **Reversa:** processo de devolução/retorno do ativo ao estoque.

---

## 8) Modelo de domínio (o que existe no módulo)

> Não é um documento técnico de banco de dados; é o “mapa mental” do produto.

### 8.1 Entidades essenciais

1. **Item (Part Number)**
   - nome/descrição, grupo/categoria
   - controle por serial? (sim/não)
   - reversa obrigatória? (sim/não)
   - atributos obrigatórios por tipo (ex.: voltagem, versão, compatibilidade)

2. **Ativo (Asset)**
   - PN
   - serial (se aplicável)
   - RFID/etiqueta (opcional)
   - condição: novo / usado / BAD / descarte / quarentena / em manutenção
   - propriedade: Faiston / terceiro (cliente) / parceiro
   - projeto/cliente final associado (quando aplicável)
   - histórico (linha do tempo)

3. **Local de estoque (Location)**
   - tipo: Centro Logístico, Base Técnica, Self Storage, Service Storage, Técnico
   - capacidade/limitações (opcional)
   - políticas (ex.: “não pode receber terceiros”, “só estoque avançado”, etc.)

4. **Saldo (Stock Balance)**
   - por PN e/ou por ativo (serial)
   - por local
   - por condição (normal, BAD, etc.)
   - disponível vs reservado vs em trânsito (status)

5. **Movimentação (Stock Movement)**
   - tipo: entrada / saída / transferência / reversa / ajuste / reserva / cancelamento
   - origem e destino (quando aplicável)
   - vínculo com chamado (pai/filho) e projeto
   - evidências anexas (NF, comprovante, foto, etc.)
   - autor (humano ou agente) + “nível de autonomia”
   - confiança do sistema (score) + justificativa

6. **Documento**
   - NF, DANFE, XML (quando existir), comprovante, checklist, foto
   - metadados extraídos por IA (PN, serial, quantidades, valores)

---

## 9) Estados e regras do estoque

### 9.1 Estados do ativo (serializado)

- **EM_ESTOQUE (Disponível)**
- **RESERVADO**
- **EM_SEPARAÇÃO (Staging)**
- **EM_TRANSITO**
- **EM_USO (com técnico / em cliente)**
- **AGUARDANDO_REVERSA**
- **EM_REVERSA (postado/coletado)**
- **EM_MANUTENÇÃO**
- **BAD**
- **QUARENTENA (aguardando inspeção)**
- **DESCARTE**
- **EXTRAVIADO (apenas com aprovação e evidência)**

### 9.2 Tipos de movimentação (mínimo viável)

- **Internalização (Entrada):** NF/recebimento → estoque  
- **Expedição (Saída):** estoque → técnico/base/cliente  
- **Transferência:** base A → base B (ou técnico ↔ base)  
- **Reversa:** retorno → estoque (com ou sem triagem)  
- **Ajuste:** correções por inventário/auditoria (sempre com aprovação)  
- **Reserva/Desreserva:** bloqueio temporário para atendimento

---

## 10) Jornadas principais (end‑to‑end)

### Jornada A — Entrada de mercadoria (internalização)

**Gatilhos típicos**
- Chegada de NF por e‑mail / documento entregue junto do equipamento.
- Chegada de equipamento sem aviso (o sistema precisa suportar).

**Resultado esperado**
- Ativos cadastrados (PN/serial), saldo atualizado, e evidências anexadas.
- Caso falte dado crítico (ID/projeto), criar tarefa e bloquear avanço.

**Fluxo (alto nível)**
1. Usuário informa “chegou NF/equipamento” no portal *ou* encaminha a NF para um canal monitorado.
2. **Agente de Intake** lê NF (documento/voz), extrai PN, serial, RFID, quantidade, valores e sugere projeto/cliente final.
3. **Agente de Estoque** valida:
   - PN existe? se não, abre “tarefa de cadastro PN”.
   - serial duplicado? se sim, abre exceção.
   - projeto/ID existe? se não, solicita cadastro/validação.
4. **Human‑in‑the‑Loop** valida pontos obrigatórios (configurável por risco/confiança).
5. Sistema registra a entrada e atualiza o saldo.
6. Sistema registra “qualidade de dados” (confiança, evidências) para auditoria futura.

**Critérios de aceite**
- Entrada suporta item serializado e não‑serializado.
- Sistema impede entrada “sem projeto” quando regra exigir.
- Cada entrada gera movimento com evidências e trilha de auditoria.

---

### Jornada B — Consulta de disponibilidade e localização (o “Google do estoque”)

**Gatilho típico**
- Operação quer saber se existe peça para atender chamado.
- Logística precisa localizar onde está o item e quem está com ele.

**Resultado esperado**
- Busca por PN/serial retorna: saldo por local, estado, e recomendações.

**UX essencial**
- Busca unificada por:
  - PN (descrição, modelo, categoria),
  - serial/RFID/etiqueta,
  - projeto/cliente final,
  - local/base/técnico.

**Critérios de aceite**
- Retorno mostra “onde” e “status” (disponível/reservado/em trânsito/…).
- Retorno mostra evidência e histórico (para evitar “alucinação operacional”).

---

### Jornada C — Reserva e separação (pré‑expedição)

**Gatilhos típicos**
- Chamado filho de logística solicita item (ex.: AP, servidor, switch).
- Operação cria necessidade de peça e o sistema deve reservar.

**Resultado esperado**
- Item reservado e “pronto para separar”, evitando “duas pessoas pegarem o mesmo”.

**Fluxo (alto nível)**
1. Chega solicitação vinculada ao chamado (com PN ou requisitos).
2. **Agente de Alocação** recomenda:
   - melhor local de origem (custo/prazo),
   - alternativa se não houver no local preferido.
3. Sistema cria **reserva** do saldo (ou do serial específico).
4. Gera **lista de separação (pick list)** e tarefa para logística.
5. Ao confirmar separação, muda status para staging.

**Critérios de aceite**
- Reserva bloqueia duplicidade.
- Cancelamento do chamado desfaz reserva com trilha.

---

### Jornada D — Transferência entre bases e/ou técnicos

**Gatilhos típicos**
- Reposição de estoque avançado.
- Realocação por mudança de demanda.
- Pegar item “mais perto” do incidente (quando aplicável).

**Regras importantes**
- Transferência entre projetos/contratos pode exigir aprovação (policy).
- Toda transferência deve manter rastreabilidade.

**Critérios de aceite**
- Transferência altera saldos corretamente.
- Regras de aprovação são respeitadas (HIL).

---

### Jornada E — Reversa (retorno do ativo)

**Gatilhos típicos**
- Instalação gerou BAD e precisa retornar.
- Substituição de equipamento.
- Fim de uso / devolução de equipamento de terceiro.

**Resultado esperado**
- Sistema sabe “o que deveria voltar”, “o que voltou”, e atualiza saldo/condição.

**Fluxo (alto nível)**
1. Chamado / regra define reversa obrigatória.
2. Sistema cria pendência: “ativo X precisa retornar”.
3. Técnico confirma status (WhatsApp/app) e posta/coleta.
4. Ao receber, logística faz triagem (condição) e atualiza estado.
5. Divergências viram exceções (ex.: serial diferente, item faltante).

**Critérios de aceite**
- Reversa cria e fecha o ciclo no estoque com rastreabilidade.

---

### Jornada F — Inventário e auditoria (cycle count AI‑assisted)

**Gatilhos típicos**
- Ciclo mensal, auditoria contratual, ou divergência detectada por IA.

**Resultado esperado**
- Sistema propõe contagem, identifica divergências e sugere ajustes (com HIL).

**Fluxo (alto nível)**
1. Sistema sugere um “roteiro de contagem” por risco/valor/atividade.
2. Usuário registra contagem (mobile/portal) e anexa evidências (fotos).
3. **Agente de Reconciliação** compara:
   - saldo esperado vs contado,
   - padrões históricos,
   - possíveis causas (erro de entrada, expedição sem baixa, extravio).
4. Sistema gera proposta de ajuste + justificativa + risco.
5. Humano aprova ou rejeita.

**Critérios de aceite**
- Ajuste não ocorre sem aprovação.
- Divergências ficam rastreáveis com causa provável.

---

## 11) Requisitos funcionais (detalhados)

### RF‑01 — Cadastro de Part Number (PN)

**Descrição**  
Permitir criar e manter o catálogo de itens (PN) com atributos mínimos e regras de controle.

**Campos mínimos**
- Tipo (produto), grupo/categoria (se aplicável)
- Controle por serial (sim/não)
- Reversa obrigatória (sim/não)
- Nome/descrição e tags

**Regras**
- Se “controle por serial = sim”, sistema exige serial em entradas e saídas.
- PN pode ter “atributos obrigatórios” configuráveis (por cliente/projeto).

**Critérios de aceite**
- Não permite movimentar item serializado sem serial.
- Log de alteração de PN (quem alterou, antes/depois).

---

### RF‑02 — Cadastro e rastreio de ativos (serializados)

**Descrição**  
Permitir registrar ativos individualmente com serial e histórico.

**Regras**
- Serial deve ser único por PN (ou global, conforme regra).
- Identificadores alternativos (RFID/etiqueta) podem existir, mas serial domina.

**Critérios de aceite**
- Busca por serial retorna a “linha do tempo” do ativo.
- Movimentos do serial atualizam seu estado automaticamente.

---

### RF‑03 — Estrutura de locais (bases, técnicos, storage)

**Descrição**  
Cadastrar locais e tratá‑los como nós de estoque.

**Tipos suportados**
- Centro Logístico
- Base Técnica
- Self Storage
- Service Storage (local com “chave” e acesso controlado)
- Técnico (estoque avançado individual)

**Regras**
- Local pode ser associado a um projeto/cliente (quando houver segregação).
- Local pode ter políticas: “pode receber terceiros”, “somente BAD”, etc.

**Critérios de aceite**
- Consulta mostra saldo por local e por tipo.
- Transferência entre locais respeita políticas.

---

### RF‑04 — Movimentações (+/–) com trilha e evidência

**Descrição**  
Registrar e automatizar movimentações de estoque com evidência.

**Movimentos suportados**
- Entrada (internalização)
- Saída (expedição/uso)
- Transferência
- Reversa (entrada/saída)
- Reserva / cancelamento
- Ajuste (sempre com HIL)

**Regras**
- Toda movimentação deve ter:
  - projeto,
  - tipo,
  - origem/destino (quando aplicável),
  - evidência mínima (configurável),
  - autor (humano/agente) + nível de autonomia.
- Movimentação pode ser “pendente” até evidência ficar completa.

**Critérios de aceite**
- Movimentos alteram saldo e estados corretamente.
- É possível auditar: “o que mudou, quando, por quê e por quem”.

---

### RF‑05 — Saldo por base/técnico/projeto (visão operacional)

**Descrição**  
Exibir saldo consolidado e segmentado.

**Visões mínimas**
- Por projeto (cliente)
- Por local (base/técnico)
- Por estado (disponível, reservado, em trânsito, BAD, etc.)
- Por criticidade (itens críticos, alto valor)

**Critérios de aceite**
- Exportar visão (CSV/PDF) para auditoria quando necessário.
- Filtros rápidos (projeto, PN, local, estado).

---

### RF‑06 — Entrada por voz / leitura de NF (AI‑First)

**Descrição**  
Substituir digitação por captura inteligente: o usuário “lê” a NF (ou envia o PDF) e o sistema preenche.

**Regras**
- O sistema deve:
  - extrair PN, quantidades, valores, serial (se existir), NF e dados relevantes,
  - sugerir projeto/cliente final,
  - indicar campos incertos e pedir confirmação.
- Deve existir “modo aprendizado” com correções do usuário.

**Critérios de aceite**
- Usuário consegue completar uma entrada sem digitar campos principais.
- Correções alimentam memória/treino (ex.: fornecedor X sempre usa layout Y).

---

### RF‑07 — Detecção de divergências e auditoria (AI)

**Descrição**  
Detectar automaticamente sinais de divergência e abrir tarefas.

**Exemplos de divergência**
- Serial aparece em dois locais ao mesmo tempo.
- Saída sem evidência de expedição.
- Reversa prevista não ocorreu no prazo.
- Saldo negativo em algum local.
- Mudança brusca fora do padrão (picos de consumo).

**Critérios de aceite**
- Divergências geram alerta/tarefa com contexto e recomendação.
- Ajuste de saldo só ocorre com HIL.

---

### RF‑08 — Integração conceitual com chamados (Tiflux)

**Descrição**  
Cada movimentação relevante precisa estar vinculada a um chamado (pai/filho) quando existir.

**Regras**
- O módulo deve suportar:
  - referência do chamado (ID) e do projeto,
  - múltiplos movimentos por chamado,
  - “chamado filho” para logística quando não há peça em bases/estoque avançado (via processo de operação).

**Critérios de aceite**
- Do ativo, consigo ver “quais chamados ele serviu”.
- Do chamado, consigo ver “quais ativos foram movimentados”.

---

### RF‑09 — Permissões, auditoria e rastreabilidade

**Descrição**  
Garantir controle de acesso e logs completos.

**Papéis mínimos**
- Admin
- Logística
- Operação
- Técnico
- Financeiro/Fiscal
- Leitura (gestão/auditoria)

**Critérios de aceite**
- Ação sensível (ajuste, descarte, transferência restrita) exige papel/aprovação.
- Log mostra usuário/agente, data/hora, e dados alterados.

---

## 12) Agentes do módulo (Observa → Pensa → Aprende → Executa)

> O módulo é “AI‑First”: agentes não são enfeite; são o motor do fluxo.

### 12.1 Agent — Controle de Estoque (+/–) (core)

**Observa**
- eventos de chamado (solicitação de peça, atualização, encerramento)
- eventos de expedição/reversa (quando existirem)
- entradas de NF / documentos / confirmações
- contagens de inventário

**Pensa**
- qual movimentação deve ocorrer?
- existe evidência suficiente?
- qual é o risco? precisa HIL?
- há inconsistência com histórico?

**Aprende**
- quando humanos corrigem uma sugestão, registra:
  - regra corrigida,
  - exceção por projeto,
  - padrão de fornecedor.

**Executa**
- cria/reserva/baixa/transferência conforme nível de autonomia
- cria tarefas para logística/financeiro quando faltam dados
- registra log e justificativa

---

### 12.2 Agent — Intake (NF/Documentos por voz/PDF)

**Observa**
- uploads, e‑mails monitorados, gravações por voz, anexos.

**Pensa**
- extrair campos, validar consistência (PN x serial x qty),
- estimar confiança por campo,
- sugerir projeto e depósito/status.

**Aprende**
- templates por fornecedor,
- correções recorrentes (ex.: “PN vem no campo X”).

**Executa**
- pré‑preenche cadastro de entrada,
- sinaliza campos incertos e abre revisão.

---

### 12.3 Agent — Reconciliação (SAP/planilhas/inventário)

**Observa**
- exportações, relatórios e contagens,
- divergências recorrentes.

**Pensa**
- onde está a diferença?
- qual causa provável (movimento faltante, erro de serial, etc.)?

**Aprende**
- padrões por projeto/base,
- sazonalidade de divergência.

**Executa**
- propõe ajustes (sempre com HIL),
- cria tarefas de investigação.

---

### 12.4 Agent — Compliance (políticas e contratos)

**Observa**
- transferências sensíveis,
- ajustes, descartes, “extraviados”,
- movimentações entre projetos.

**Pensa**
- está permitido?
- precisa de aprovação de qual papel?

**Aprende**
- exceções contratuais por projeto,
- perfis de risco.

**Executa**
- bloqueia, solicita aprovação e registra justificativa.

---

### 12.5 Agent — Comunicação com técnicos (WhatsApp / app)

**Observa**
- pendências de confirmação e reversa,
- eventos críticos (atrasos, item errado, etc.)

**Pensa**
- quem contatar?
- qual mensagem, com qual contexto?

**Aprende**
- padrões de resposta por técnico,
- melhores horários/canais.

**Executa**
- envia mensagens e coleta confirmações (com registro).

---

## 13) Matriz Human‑in‑the‑Loop (HIL)

| Ação | Autonomia padrão | Exceções |
|---|---:|---|
| Criar PN novo | HIL | Autônomo só se categoria já existir e risco baixo |
| Entrada por NF com alta confiança | Executa com revisão | HIL se valor alto ou serial crítico |
| Reserva por chamado | Autônomo | HIL se transferir entre projetos |
| Transferência entre bases do mesmo projeto | Autônomo | HIL se “local restrito” ou “estoque de terceiros” |
| Ajuste de inventário | HIL obrigatório | Nunca autônomo |
| Descarte / extravio | HIL obrigatório | Nunca autônomo |

---

## 14) Experiência do usuário (UI/UX) — requisitos mínimos

### 14.1 “Inbox” de tarefas (operacional)

Um painel único onde o usuário vê:
- entradas pendentes (NF lida, faltou confirmar)
- divergências detectadas
- reservas a separar (pick list)
- reversas atrasadas
- solicitações de aprovação (HIL)

### 14.2 Busca unificada + Copiloto (“Sasha”)

- Campo de busca universal + modo chat:
  - “Onde está o serial X?”
  - “Quantos switches PN Y existem em RJ e DF?”
  - “Quais reversas estão pendentes há mais de 5 dias?”

Respostas devem incluir:
- números + locais,
- status,
- “por que o sistema acha isso” (evidência/histórico).

### 14.3 Mobile/PWA (mínimo viável)

- Confirmar recebimento / uso / devolução (técnicos).
- Scanner (câmera) para serial/QR (se adotado).
- Checklist rápido de inventário.

---

## 15) Relatórios mínimos (dentro do módulo)

Mesmo antes do “Módulo de Dashboards” completo, o estoque precisa ter:

- Saldo por projeto e por local (com filtros).
- Itens críticos abaixo do mínimo (quando definido).
- Pendências de reversa (por técnico/projeto).
- Divergências e ajustes (histórico).
- Linha do tempo por ativo (serial).

---

## 16) Migração e transição do legado (produto)

### 16.1 Estratégia

- Importar planilhas atuais como “estado inicial”, mas marcando **qualidade/certeza**.
- Rodar um período de convivência onde:
  - o sistema sugere correções,
  - humanos confirmam,
  - e a confiança cresce.
- Substituir gradualmente o uso de planilhas por:
  - consulta no portal,
  - inbox de tarefas,
  - automações por agente.

### 16.2 Requisitos de migração (produto)

- Importação deve aceitar diferentes “esquemas” de planilha.
- Sistema deve mapear colunas para campos, com sugestão por IA.
- Deve haver relatório de “campos faltantes” e “possíveis duplicidades”.

---

## 17) Riscos e mitigação

- **Risco:** dados históricos inconsistentes → *Mitigação:* marcar confiança, não automatizar ajustes sem HIL, reconciliação assistida.  
- **Risco:** agente executar movimento errado → *Mitigação:* níveis de autonomia, evidência mínima, rollback e auditoria.  
- **Risco:** regras contratuais não codificadas → *Mitigação:* Compliance Agent + política configurável por projeto.  
- **Risco:** baixa adesão do técnico → *Mitigação:* UX mínima (WhatsApp), mensagens contextualizadas, redução de esforço.

---

## 18) Dependências

- Integração/orquestração de eventos (MCP Core) para ligar chamados ↔ estoque.  
- Catálogo de usuários e permissões (Admin).  
- Acesso a evidências (NF, anexos, fotos) e políticas de retenção.  
- Definição (mesmo que incremental) de:
  - tipos de estoque/locais,
  - atributos obrigatórios por projeto,
  - regras de transferência entre projetos,
  - itens críticos e mínimos (quando aplicável).

---

## 19) Critérios de sucesso do MVP (checklist)

- ✅ Conseguir registrar entrada/saída/transferência com trilha e evidência.  
- ✅ Conseguir consultar saldo por base/técnico/projeto em tempo real.  
- ✅ Conseguir rastrear um serial do recebimento até a saída e retorno (quando houver).  
- ✅ Conseguir operar estoque avançado (técnico como “local”) com confirmações simples.  
- ✅ Conseguir detectar divergências básicas e criar tarefas.  
- ✅ Conseguir fazer entrada por voz/PDF (com HIL) sem digitação pesada.

---

## Apêndice A — Exemplos de cenários (para testes de aceitação)

1. **Entrada serializada**: chegam 10 APs com serial; 2 seriais duplicados → sistema bloqueia e abre exceção.  
2. **Entrada não‑serializada**: chegam 50 cabos; saldo aumenta e fica disponível.  
3. **Reserva por chamado**: operação abre chamado filho pedindo 1 switch; sistema reserva e cria pick list.  
4. **Transferência para técnico**: repor estoque avançado em DF; sistema transfere e pede confirmação do técnico no recebimento.  
5. **Reversa obrigatória**: ativo usado deve voltar; técnico não posta em 5 dias → sistema alerta e escala.  
6. **Inventário**: contagem física difere; sistema propõe ajuste e pede aprovação.



---

## Apêndice B — Catálogo inicial de “Locais/Estoques” (exemplo para parametrização)

> **Objetivo:** já começar o módulo com um *starter pack* de locais que espelha a operação real.  
> **Observação:** nomes abaixo são exemplos e podem/Devem ser normalizados (ID único + apelido).  
> **Produto:** o SGA 2.0 deve permitir que **Projeto** e **Local** sejam relacionados, mas não sejam a mesma coisa (para evitar confusão quando um projeto tiver múltiplas bases).

### B.1 Estoques por Projeto/Cliente (exemplos)
- NTT – Arcos Dourados  
- NTT – Necxt  
- NTT – IPB  
- NTT – KONAMI  
- NTT – NTT_ROUTERLINK  
- FAISTON  
- IMAGINARIUM  
- IDM  
- ITAÚ  
- Linker  
- MADERO  
- MDS  
- ONETRUST  
- PORTO SEGURO  
- RENNER  
- SEM PARAR  
- SODEXO  
- SUL AMÉRICA  
- ZAMP  
- SYNGENTA  
- Unimed Nacional  
- BACKUP  

### B.2 Bases Técnicas (exemplos)
- NTT – Montes Claros  
- NTT – Rio do Sul  
- NTT – Ponta Grossa  
- NTT – Ponta Porã  
- NTT – Araraquara  
- NTT – Itajaí  
- NTT – Taubaté  
- NTT – Três Lagoas  
- NTT – Araçatuba  
- NTT – Caruaru  
- NTT – Marabá  
- NTT – Vitória da Conquista  
- NTT – Uruguaiana  

### B.3 Self Storage (exemplos)
- Self Storage – MG  
- Self Storage – SC  

### B.4 Service Storage (exemplos)
- NTT – Santander SP  
- NTT – Santander BV  
- NTT – Santander BSB  

---

## Apêndice C — Modelos de dados (exemplos de 10 ativos/linhas)

> **Nota:** exemplos fictícios (para alinhar campos e telas). Substituir por 5–10 itens reais assim que a operação enviar.

| asset_id | part_number | serial | projeto | cliente_final | local_atual | tipo_local | condição | status | propriedade |
|---|---|---|---|---|---|---|---|---|---|
| AST-0001 | SW-CISCO-C9200-24T | FOC1234A1B2 | NTT_ROUTERLINK | NTT | Barueri-CD | Centro Logístico | Novo | EM_ESTOQUE | Faiston |
| AST-0002 | AP-ARUBA-515 | CNF9KX1234 | NTT – Arcos Dourados | Arcos Dourados | NTT – Taubaté | Base Técnica | Usado | EM_USO | Terceiro |
| AST-0003 | SSD-1TB-SATA | (n/a) | FAISTON | Interno | Barueri-CD | Centro Logístico | Novo | EM_ESTOQUE | Faiston |
| AST-0004 | NOTE-DELL-5430 | 7H2K9L1 | ITAÚ | Itaú | Técnico: João Silva | Técnico | Usado | EM_USO | Terceiro |
| AST-0005 | SWITCH-HP-1920 | HPX1920ZZ9 | NTT – Necxt | Necxt | Em trânsito (Gollog) | Em trânsito | Usado | EM_TRANSITO | Terceiro |
| AST-0006 | ROUTER-MIKROTIK-RB4011 | MKT4011A77 | ZAMP | Zamp | BAD – Barueri | Centro Logístico | BAD | BAD | Terceiro |
| AST-0007 | AP-UBIQUITI-U6-LR | U6LR00991 | PORTO SEGURO | Porto | Service Storage – Santander SP | Service Storage | Novo | EM_ESTOQUE | Faiston |
| AST-0008 | UPS-APC-1500VA | APC15K8890 | MADERO | Madero | Self Storage – MG | Self Storage | Usado | EM_ESTOQUE | Terceiro |
| AST-0009 | SERVER-DELL-R640 | R640SN0008 | ONETRUST | OneTrust | Barueri-CD (Staging) | Centro Logístico | Usado | EM_SEPARAÇÃO | Faiston |
| AST-0010 | SWITCH-CISCO-2960X | FCW2960X22 | NTT – IPB | IPB | NTT – Ponta Grossa | Base Técnica | Usado | AGUARDANDO_REVERSA | Terceiro |

---

## Apêndice D — Campos mínimos de uma movimentação (checklist de produto)

**Uma movimentação só é “válida” quando tiver:**
- Tipo de movimentação (entrada/saída/transferência/reversa/ajuste/reserva)
- Projeto (e, quando aplicável, cliente final)
- Origem e destino (ou “origem = externo” em entradas; “destino = externo” em saídas)
- PN e/ou serial (conforme regra do PN)
- Quantidade (para não‑serializados)
- Evidência mínima (anexo, referência, confirmação, etc.)
- Referência de chamado (quando existir)
- Autor e modo de execução:
  - humano (nome/usuário),
  - ou agente (nome do agente + autonomia A/B/C)
- Carimbo de data/hora + trilha de auditoria

