#!/usr/bin/env python3
"""Check redirects and Claude section links retained by the integration split."""

import collections
import json
import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
COMPAT = "/integrations/claude"
CODE = "/integrations/claude-code"
ENTERPRISE = "/integrations/claude-enterprise"
RETIRED = ("cloudflare", "aws-cloudfront", "fastly", "akamai")


def sections(text):
    """Collect heading sections and explicit IDs, excluding fenced examples."""
    result, pending, active = {}, [], []
    counts = collections.Counter()
    fence = None
    for line in text.splitlines():
        marker = re.match(r"^\s*(`{3,}|~{3,})", line)
        if marker:
            if fence is None:
                fence = marker[1][0]
            elif marker[1][0] == fence:
                fence = None
            continue
        if fence:
            continue
        pending.extend(re.findall(r'\bid=["\']([^"\']+)["\']', line))
        heading = re.match(r"^#{1,6}\s+(.+?)\s*#*\s*$", line)
        if heading:
            slug = re.sub(r"[^\w\s-]", "", heading[1].lower()).replace(" ", "-")
            number = counts[slug]
            counts[slug] += 1
            active = [f"{slug}-{number}" if number else slug, *pending]
            pending = []
            for anchor in active:
                result[anchor] = []
        for anchor in active:
            result[anchor].append(line)
    return {anchor: "\n".join(lines) for anchor, lines in result.items()}


def page_entries(node):
    if isinstance(node, dict):
        for key, value in node.items():
            if key == "pages" and isinstance(value, list):
                yield from (item for item in value if isinstance(item, str))
            yield from page_entries(value)
    elif isinstance(node, list):
        for item in node:
            yield from page_entries(item)


def main():
    docs = json.loads((ROOT / "docs.json").read_text())
    errors = []
    redirects = docs.get("redirects", [])
    sources = collections.Counter(item["source"] for item in redirects)
    for source, count in sources.items():
        if count > 1:
            errors.append(f"Duplicate redirect source: {source}")
    redirects = {item["source"]: item["destination"] for item in redirects}

    expected = {"/trustguard/integrations/edge-waf": "/integrations/overview"}
    for vendor in RETIRED:
        for prefix in ("/integrations", "/trustguard/integrations", "/trustguard/integrations/edge-waf"):
            expected[f"{prefix}/{vendor}"] = "/integrations/overview"
        if (ROOT / f"integrations/{vendor}.mdx").exists():
            errors.append(f"Retired guide was restored: {vendor}")
    for source in (
        "/trustguard/integrations/ide/claude-code",
        "/trustguard/integrations/ide/claude-enterprise",
        "/trustguard/integrations/claude-code",
        "/trustguard/integrations/claude-enterprise",
        "/trustgate/mcp/claude",
        "/trustgate/integrations/claude",
    ):
        expected[source] = COMPAT
    for source, destination in expected.items():
        if redirects.get(source) != destination:
            errors.append(f"Expected direct redirect: {source} -> {destination}")
        if destination in redirects or not (ROOT / f"{destination.lstrip('/')}.mdx").is_file():
            errors.append(f"Redirect destination must be a page: {destination}")

    if COMPAT in redirects:
        errors.append(f"{COMPAT} must remain a page, not a redirect")
    if COMPAT.lstrip("/") in set(page_entries(docs.get("navigation", {}))):
        errors.append(f"{COMPAT} must not appear in navigation")

    mappings = {
        "claude-enterprise": [f"{ENTERPRISE}#inference-hook"],
        "claude-code": [f"{CODE}#trustguard-plugin"],
        "organization-connectors": [f"{ENTERPRISE}#organization-connectors"],
        "claude-code-cli": [f"{CODE}#connect-to-trustgate"],
        "deployment-options": [f"{CODE}#trustguard-plugin", f"{ENTERPRISE}#deployment-options"],
    }
    for anchor in (
        "neuraltrust-controls", "before-you-start", "verify", "reference", "coverage",
        "what-is-evaluated", "configuration", "attributes", "troubleshooting", "related",
    ):
        mappings[anchor] = [f"{CODE}#{anchor}", f"{ENTERPRISE}#{anchor}"]
    for alias, anchor in (
        ("why-it-needs-a-guardrail", "neuraltrust-controls"),
        ("what-neuraltrust-does-here", "neuraltrust-controls"),
        ("choose-your-setup", "deployment-options"),
    ):
        mappings[alias] = mappings[anchor]

    pages = {}
    for page in (COMPAT, CODE, ENTERPRISE):
        path = ROOT / f"{page.lstrip('/')}.mdx"
        if path.is_file():
            pages[page] = sections(path.read_text())
        else:
            errors.append(f"Missing page: {page}")
            pages[page] = {}
    for anchor, destinations in mappings.items():
        if anchor not in pages[COMPAT]:
            errors.append(f"Missing compatibility anchor: {COMPAT}#{anchor}")
            continue
        links = re.findall(r"\]\((/[^\s)]+)\)", pages[COMPAT][anchor])
        for destination in destinations:
            if destination not in links:
                errors.append(f"{COMPAT}#{anchor} must link to {destination}")
            page, target = destination.split("#", 1)
            if target not in pages[page]:
                errors.append(f"Missing destination anchor: {destination}")

    if errors:
        print("Legacy route checks failed:\n  " + "\n  ".join(errors), file=sys.stderr)
        return 1
    print(f"Legacy routes pass: {len(expected)} direct redirects and {len(mappings)} Claude anchors.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
