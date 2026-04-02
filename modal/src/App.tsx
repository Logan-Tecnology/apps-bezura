import { useCallback, useEffect, useMemo, useState } from "react";

const SESSION_RE =
  /\/sessions\/([0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12})/i;

const MSG_CONTEXT_URL = "cadastro-bezura-context-url";
const MSG_PAGE_URL = "cadastro-bezura-page-url";
const MSG_PARENT_URL = "cadastro-bezura-parent-url";
const MSG_REQUEST_PAGE_URL = "cadastro-bezura-request-page-url";

const URL_MSG_TYPES = new Set([
  MSG_CONTEXT_URL,
  MSG_PAGE_URL,
  MSG_PARENT_URL
]);

function CopyIcon() {
  return (
    <svg
      className="bubble-copy-icon"
      xmlns="http://www.w3.org/2000/svg"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="2"
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden="true"
    >
      <rect x="9" y="9" width="13" height="13" rx="2" ry="2" />
      <path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1" />
    </svg>
  );
}

function extractSessionId(url: string): string | null {
  if (!url) return null;
  try {
    const m = url.match(SESSION_RE);
    return m ? m[1].toLowerCase() : null;
  } catch {
    return null;
  }
}

function readContextUrlFromQuery(): string {
  const params = new URLSearchParams(window.location.search);
  const encoded =
    params.get("contextUrl") ||
    params.get("parentUrl") ||
    params.get("ref") ||
    params.get("url");
  if (encoded) {
    try {
      return decodeURIComponent(encoded);
    } catch {
      return encoded;
    }
  }
  return "";
}

function isReferrerLikelyStripped(referrer: string): boolean {
  if (!referrer) return true;
  try {
    const r = new URL(referrer);
    return r.pathname === "/" || r.pathname === "";
  } catch {
    return true;
  }
}

export default function App() {
  const [copied, setCopied] = useState(false);
  const [contextUrl, setContextUrl] = useState("");
  const [pasteValue, setPasteValue] = useState("");

  const applyUrl = useCallback((raw: string) => {
    const trimmed = raw.trim();
    if (!trimmed) return;
    setContextUrl(trimmed);
  }, []);

  useEffect(() => {
    const fromQuery = readContextUrlFromQuery();
    if (fromQuery) {
      setContextUrl(fromQuery);
      return;
    }

    let cancelled = false;
    const tryReferrer = () => {
      if (cancelled) return;
      setContextUrl((prev) => {
        if (prev) return prev;
        const ref = document.referrer;
        if (!ref) return prev;
        if (extractSessionId(ref) || !isReferrerLikelyStripped(ref)) return ref;
        return prev;
      });
    };

    tryReferrer();
    const timeouts = [40, 200, 600].map((ms) =>
      window.setTimeout(tryReferrer, ms)
    );
    return () => {
      cancelled = true;
      timeouts.forEach((id) => window.clearTimeout(id));
    };
  }, []);

  useEffect(() => {
    function onMessage(event: MessageEvent) {
      const data = event.data;
      if (!data || typeof data !== "object") return;
      if (!URL_MSG_TYPES.has(data.type)) return;
      if (typeof data.url !== "string" || !data.url.trim()) return;
      setContextUrl(data.url.trim());
    }
    window.addEventListener("message", onMessage);
    return () => window.removeEventListener("message", onMessage);
  }, []);

  const requestUrlFromParent = useCallback(() => {
    try {
      if (window.parent && window.parent !== window) {
        window.parent.postMessage({ type: MSG_REQUEST_PAGE_URL }, "*");
      }
    } catch (_e) {
      /* cross-origin parent still receives postMessage */
    }
  }, []);

  useEffect(() => {
    const t1 = window.setTimeout(requestUrlFromParent, 100);
    const t2 = window.setTimeout(requestUrlFromParent, 500);
    return () => {
      window.clearTimeout(t1);
      window.clearTimeout(t2);
    };
  }, [requestUrlFromParent]);

  const sessionId = useMemo(() => extractSessionId(contextUrl), [contextUrl]);

  const registrationUrl = useMemo(() => {
    if (!sessionId) return "";
    const origin = window.location.origin;
    return `${origin}/?${sessionId}`;
  }, [sessionId]);

  const copyLink = useCallback(async () => {
    if (!registrationUrl) return;
    try {
      await navigator.clipboard.writeText(registrationUrl);
    } catch {
      const ta = document.createElement("textarea");
      ta.value = registrationUrl;
      ta.setAttribute("readonly", "");
      ta.style.position = "fixed";
      ta.style.left = "-9999px";
      document.body.appendChild(ta);
      ta.select();
      document.execCommand("copy");
      document.body.removeChild(ta);
    }
    setCopied(true);
    window.setTimeout(() => setCopied(false), 2200);
  }, [registrationUrl]);

  const applyPaste = useCallback(() => {
    applyUrl(pasteValue);
  }, [applyUrl, pasteValue]);

  return (
    <div className="app">
      <header className="app-header">
        <h1 className="app-header-title">Logan Tools</h1>
        <div className="app-header-brand">
          <img src="/logan-technology-logomarca-.png" alt="Logan Technology" />
        </div>
      </header>
      <main className="app-main">
        {!registrationUrl ? (
          <>
            <div className="actions-row">
              <button
                type="button"
                className="btn-primary"
                onClick={requestUrlFromParent}
              >
                Gerar link do formulário
              </button>
              <p className="actions-hint">
                Tenta obter a URL automaticamente. Se não aparecer o link,
                cole a URL do chat abaixo — ou peça ao time do Bezura para
                passar a URL na <code>src</code> do iframe (veja{" "}
                <code>modal/host-snippet.txt</code> no projeto).
              </p>
            </div>
            <div className="paste-panel">
              <label className="paste-label" htmlFor="paste-url">
                URL da barra de endereços (aba do chat)
              </label>
              <input
                id="paste-url"
                className="paste-input"
                type="url"
                inputMode="url"
                autoComplete="off"
                placeholder="https://app.bezura.com.br/chat2/sessions/..."
                value={pasteValue}
                onChange={(e) => setPasteValue(e.target.value)}
                onKeyDown={(e) => {
                  if (e.key === "Enter") applyPaste();
                }}
              />
              <button type="button" className="btn-secondary" onClick={applyPaste}>
                Aplicar URL
              </button>
            </div>
          </>
        ) : null}

        <div
          className={
            "bubble" + (!registrationUrl ? " bubble--waiting" : " bubble--ready")
          }
        >
          <span className="bubble-title">Formulário de Cadastro</span>
          {registrationUrl ? (
            <div className="bubble-link-row">
              <p className="bubble-url" title={registrationUrl}>
                {registrationUrl}
              </p>
              <button
                type="button"
                className="bubble-copy"
                onClick={copyLink}
                aria-label="Copiar link do formulário"
                title="Copiar"
              >
                <CopyIcon />
              </button>
            </div>
          ) : (
            <p className="bubble-hint">
              Use o botão acima ou cole a URL do chat. O ID vem do trecho{" "}
              <code>/sessions/</code> na URL.
            </p>
          )}
        </div>
        {copied ? <p className="toast">Link copiado.</p> : null}
      </main>
    </div>
  );
}
