# Bezura | Painel de Lembretes (n8n + WhatsApp)

Aplicação para gerenciamento de lembretes recorrentes com disparo automatizado via n8n, suportando envio por API oficial e não oficial, com painel web para cadastro, edição, pausa e exclusão.

## Visão Geral

Este repositório concentra:

- Frontend web de gerenciamento de lembretes em `web/modal/index.html`.
- Infraestrutura de deploy em VPS com Docker + Traefik em `infra/`.
- Workflow n8n de orquestração de lembretes (persistido no n8n, não em arquivo versionado).
- Scripts auxiliares para patch/validação de workflow n8n em `infra/scripts/`.

Objetivo operacional:

- Permitir ao usuário final agendar lembretes com data/hora e recorrência.
- Garantir envio no horário correto.
- Evitar reenvio indevido (principalmente recorrência "uma vez").
- Suportar múltiplas origens de envio (oficial e não oficial).

## Arquitetura Atual

### 1) Frontend (Painel de Lembretes)

Arquivo principal: `web/modal/index.html`

Responsabilidades:

- Login funcional por `id_cliente` e token já cadastrado no backend n8n.
- Cadastro e edição de lembretes.
- Definição de recorrência:
  - `once` (uma vez)
  - `daily`
  - `weekly` (com `dias_semana`)
  - `monthly` (com `intervalo_mes` e `dia_mes`)
- Listagem com filtros e ações:
  - editar
  - pausar/ativar
  - excluir
- UX aprimorada:
  - badges de status/canal
  - recorrência humanizada
  - próximo envio com indicação relativa
  - melhor aproveitamento horizontal da tela

### 2) Workflow n8n (Orquestração de Envio)

Workflow em produção (n8n cloud/self-hosted):

- ID: `2WHEl44lXMUN4DHE`
- Nome: `Lembretes_Bezura` (ou equivalente no ambiente)

Fluxo principal:

1. `Acionador` (schedule, 1 min)
2. `Lembretes_Bezura` (leitura Data Table de lembretes)
3. `Enriquecer_Tipo_API` (normalização de dados e tipo de API)
4. `Filtrar_Envio_Agora` (janela estrita de disparo)
5. `Rotear_API_Envio` (oficial x não oficial)
6. `Buscar_Token_Envio` + `Merge_Envio_Com_Token` (ramo oficial)
7. `Envio_Lembrete` (oficial, endpoint Helena)
8. `Envio_Lembrete_NaoOficial` (não oficial)
9. `Calcular_Proxima_Recorrencia`
10. `Pos_Envio_Status` (update determinístico em Data Table)

### 3) Infra (Docker + Traefik)

Arquivo principal: `infra/docker-compose.vps.yml`

- Serviço Nginx para publicação do frontend.
- Labels Traefik para roteamento por host (`apps.logzap.com.br` e `cadastro.bezura.com.br` apontam para o mesmo container).
- URL pública do painel: **https://apps.logzap.com.br/** (raiz do site; `/modal/` continua válido para compatibilidade).
- Montagem de `web/modal` e assets no container.

### 4) Deploy CI/CD

Workflow GitHub Actions: `.github/workflows/deploy.yml`

- Trigger: push em `main`
- Ação:
  - SSH na VPS
  - `git pull origin main`
  - `docker compose -f infra/docker-compose.vps.yml up -d --build`

## Regras Críticas de Disparo

As regras abaixo foram implementadas para evitar disparos indevidos:

### Janela de envio

No nó `Filtrar_Envio_Agora`:

- Só envia se `status = Ativo`.
- Só envia dentro da janela do minuto agendado:
  - `now >= ts`
  - `now < ts + 60s`

Isso evita:

- envio atrasado acumulado,
- disparo fora da data/hora definida.

### Recorrência

No pós-envio:

- `once` -> marca `status = Enviado`.
- `daily` -> avança para próximo dia.
- `weekly` -> calcula próxima data com base em `dias_semana`.
- `monthly` -> calcula próximo mês com `intervalo_mes` e `dia_mes`.

### Persistência pós-envio

No nó `Pos_Envio_Status` (Data Table update):

- Atualiza `status`, `data` e `hora`.
- Match por `id_cliente + mensagem` (mensagem com RID), para atualização determinística de 1 registro.

## Endpoints de Envio

### Oficial (Helena)

- Endpoint: `POST https://api.helena.run/chat/v1/send/text`
- Body esperado:
  - `text`
  - `to`
  - `from`
  - `options`

### Não oficial

- Endpoint: `POST https://api.wts.chat/chat/v1/message/send`
- Body no formato do provider não oficial.

## Data Model (n8n Data Tables)

Campos relevantes de lembretes:

- `id_cliente`
- `nome`
- `origem` (`oficial::...` ou `nao_oficial::...`)
- `ddi`
- `destino` (ou `Telefone_Destino`, conforme legado)
- `data`
- `hora`
- `recorrencia`
- `dias_semana`
- `intervalo_mes`
- `dia_mes`
- `mensagem` (com RID para unicidade)
- `status` (`Ativo`, `Pausado`, `Enviado`, `Excluido`)

## Scripts de Manutenção

### Patch de merge/conexões no n8n

Arquivo: `infra/scripts/n8n_patch_lembretes_merge.py`

Uso:

```bash
export N8N_API_KEY="<sua_chave>"
export N8N_BASE_URL="https://n8n.bezura.cloud"
python3 infra/scripts/n8n_patch_lembretes_merge.py
```

Dry-run local:

```bash
python3 infra/scripts/n8n_patch_lembretes_merge.py --dry-run
```

Teste unitário associado:

```bash
python3 -m unittest tests.test_n8n_merge_patch -v
```

## Execução Local

Como o frontend é estático:

```bash
python3 -m http.server 8080
```

Acesse:

- `http://localhost:8080/web/modal/`

## Deploy em Produção

### Manual na VPS

```bash
cd /home/vinicius/avisos-bezura
git pull origin main
docker compose -f infra/docker-compose.vps.yml up -d --build
```

### Via GitHub Actions

- Faça push na branch `main`.
- O workflow `.github/workflows/deploy.yml` executará o deploy remoto.

## Estrutura do Repositório

```text
.
├── .github/workflows/deploy.yml
├── api/
│   ├── package.json
│   └── server.js
├── docs/
├── infra/
│   ├── docker-compose.vps.yml
│   ├── nginx/
│   └── scripts/
│       └── n8n_patch_lembretes_merge.py
├── tests/
│   ├── fixtures/n8n_lembretes_merge_minimal.json
│   └── test_n8n_merge_patch.py
└── web/
    ├── avisos-recorrente.png
    └── modal/index.html
```

## Segurança Operacional

- Nunca versionar tokens/chaves reais.
- Não expor `N8N_API_KEY` em chats, issues ou commits.
- Rotacionar credenciais ao menor sinal de exposição.
- Manter validação de entrada no frontend e no n8n.
- Monitorar falhas de envio (`failedReason` / `statusUrl` quando disponível).

## Troubleshooting Rápido

### "Envia a cada minuto mesmo sendo uma vez"

Verificar:

1. `Filtrar_Envio_Agora` com janela estrita de 60s.
2. `Pos_Envio_Status` atualizando `status` para `Enviado` em `once`.
3. Match determinístico por `id_cliente + mensagem`.

### "Não envia no oficial"

Verificar:

1. Endpoint oficial `send/text`.
2. Payload com `text` na raiz.
3. `Authorization: Bearer <Token_API>`.
4. `from`/`to` somente dígitos válidos.

### "Merge com erro de fields to match"

No `Merge_Envio_Com_Token`:

- `mode = combine`
- `combineBy = combineByPosition`

## Notas sobre `api/`

A pasta `api/` contém serviço Node.js de outro fluxo de negócio (ingestão de lead/webhook seguro), preservado no repositório por histórico. O produto principal deste projeto, hoje, é o painel de lembretes + workflow n8n.

## Licença

Uso interno/proprietário.
