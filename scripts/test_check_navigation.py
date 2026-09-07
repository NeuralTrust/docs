#!/usr/bin/env python3
"""Regression tests for top-level navigation ownership. Run with unittest."""

import importlib.util
import pathlib
import unittest

SPEC = importlib.util.spec_from_file_location(
    "check_navigation", pathlib.Path(__file__).with_name("check-navigation.py")
)
navigation_check = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(navigation_check)


class TabOwnershipTests(unittest.TestCase):
    def conflicts(self, tabs):
        return navigation_check.tab_ownership_conflicts({"tabs": tabs})

    def test_catalog_cannot_belong_to_product_tabs(self):
        # The pre-fix configuration let TrustGate claim the Integrations route.
        tabs = [
            {
                "tab": product,
                "groups": [
                    {"group": "Introduction", "pages": [f"{product.lower()}/overview"]},
                    {"group": "Integrations", "pages": ["integrations/overview"]},
                ],
            }
            for product in ("TrustGate", "TrustGuard")
        ]
        tabs.append({
            "tab": "Integrations",
            "groups": [{"group": "Start here", "pages": ["integrations/overview"]}],
        })
        self.assertEqual(self.conflicts(tabs), {
            "integrations/overview": ["TrustGate", "TrustGuard", "Integrations"],
        })

    def test_distinct_routes_in_different_tabs(self):
        self.assertEqual(self.conflicts([
            {"tab": "Overview", "pages": ["index"]},
            {"tab": "TrustGate", "pages": ["trustgate/overview"]},
            {"tab": "Integrations", "pages": ["integrations/overview"]},
        ]), {})

    def test_nested_groups_are_checked(self):
        self.assertEqual(self.conflicts([
            {
                "tab": "TrustGate",
                "groups": [{"group": "MCP", "pages": [
                    {"group": "Clients", "pages": ["integrations/cursor"]},
                ]}],
            },
            {"tab": "Integrations", "pages": ["integrations/cursor"]},
        ]), {"integrations/cursor": ["TrustGate", "Integrations"]})

    def test_repeated_route_in_one_tab_is_allowed(self):
        self.assertEqual(self.conflicts([{
            "tab": "Integrations",
            "groups": [
                {"group": "Start here", "pages": ["integrations/overview"]},
                {"group": "Guides", "pages": ["integrations/overview"]},
            ],
        }]), {})

    def test_external_urls_are_not_owned_routes(self):
        pages = ["https://example.com/guide", "http://example.com/guide"]
        self.assertEqual(self.conflicts([
            {"tab": "TrustGate", "pages": pages},
            {"tab": "Integrations", "pages": pages},
        ]), {})

    def test_optional_boundary_slashes_do_not_hide_duplicate_routes(self):
        self.assertEqual(self.conflicts([
            {"tab": "TrustGate", "pages": ["/integrations/overview/"]},
            {"tab": "Integrations", "pages": ["integrations/overview"]},
        ]), {"integrations/overview": ["TrustGate", "Integrations"]})

    def test_navigation_without_tabs_has_no_conflicts(self):
        self.assertEqual(navigation_check.tab_ownership_conflicts({
            "groups": [{"group": "Start here", "pages": ["index"]}],
        }), {})


if __name__ == "__main__":
    unittest.main()
