/**
 * Incorpore no sistema host (ex.: app.bezura.com.br):
 * <script src="https://cadastro.bezura.com.br/modal/cadastro-modal-loader.js" defer></script>
 *
 * Opcional: data-cadastro-origin="https://cadastro.bezura.com.br"
 *
 * O iframe recebe a URL via ?contextUrl= na src e por postMessage após o load.
 * referrerPolicy unsafe-url ajuda document.referrer a trazer path completo (quando o browser permitir).
 *
 * Opcional no app pai (ex.: app.bezura.com.br), se o iframe não usar ?contextUrl= na src:
 * window.addEventListener("message", function (e) {
 *   if (e.origin !== "https://cadastro.bezura.com.br") return;
 *   if (e.data && e.data.type === "cadastro-bezura-request-page-url") {
 *     e.source && e.source.postMessage(
 *       { type: "cadastro-bezura-context-url", url: location.href },
 *       e.origin
 *     );
 *   }
 * });
 */
(function (w, d) {
  var script = d.currentScript;
  var MODAL_ORIGIN =
    (script && script.getAttribute("data-cadastro-origin")) ||
    "https://cadastro.bezura.com.br";
  MODAL_ORIGIN = String(MODAL_ORIGIN).replace(/\/$/, "");

  var MSG_TYPE = "cadastro-bezura-context-url";

  var holderId = "cadastro-bezura-modal-root";

  function sendPageUrlToIframe(iframe) {
    if (!iframe || !iframe.contentWindow) return;
    try {
      iframe.contentWindow.postMessage(
        { type: MSG_TYPE, url: w.location.href },
        MODAL_ORIGIN
      );
    } catch (_e) {}
  }

  function mount() {
    if (d.getElementById(holderId)) return;

    var holder = d.createElement("div");
    holder.id = holderId;
    holder.setAttribute("aria-label", "Cadastro Bezura");
    holder.style.cssText =
      "position:fixed;bottom:16px;right:16px;z-index:2147483646;width:min(568px,calc(100vw - 32px));height:min(660px,calc(100vh - 32px));border:none;border-radius:16px;overflow:hidden;box-shadow:0 18px 40px rgba(27,63,138,0.28);";

    var iframe = d.createElement("iframe");
    var contextUrl = encodeURIComponent(w.location.href);
    iframe.src = MODAL_ORIGIN + "/modal/?contextUrl=" + contextUrl;
    iframe.title = "Cadastro Bezura";
    iframe.style.cssText = "width:100%;height:100%;border:0;background:#fff;";
    iframe.setAttribute("referrerpolicy", "unsafe-url");

    iframe.addEventListener("load", function () {
      sendPageUrlToIframe(iframe);
      w.setTimeout(function () {
        sendPageUrlToIframe(iframe);
      }, 200);
      w.setTimeout(function () {
        sendPageUrlToIframe(iframe);
      }, 800);
    });

    holder.appendChild(iframe);
    d.body.appendChild(holder);
  }

  if (d.readyState === "loading") {
    d.addEventListener("DOMContentLoaded", mount);
  } else {
    mount();
  }
})(window, document);
