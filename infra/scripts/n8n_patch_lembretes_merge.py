#!/usr/bin/env python3
"""
Aplica correções no workflow Lembretes_Bezura no n8n:

1. Merge_Envio_Com_Token: Combine → Position (sem Matching Fields vazio).
2. Conexões: Buscar_Token_Envio só após o ramo oficial do Rotear_API_Envio,
   não direto do Filtrar_Envio_Agora (mesma contagem de itens nos dois inputs do Merge).

Uso:
  export N8N_API_KEY='...'
  export N8N_BASE_URL='https://n8n.bezura.cloud'   # opcional
  python3 infra/scripts/n8n_patch_lembretes_merge.py

  python3 infra/scripts/n8n_patch_lembretes_merge.py --dry-run   # só valida fixture local
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import urllib.error
import urllib.request
from copy import deepcopy
from typing import Any

WORKFLOW_ID = "2WHEl44lXMUN4DHE"
DEFAULT_BASE = "https://n8n.bezura.cloud"


def _conn_targets(main_branch: list) -> list[dict[str, Any]]:
    """Lista de alvos na primeira saída de um nó."""
    if not main_branch or not main_branch[0]:
        return []
    return main_branch[0]


def _set_branch_targets(main_branch: list, targets: list[dict[str, Any]]) -> None:
    if not main_branch:
        main_branch.append([])
    main_branch[0] = targets


def patch_merge_node_parameters(node: dict[str, Any]) -> dict[str, Any]:
    """Normaliza nó Merge para combine + position (v2 ou v3)."""
    if node.get("type") != "n8n-nodes-base.merge":
        return node
    if node.get("name") != "Merge_Envio_Com_Token":
        return node

    params = dict(node.get("parameters") or {})
    tv = node.get("typeVersion")

    # Merge v3 (n8n 2.x): combineBy
    if tv == 3 or tv == 3.1 or tv == 3.2 or (isinstance(tv, (int, float)) and float(tv) >= 3):
        params["mode"] = "combine"
        params["combineBy"] = "combineByPosition"
        # Evita resíduos do modo por campos
        for stale in (
            "mergeByFields",
            "fieldsToMatch",
            "joinMode",
        ):
            params.pop(stale, None)
    else:
        # Merge v2.x
        params["mode"] = "combine"
        params["combinationMode"] = "mergeByPosition"

    node["parameters"] = params
    return node


def patch_connections(connections: dict[str, Any]) -> dict[str, Any]:
    """
    - Filtrar_Envio_Agora → apenas Rotear_API_Envio.
    - Rotear_API_Envio saída 0 (oficial) → Merge_Envio_Com_Token (in 0) + Buscar_Token_Envio.
    """
    c = deepcopy(connections)

    merge_tgt = {"node": "Merge_Envio_Com_Token", "type": "main", "index": 0}
    token_tgt = {"node": "Buscar_Token_Envio", "type": "main", "index": 0}
    rotear_tgt = {"node": "Rotear_API_Envio", "type": "main", "index": 0}

    # 1) Filtrar → só Rotear
    if "Filtrar_Envio_Agora" in c:
        main = c["Filtrar_Envio_Agora"].get("main") or [[]]
        first = _conn_targets(main)
        first = [x for x in first if x.get("node") != "Buscar_Token_Envio"]
        if not any(x.get("node") == "Rotear_API_Envio" for x in first):
            first = [rotear_tgt] + first
        seen: set[tuple[Any, Any]] = set()
        dedup: list[dict[str, Any]] = []
        for x in first:
            key = (x.get("node"), x.get("index"))
            if key in seen:
                continue
            seen.add(key)
            dedup.append(x)
        _set_branch_targets(main, dedup)
        c["Filtrar_Envio_Agora"]["main"] = main

    # 2) Rotear saída 0 → Merge + Buscar_Token (paralelo a partir do mesmo item)
    if "Rotear_API_Envio" in c:
        main = c["Rotear_API_Envio"].setdefault("main", [[], []])
        while len(main) < 2:
            main.append([])
        # Saída 0 = ramo verdadeiro (oficial) no IF 2.x
        main[0] = [merge_tgt, token_tgt]
        c["Rotear_API_Envio"]["main"] = main

    # 3) Buscar_Token → Merge input 1 (mantém se já existir)
    if "Buscar_Token_Envio" in c:
        main = c["Buscar_Token_Envio"].get("main") or [[]]
        first = _conn_targets(main)
        merge_in1 = {"node": "Merge_Envio_Com_Token", "type": "main", "index": 1}
        if not any(x.get("node") == "Merge_Envio_Com_Token" for x in first):
            first = [merge_in1]
        else:
            first = [merge_in1] if merge_in1 not in first else first
        _set_branch_targets(main, first)
        c["Buscar_Token_Envio"]["main"] = main

    return c


def patch_workflow(workflow: dict[str, Any]) -> dict[str, Any]:
    wf = deepcopy(workflow)
    nodes = wf.get("nodes") or []
    for i, n in enumerate(nodes):
        nodes[i] = patch_merge_node_parameters(dict(n))
    wf["nodes"] = nodes
    wf["connections"] = patch_connections(dict(wf.get("connections") or {}))
    return wf


def build_api_payload(workflow: dict[str, Any]) -> dict[str, Any]:
    """Payload aceito pelo PUT /workflows/:id (schema rejeita chaves extras em settings)."""
    raw = workflow.get("settings") or {}
    settings: dict[str, Any] = {}
    if isinstance(raw.get("executionOrder"), str):
        settings["executionOrder"] = raw["executionOrder"]
    return {
        "name": workflow["name"],
        "nodes": workflow["nodes"],
        "connections": workflow["connections"],
        "settings": settings,
    }


def api_request(
    method: str,
    url: str,
    headers: dict[str, str],
    body: dict[str, Any] | None = None,
) -> tuple[int, dict[str, Any] | str]:
    data = None
    if body is not None:
        data = json.dumps(body).encode("utf-8")
        headers = {**headers, "Content-Type": "application/json"}
    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=120) as resp:
            raw = resp.read().decode("utf-8")
            code = resp.getcode()
            try:
                return code, json.loads(raw)
            except json.JSONDecodeError:
                return code, raw
    except urllib.error.HTTPError as e:
        err_body = e.read().decode("utf-8", errors="replace")
        try:
            return e.code, json.loads(err_body)
        except json.JSONDecodeError:
            return e.code, err_body


def main() -> int:
    parser = argparse.ArgumentParser(description="Patch n8n Lembretes merge + wiring")
    parser.add_argument("--dry-run", action="store_true", help="Valida fixture em tests/fixtures")
    parser.add_argument("--fixture", default="", help="JSON do workflow para teste local")
    args = parser.parse_args()

    root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
    fixture_path = args.fixture or os.path.join(
        root, "tests", "fixtures", "n8n_lembretes_merge_minimal.json"
    )

    if args.dry_run:
        with open(fixture_path, encoding="utf-8") as f:
            wf = json.load(f)
        patched = patch_workflow(wf)
        # Invariantes
        fe = patched["connections"]["Filtrar_Envio_Agora"]["main"][0]
        assert all(x["node"] != "Buscar_Token_Envio" for x in fe)
        r0 = patched["connections"]["Rotear_API_Envio"]["main"][0]
        assert {x["node"] for x in r0} >= {"Merge_Envio_Com_Token", "Buscar_Token_Envio"}
        m = next(n for n in patched["nodes"] if n["name"] == "Merge_Envio_Com_Token")
        p = m["parameters"]
        assert p.get("mode") == "combine"
        assert p.get("combineBy") == "combineByPosition" or p.get("combinationMode") == "mergeByPosition"
        print("dry-run OK:", fixture_path)
        return 0

    key = os.environ.get("N8N_API_KEY", "").strip()
    base = os.environ.get("N8N_BASE_URL", DEFAULT_BASE).rstrip("/")
    if not key:
        print(
            "Defina N8N_API_KEY (Configurações → API no n8n) e execute novamente.",
            file=sys.stderr,
        )
        return 2

    url = f"{base}/api/v1/workflows/{WORKFLOW_ID}"
    headers = {"X-N8N-API-KEY": key, "Accept": "application/json"}

    code, data = api_request("GET", url, headers)
    if code != 200 or not isinstance(data, dict):
        print(f"GET falhou: {code} {data}", file=sys.stderr)
        return 1

    patched = patch_workflow(data)
    payload = build_api_payload(patched)

    code_put, put_resp = api_request("PUT", url, headers, payload)
    if code_put != 200:
        print(f"PUT falhou: {code_put} {put_resp}", file=sys.stderr)
        return 1

    print("Workflow atualizado:", put_resp.get("updatedAt") if isinstance(put_resp, dict) else put_resp)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
