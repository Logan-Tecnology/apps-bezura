# 🚀 Logan Technology | Formulário de Cadastro

Landing page de cadastro rápido orientada a conversão, com validações de dados, enriquecimento automático (CPF/CNPJ e CEP), **API Node.js segura** para intermediação e envio para n8n, além de redirecionamento para WhatsApp.

## 📌 Etapas resumidas do projeto (SDLC)

1. **Planejamento e requisitos**  
   Definição do objetivo de negócio (captação de leads qualificados), campos obrigatórios e integrações (n8n + WhatsApp).
2. **Projeto e arquitetura**  
   Escolha de arquitetura simples e performática: frontend estático (`HTML + CSS + JS`) para reduzir latência e pontos de falha.
3. **Implementação**  
   Construção do formulário, máscaras, validações locais e integrações com APIs externas (BrasilAPI e ViaCEP).
4. **Testes e validação**  
   Testes de fluxo feliz/erro: CPF/CNPJ, CEP, telefone por país, fallback de API indisponível e envio do webhook.
5. **Deploy e operação**  
   Publicação em ambiente web com proxy reverso, monitoramento básico de disponibilidade e versão explícita no rodapé.
6. **Evolução contínua**  
   Incrementos de UX, robustez de validação e versionamento semântico para rastreabilidade de releases.

## 🧩 Visão geral da solução

- **Objetivo:** coletar dados completos do lead para orçamento comercial.
- **Entrada:** CPF/CNPJ, nome, e-mail, telefone, CEP (ou endereço manual se o lead marcar **Não sei o CEP**) e endereço completo quando aplicável.
- **Saída:** payload estruturado enviado primeiro para a API segura (`POST /lead`) e depois para o webhook n8n.
- **Resiliência:** mesmo com falha no webhook, o fluxo segue para WhatsApp para não perder conversão.

## 🏗️ Arquitetura

- **Frontend:** página única estática em `web/index.html`.
- **Backend:** API Node.js (`Express`) em `api/server.js`.
- **Integrações externas:**
  - **BrasilAPI** para validação de CNPJ e sugestão de dados (`/api/cnpj/v1/{cnpj}`).
  - **ViaCEP** para consulta e sugestão de endereço (`/ws/{cep}/json/`).
  - **Webhook n8n** consumido apenas pelo backend seguro.
  - **WhatsApp** para continuidade do atendimento comercial.

## 🧭 Como foi feito (passo a passo técnico)

1. **Front-end estático de alta performance**
   - Construção de página única em `web/index.html` (sem framework) para reduzir tempo de carregamento e simplificar deploy.
   - Implementação de máscaras e validações client-side para CPF/CNPJ, telefone internacional e CEP.

2. **Enriquecimento de dados no navegador**
   - Integração com BrasilAPI para validação de CNPJ e sugestão de contato.
   - Integração com ViaCEP para sugestão automática de endereço a partir do CEP.
   - Opção **Não sei o CEP** para abrir imediatamente o preenchimento manual de endereço.
   - Fallback para preenchimento manual quando APIs externas falham.

3. **Camada segura de backend (`POST /lead`)**
   - Criação de API Node.js com `Express`.
   - Hardening com `helmet` e proteção anti-abuso com `express-rate-limit`.
   - Validação de schema com `zod` antes de processar qualquer requisição.

4. **Regra de negócio para não duplicar cliente**
   - Antes de enviar ao n8n, o backend consulta a API de clientes por documento.
   - Se já existir CPF/CNPJ cadastrado, retorna `409` (`CLIENT_ALREADY_EXISTS`) e bloqueia o envio.

5. **Orquestração no n8n para cadastro final**
   - Workflow recebe payload já validado.
   - Mapeamento com `Edit Fields`.
   - Consulta de cidades por UF para tentar resolver `cidade_id`.
   - Fallback inteligente (exato, parcial, prefixo e similaridade) para melhorar a resolução.
   - Envio final para `POST /clientes` da API Betel.

6. **Deploy em VPS com Docker + Traefik**
   - Stack com frontend (Nginx) e API no mesmo host (`cadastro.bezura.com.br`), com prioridade de rota maior para `/lead` no backend.
   - Rede Docker externa **`proxy`** (a mesma à qual o Traefik está anexado) e certificados TLS via resolver **`letsencrypt`** nas labels do compose.
   - Segredos apenas em `api/.env` no servidor (nunca no frontend).
   - Publicação: `git pull` no diretório do projeto + `docker compose -f infra/docker-compose.vps.yml up -d --build`.

## 🛠️ Tecnologias utilizadas

- `HTML5`
- `CSS3` (layout responsivo, animações e microinterações)
- `JavaScript` (vanilla, sem frameworks)
- `Fetch API` + `AbortController`
- `Node.js` + `Express`
- `Helmet`
- `express-rate-limit`
- `Zod`
- `dotenv`

## 📦 Dependências

Dependências de backend:

- `express`
- `helmet`
- `express-rate-limit`
- `zod`
- `dotenv`

Dependências de runtime externo via HTTP:

- [BrasilAPI](https://brasilapi.com.br/)
- [ViaCEP](https://viacep.com.br/)
- [n8n](https://n8n.io/)
- [WhatsApp Click-to-Chat](https://faq.whatsapp.com/5913398998672934)

## 🔄 Fluxo funcional

1. Usuário preenche documento (CPF/CNPJ).
2. Sistema aplica máscara e validação local.
3. Para CNPJ válido, consulta BrasilAPI e sugere nome/e-mail/telefone quando disponível.
4. Usuário informa CEP **ou** marca **Não sei o CEP** (campo desabilitado, endereço preenchido manualmente).
5. Com CEP válido, o sistema consulta ViaCEP e sugere endereço; sem CEP, o envio usa o texto `Não informado` no campo `cep` e exige rua, número, bairro, cidade e UF.
6. Formulário valida campos obrigatórios conforme o modo escolhido.
7. Payload é enviado para `POST /lead` (API segura).
8. API valida schema, aplica rate-limit e anexa header secreto para o n8n.
9. API repassa payload ao webhook n8n.
10. Usuário é redirecionado para WhatsApp com mensagem estruturada.

## 🧪 Regras de validação implementadas

- CPF e CNPJ com validação de dígitos verificadores.
- Rejeição de documentos com dígitos repetidos.
- Telefone validado por país (`BR`, `PT`, `US`, `AR`).
- CEP com 8 dígitos e máscara `00000-000`, exceto quando **Não sei o CEP** estiver marcado (payload com `cep: "Não informado"`).
- Com CEP normal: endereço mínimo rua, bairro, cidade e UF (com complemento ViaCEP quando possível).
- Sem CEP (modo manual): obrigatórios rua, **número**, bairro, cidade e UF.
- Timeout de 5s na consulta ViaCEP com fallback para preenchimento manual.

## 🔐 Boas práticas aplicadas

- Validação no cliente para reduzir tráfego inválido.
- Validação server-side com schema (`Zod`).
- `Helmet` para hardening básico de headers.
- Rate limit por IP no endpoint de entrada (`/lead`).
- Fallback de integração para não bloquear o funil comercial.
- Payload consistente e com `submittedAt` em ISO-8601.
- Estrutura simples para reduzir superfície de erro operacional.

> Observação: para ambiente B2B, recomenda-se complementar com validação/sanitização no backend, rate limiting e observabilidade de webhook.

## ⚙️ Configuração

No frontend:

- `WEBHOOK_URL`: endpoint interno `/lead`.
- `WHATSAPP_BASE_URL`: número destino do atendimento.

No backend (`api/.env` — use `api/.env.example` como modelo):

- `PORT`: porta interna da API (ex.: `3000`)
- `N8N_WEBHOOK_URL`: URL do webhook de ingestão no n8n
- `N8N_WEBHOOK_TOKEN`: segredo enviado no header `x-webhook-token`
- `BETEL_ACCESS_TOKEN` / `BETEL_SECRET_ACCESS_TOKEN`: credenciais da API Betel para checagem de duplicidade por documento antes do webhook

## 🚀 Execução local

Como é estático, você pode abrir diretamente no navegador:

```bash
xdg-open web/index.html
```

Ou servir com um servidor HTTP simples:

```bash
python3 -m http.server 8080
```

Depois acesse `http://localhost:8080/web/`.

## 🌐 Deploy em produção (VPS)

Domínio público: **`cadastro.bezura.com.br`**.

### Diretório e Git na VPS (ex.: Hetzner)

O deploy de referência usa o clone em **`/opt/form-bezura`**. Atualização típica:

```bash
cd /opt/form-bezura
git pull --ff-only
cd infra
docker compose -f docker-compose.vps.yml up -d --build
```

O `docker-compose.vps.yml` monta `web/index.html` e assets no container Nginx e constrói a imagem da API a partir de `api/`. É necessário existir **`api/.env`** no servidor (não versionado).

### Traefik

- Rede externa: **`proxy`** (o stack do cadastro precisa estar na mesma rede que o Traefik).
- Labels usam `traefik.docker.network=proxy` e `tls.certresolver=letsencrypt` (ajuste se o seu Traefik usar outros nomes).

### DNS (importante)

O registro **A** (ou **CNAME**) de **`cadastro.bezura.com.br`** deve apontar para o **mesmo servidor** onde os containers `cadastro-site` e `cadastro-api` estão rodando. Se o DNS continuar apontando para outro IP (hospedagem antiga), o navegador exibirá uma versão antiga do HTML (por exemplo rodapé `v1.3.0`) mesmo com o repositório já em `v1.4.0` na VPS correta. Após alterar DNS, purgue cache se usar proxy CDN (ex.: Cloudflare).

### Acesso Git via SSH na VPS

Se **deploy keys** estiverem desabilitadas no repositório GitHub, use uma chave SSH dedicada na VPS e registro na conta com acesso ao org/repo, ou habilite deploy key read-only no repositório. Host alias sugerido em `~/.ssh/config`: `github.com-form-bezura` com `IdentityFile` apontando para a chave da VPS.

## 🗂️ Estrutura do repositório

```text
.
├── api
│   ├── .env.example
│   ├── Dockerfile
│   ├── package.json
│   └── server.js
├── infra
│   └── docker-compose.vps.yml
├── web
│   ├── index.html
│   ├── logan-logo.png
│   └── logan-technology-logomarca-.png
└── README.md
```

## 🏷️ Versionamento

Este projeto adota **SemVer** (`MAJOR.MINOR.PATCH`):

- **MAJOR**: mudanças incompatíveis de contrato/fluxo.
- **MINOR**: novas funcionalidades compatíveis.
- **PATCH**: correções sem mudança funcional relevante.

### 📍 Versão atual

- **Formulário/API:** `v1.4.1` (rodapé e chave de rascunho `localStorage` alinhadas).
- Inclui opção **Não sei o CEP**, validação de `cep` no backend para CEP numérico ou texto `Não informado`, e compose Traefik alinhado à rede **`proxy`** + **`letsencrypt`**.

## 📝 Histórico de versões (detalhado)

### `v1.4.0` - CEP desconhecido e deploy Traefik alinhado

**Tipo de release:** `MINOR`

**Principais entregas**
- Checkbox **Não sei o CEP** ao lado do campo: desabilita CEP, exibe bloco de endereço manual e envia `cep` como `Não informado` quando marcado.
- Validação no cliente: com modo sem CEP, obrigatórios logradouro, número, bairro, cidade e UF.
- API (`zod`): aceita CEP com 8 dígitos (com ou sem hífen) ou o texto normalizado **não informado** (com/sem acento).
- `infra/docker-compose.vps.yml`: rede externa **`proxy`** e `certresolver` **`letsencrypt`** (compatível com Traefik na VPS Hetzner de referência).
- Chave de rascunho `logan-form-draft-v1.4.0` para não misturar estado com releases anteriores.

**Impacto funcional**
- Reduz abandono quando o lead não tem CEP em mãos.
- Documentação de deploy e DNS no README evita confusão entre versão no Git e versão vista no domínio público.

---

### `v1.3.0` - Anti-duplicidade e cidade_id resiliente

**Tipo de release:** `MINOR`

**Principais entregas**
- Consulta prévia em `GET /clientes?cpf_cnpj=` na API Betel antes de disparar webhook.
- Bloqueio de cadastro duplicado no backend (`POST /lead`) com retorno `409` (`CLIENT_ALREADY_EXISTS`).
- Frontend atualizado para exibir aviso de duplicidade e interromper o fluxo sem enviar ao webhook.
- Workflow n8n aprimorado com resolução de `cidade_id` por:
  - match exato,
  - match parcial,
  - match por prefixo,
  - fallback por similaridade (Levenshtein).
- Inclusão de observação automática no contato quando `cidade_id` não é encontrado ou quando fallback é usado.

**Impacto funcional**
- Evita criação de clientes duplicados por CPF/CNPJ.
- Melhora consistência de endereço no cadastro final da API de clientes.
- Reduz ruído operacional com alerta explícito de revisão manual quando cidade não é resolvida.

---

### `v1.2.0` - Backend seguro para webhook

**Tipo de release:** `MINOR`

**Principais entregas**
- Criação da API `POST /lead` em Node.js (`Express`).
- Implementação de `helmet` e `express-rate-limit`.
- Validação de payload com `zod` antes de encaminhar ao n8n.
- Encaminhamento ao n8n com segredo em `.env` (`x-webhook-token`).
- `infra/docker-compose.vps.yml` com roteamento Traefik para API (`/lead`) e site no mesmo domínio (evolução posterior: rede `proxy` + `letsencrypt`; ver `v1.4.0`).

**Impacto de segurança**
- Segredo removido do frontend e movido para ambiente de servidor.
- Redução de abuso por validação + limitação de taxa.

---

### `v1.1.0` - Cadastro com endereço enriquecido

**Tipo de release:** `MINOR` (nova funcionalidade sem quebra de compatibilidade)

**Principais entregas**
- Inclusão do campo de **CEP** com máscara automática (`00000-000`).
- Integração com **ViaCEP** para sugestão automática de logradouro, bairro, cidade e UF.
- Inclusão de bloco de endereço no formulário (`Endereço`, `Número`, `Bairro`, `Cidade`, `UF`, `Complemento`).
- Ampliação do payload enviado ao webhook com dados completos de localização.
- Ampliação da mensagem enviada para o WhatsApp com os mesmos dados de endereço.
- Exibição de versão no footer para rastreabilidade de release em produção.

**Validações e robustez**
- Validação de CEP com obrigatoriedade de 8 dígitos.
- Exibição de status de consulta do CEP (carregando, sucesso e erro).
- Timeout na consulta ViaCEP para evitar bloqueio de UX.
- Fallback para preenchimento manual quando API externa estiver indisponível.
- Garantia de endereço mínimo obrigatório antes do envio (rua, bairro, cidade e UF).

**Impacto funcional**
- Melhora significativa da qualidade dos leads enviados para operação/comercial.
- Redução de retrabalho no contato inicial por falta de endereço.
- Maior padronização dos dados entre frontend, n8n e WhatsApp.

---

### `v1.0.0` - Primeira versão produtiva do formulário

**Tipo de release:** `MAJOR` inicial

**Escopo entregue**
- Landing page estática otimizada para captação de leads.
- Formulário com campos essenciais: CPF/CNPJ, nome, e-mail e telefone.
- Máscaras de entrada para documento e telefone com suporte a múltiplos países.
- Validação local de CPF/CNPJ por dígitos verificadores.
- Integração com **BrasilAPI** para validação de CNPJ e sugestão de dados de contato.
- Envio de payload para **webhook n8n**.
- Redirecionamento automático para **WhatsApp** com mensagem pré-formatada.

**Qualidade e operação**
- Tratamento de erros e mensagens de feedback para o usuário.
- Estratégia resiliente de continuidade do fluxo mesmo com falha no webhook.
- Estrutura simples sem dependências de build para facilitar deploy e manutenção.

**Resultado**
- Estabelecimento da base funcional do funil digital de cadastro da Logan Technology.
- Primeiro release apto a operação em produção com rastreabilidade de versão.

## ✅ Checklist de release

- [x] Validações críticas revisadas
- [x] Integrações externas testadas
- [x] Mensagens de erro/fallback validadas
- [x] Versão atualizada no README
- [x] Versão exibida no footer

## 📄 Licença

Uso interno / proprietário Logan Technology.

