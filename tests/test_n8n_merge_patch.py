"""Testes do patch de Merge / conexões (sem chamar API)."""

import json
import unittest
from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "infra" / "scripts" / "n8n_patch_lembretes_merge.py"
FIXTURE = ROOT / "tests" / "fixtures" / "n8n_lembretes_merge_minimal.json"


def _load_patch_module():
    spec = spec_from_file_location("n8n_patch_lembretes_merge", SCRIPT)
    mod = module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(mod)
    return mod


class TestPatchLembretesMerge(unittest.TestCase):
    def test_fixture_patch_invariants(self):
        mod = _load_patch_module()
        with open(FIXTURE, encoding="utf-8") as f:
            wf = json.load(f)
        out = mod.patch_workflow(wf)

        fe = out["connections"]["Filtrar_Envio_Agora"]["main"][0]
        self.assertTrue(all(x["node"] != "Buscar_Token_Envio" for x in fe))
        self.assertTrue(any(x["node"] == "Rotear_API_Envio" for x in fe))

        r0 = out["connections"]["Rotear_API_Envio"]["main"][0]
        nodes = {x["node"] for x in r0}
        self.assertIn("Merge_Envio_Com_Token", nodes)
        self.assertIn("Buscar_Token_Envio", nodes)

        merge = next(n for n in out["nodes"] if n["name"] == "Merge_Envio_Com_Token")
        p = merge["parameters"]
        self.assertEqual(p.get("mode"), "combine")
        self.assertEqual(p.get("combineBy"), "combineByPosition")


if __name__ == "__main__":
    unittest.main()
