#!/usr/bin/env python3
"""Focused offline tests for the external app registry projection."""

from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REPO = ROOT.parents[1]
sys.path.insert(0, str(ROOT))
from server import IntegrationsApi, parse_registry  # noqa: E402


REGISTRY = """export const EXTERNAL_APP_REGISTRY: ExternalAppRecord[] = [
  // Existing direct integrations (2)
  { id: 'gmail', name: 'Gmail', category: 'communication', status: 'live', apiDocs: 'https://developers.google.com/gmail/api' },
  { id: 'supabase', name: 'Supabase', category: 'database', status: 'mcp_only', apiDocs: 'https://supabase.com/docs', note: 'Owner\\'s MCP only' },

  // Commerce (1)
  { id: 'shop-x', name: 'Shop X', category: 'commerce', status: 'planned', apiDocs: 'https://shop.example/docs' },
];
"""


class IntegrationsApiTest(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        (self.root / "integrations" / "gmail").mkdir(parents=True)
        (self.root / "integrations" / "gmail" / "README.md").write_text("# Gmail\n", encoding="utf-8")
        self.path = self.root / "registry.ts"
        self.path.write_text(REGISTRY, encoding="utf-8")
        self.api = IntegrationsApi(self.path, token="", environment="development", root=self.root)

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def get(self, target: str, **kwargs):
        return self.api.handle("GET", target, **kwargs)

    def test_overview(self) -> None:
        payload = self.get("/api/v1/integrations").payload
        self.assertEqual(payload["schema_version"], "solo-empire.integrations.v1")
        self.assertEqual(payload["summary"]["apps_total"], 3)
        self.assertEqual(payload["summary"]["connected"], 2)
        self.assertEqual(payload["summary"]["with_guide"], 1)
        apps = {app["id"]: app for app in payload["apps"]}
        self.assertEqual(apps["gmail"]["guide"], "integrations/gmail/README.md")
        self.assertEqual(apps["gmail"]["section"], "Existing direct integrations")
        self.assertEqual(apps["supabase"]["note"], "Owner's MCP only")
        self.assertEqual(apps["shop-x"]["section"], "Commerce")
        self.assertEqual([item["value"] for item in payload["signals"]["statuses"]], ["live", "mcp_only", "planned"])

    def test_filters(self) -> None:
        self.assertEqual([app["id"] for app in self.get("/api/v1/integrations?status=planned").payload["apps"]], ["shop-x"])
        self.assertEqual([app["id"] for app in self.get("/api/v1/integrations?category=database").payload["apps"]], ["supabase"])
        self.assertEqual([app["id"] for app in self.get("/api/v1/integrations?q=GMAIL").payload["apps"]], ["gmail"])
        self.assertEqual(self.get("/api/v1/integrations?q=" + "x" * 81).status, 400)

    def test_strict_parsing_fails_closed(self) -> None:
        for broken in (
            REGISTRY.replace("status: 'live'", "status: 'unknown'"),
            REGISTRY.replace("apiDocs: 'https://developers", "apiDocs: 'http://developers"),
            REGISTRY.replace("{ id: 'shop-x'", "{ id: shopX"),
            REGISTRY.replace("id: 'supabase'", "id: 'gmail'"),
        ):
            with self.subTest(broken=broken[:0]):
                with self.assertRaises(ValueError):
                    parse_registry(broken)
        self.path.write_text(REGISTRY.replace("{ id: 'shop-x'", "{ id: shopX"), encoding="utf-8")
        response = self.get("/api/v1/integrations")
        self.assertEqual(response.status, 503)
        self.assertEqual(response.payload["error"]["code"], "registry_unavailable")

    def test_read_only_and_auth(self) -> None:
        self.assertEqual(self.api.handle("POST", "/api/v1/integrations").status, 405)
        self.assertEqual(self.get("/api/v1/other").status, 404)
        guarded = IntegrationsApi(self.path, token="t0ken", environment="development", root=self.root)
        self.assertEqual(guarded.handle("GET", "/api/v1/integrations").status, 401)
        self.assertEqual(guarded.handle("GET", "/api/v1/integrations", headers={"Authorization": "Bearer t0ken"}).status, 200)
        self.assertEqual(IntegrationsApi(self.path, token="", environment="production").handle("GET", "/api/v1/integrations").status, 503)

    def test_real_registry_parses_every_record(self) -> None:
        real = REPO / "infra" / "api" / "external_app_registry.ts"
        records = parse_registry(real.read_text(encoding="utf-8"))
        self.assertEqual(len(records), real.read_text(encoding="utf-8").count("{ id: '"))


if __name__ == "__main__":
    unittest.main()
