#!/usr/bin/env python3
"""Regression tests for the TrustGate OpenAPI generator. Run with unittest."""

import importlib.util
import pathlib
import unittest

SPEC = importlib.util.spec_from_file_location(
    "trustgate_openapi", pathlib.Path(__file__).with_name("trustgate_openapi.py")
)
tg = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(tg)


def ref(section, name):
    return {"$ref": f"#/components/{section}/{name}"}


def source():
    body = {"content": {"application/json": {"schema": ref("schemas", "A")}}}
    return {
        "openapi": "3.0.0",
        "paths": {
            "/a": {
                "parameters": [{"name": "x", "in": "query"}],
                "get": {"security": [{"Bearer": []}], "responses": {"200": {"description": "ok", "content": {"application/json": {"schema": ref("schemas", "A")}}}}},
                "delete": {"requestBody": ref("requestBodies", "R"), "responses": {}},
            },
            "/b": {"get": {"responses": {"200": {"description": "ok", "content": {"application/json": {"schema": ref("schemas", "Hidden")}}}}}},
        },
        "components": {
            "schemas": {
                "Z": {"type": "object"},
                "A": {"type": "object", "properties": {"b": ref("schemas", "B")}},
                "B": {"type": "string"},
                "Hidden": {"type": "object"},
            },
            "requestBodies": {"R": body},
            "securitySchemes": {"Bearer": {"type": "http", "scheme": "bearer"}, "Unused": {"type": "http", "scheme": "basic"}},
        },
    }


ALLOWED = {("get", "/a"), ("delete", "/a")}


class PruneTests(unittest.TestCase):
    def test_drops_operations_outside_the_allowlist(self):
        out = tg.prune(source(), {("get", "/a")})
        self.assertEqual(tg.operations(out), {("get", "/a")})
        self.assertNotIn("/b", out["paths"])

    def test_keeps_path_level_keys_of_published_paths(self):
        out = tg.prune(source(), {("get", "/a")})
        self.assertIn("parameters", out["paths"]["/a"])

    def test_prunes_components_transitively(self):
        out = tg.prune(source(), {("get", "/a")})
        self.assertEqual(set(out["components"]["schemas"]), {"A", "B"})
        self.assertNotIn("requestBodies", out["components"])

    def test_keeps_used_security_scheme_only(self):
        out = tg.prune(source(), {("get", "/a")})
        self.assertEqual(set(out["components"]["securitySchemes"]), {"Bearer"})

    def test_preserves_source_key_order(self):
        out = tg.prune(source(), ALLOWED)
        self.assertEqual(list(out["components"]["schemas"]), ["A", "B"])
        self.assertEqual(list(out), ["openapi", "paths", "components"])

    def test_dump_is_four_space_with_trailing_newline(self):
        text = tg.dump({"a": 1})
        self.assertEqual(text, '{\n    "a": 1\n}\n')


class CheckTests(unittest.TestCase):
    def published(self):
        return tg.prune(source(), ALLOWED)

    def test_pruned_spec_passes(self):
        self.assertEqual(tg.problems(self.published(), ALLOWED), [])

    def test_missing_operation_fails(self):
        spec = self.published()
        del spec["paths"]["/a"]["delete"]
        self.assertTrue(any("missing allowlisted" in p for p in tg.problems(spec, ALLOWED)))

    def test_extra_operation_fails(self):
        spec = self.published()
        spec["paths"]["/c"] = {"get": {"responses": {}}}
        self.assertIn("operation not in allowlist: GET /c", tg.problems(spec, ALLOWED))

    def test_unresolved_ref_fails(self):
        spec = self.published()
        spec["components"]["schemas"]["A"]["properties"]["b"] = ref("schemas", "Nope")
        self.assertTrue(any("unresolved $ref" in p for p in tg.problems(spec, ALLOWED)))

    def test_orphan_component_fails(self):
        spec = self.published()
        spec["components"]["schemas"]["Z"] = {"type": "object"}
        self.assertTrue(any("orphan component" in p for p in tg.problems(spec, ALLOWED)))

    def test_unknown_security_scheme_fails(self):
        spec = self.published()
        del spec["components"]["securitySchemes"]
        self.assertTrue(any("unknown security scheme" in p for p in tg.problems(spec, ALLOWED)))


if __name__ == "__main__":
    unittest.main()
