# n8n: `chatSessionId` no fluxo e mensagem na sessão (Helena / Bezura)

O `POST /lead` repassa ao webhook n8n o mesmo JSON do cadastro, incluindo o campo opcional **`chatSessionId`** (UUID), quando o lead abriu o formulário com link do tipo `https://cadastro.bezura.com.br/?<uuid>`.

Referências da API Helena:

- [Autenticação (Bearer)](https://helena.readme.io/reference/getting-started-with-your-api)
- [Enviar mensagem na sessão](https://helena.readme.io/reference/post_v1-session-id-message) — `POST https://api.helena.run/chat/v1/session/{id}/message`
- Opcional (resposta em até ~25s): [Enviar mensagem síncrona](https://helena.readme.io/reference/post_v1-session-id-message-sync) — `.../message/sync`

O `{id}` da URL da Helena é o **mesmo UUID** da rota do chat Bezura (`.../sessions/<uuid>`), enviado no webhook como **`chatSessionId`**.

---

## 1. O que chega no Webhook n8n

Exemplo (campos principais):

```json
{
  "documentType": "CPF",
  "document": "000.000.000-00",
  "name": "...",
  "email": "...",
  "phoneCountry": "BR",
  "phone": "...",
  "cep": "...",
  "addressStreet": "...",
  "addressNumber": "...",
  "addressDistrict": "...",
  "addressCity": "...",
  "addressState": "SP",
  "addressComplement": "",
  "source": "logan-form-web",
  "submittedAt": "2026-04-02T12:00:00.000Z",
  "chatSessionId": "a5516cf1-53f1-4df4-810f-cc67711e8915"
}
```

Dependendo da versão do nó **Webhook**, os dados podem vir na raiz do item (`$json.chatSessionId`) ou dentro de `body` (`$json.body.chatSessionId`). Use a aba **Executions** do n8n no último disparo para confirmar.

**Expressão segura (em qualquer campo / URL):**

```text
{{ $json.chatSessionId || $json.body?.chatSessionId || '' }}
```

---

## 2. Manter o ID em todos os `Edit Fields` / `Set`

Em **cada** nó que remapeia o payload (Edit Fields, Set, etc.):

1. Inclua explicitamente **`chatSessionId`** na saída.
2. Valor: `{{ $json.chatSessionId }}` (ou a expressão composta acima se a origem for `body`).

Assim o UUID não se perde antes do `POST /clientes` Betel e antes do nó Helena.

---

## 3. Só chamar Helena se existir sessão

Adicione um nó **IF** (ou **Switch**) antes do HTTP Request:

- **Condição:** `chatSessionId` não vazio.
- Exemplo: `{{ $json.chatSessionId }}` **is not empty** (ou comprimento da string > 0).

- Ramo **true:** vai para o nó Helena.
- Ramo **false:** pode ir direto ao fim do fluxo (ou só log), para não quebrar cadastros sem chat.

---

## 4. Nó HTTP Request — enviar mensagem na sessão

Ajuste o nó que você já criou assim:

| Campo | Valor |
|--------|--------|
| **Method** | `POST` |
| **URL** | `https://api.helena.run/chat/v1/session/{{ $json.chatSessionId }}/message` |
| | Se o ID estiver só no primeiro item após vários nós: `{{ $('NomeDoNóQueAindaTemOWebhook').item.json.chatSessionId }}` |
| **Authentication** | Header `Authorization` = `Bearer <token>` (credencial n8n ou variável de ambiente; [doc Helena](https://helena.readme.io/reference/getting-started-with-your-api)) |
| **Send Headers** | `Content-Type: application/json` |
| **Send Body** | JSON |

**Corpo (body):** mantenha o mesmo JSON que você já validou no nó atual (a doc pública do ReadMe nem sempre lista todos os campos). Em geral há campo de texto da mensagem; exemplo ilustrativo (ajuste ao payload real do seu nó / “Try it” da Helena):

```json
{
  "text": "Cadastro concluído com sucesso. Você pode voltar ao chat para continuar o atendimento."
}
```

Se o seu nó já usa outro formato (`content`, `type`, template etc.), **não mude o body** — só substitua o **`{id}` da URL** pela expressão com **`chatSessionId`**.

**Síncrono:** troque o path final de `/message` para `/message/sync` se quiser esperar o status na mesma execução (até ~25s).

**Regras do canal:** a Helena aplica as mesmas regras do atendimento (ex.: WhatsApp pode exigir modelo em certos casos). Ver texto da [doc “Enviar mensagem”](https://helena.readme.io/reference/post_v1-session-id-message).

---

## 5. Normalizar `chatSessionId` com um único nó (opcional)

Se o webhook entregar `body` aninhado, um nó **Code** (JavaScript) no início ajuda:

```javascript
const j = $input.first().json;
const flat = j.body && typeof j.body === "object" ? { ...j, ...j.body } : j;
const chatSessionId = flat.chatSessionId || "";
return [{ json: { ...flat, chatSessionId } }];
```

Os nós seguintes passam a usar sempre `$json.chatSessionId`.

---

## Workflow no n8n

O link `https://n8n.bezura.cloud/workflow/kzjREuvKXHbvuWjg` só pode ser editado dentro do n8n; este arquivo descreve exatamente o que configurar lá. Depois de alterar, execute um teste com payload contendo `chatSessionId` e outro sem, para validar o IF e o POST Helena.
