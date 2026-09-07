#!/usr/bin/env python3
"""Check navigation page existence and unambiguous top-level tab ownership.

A page entry is any string inside a "pages" array. Group and tab names are not
paths, so they are not checked. A group label containing a slash is not a page
path and must not be passed to the file-existence check.

A local page must belong to only one top-level tab. Cross-tab discovery should
use links in page content, not duplicate page entries in navigation.

Run it before opening a PR:

    python3 scripts/check-navigation.py
"""

import json
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
DOCS_JSON = ROOT / "docs.json"


def page_entries(node):
    """Yield every string that sits inside a "pages" array."""
    if isinstance(node, dict):
        for key, value in node.items():
            if key == "pages" and isinstance(value, list):
                for item in value:
                    if isinstance(item, str):
                        yield item
                    else:
                        yield from page_entries(item)
            else:
                yield from page_entries(value)
    elif isinstance(node, list):
        for item in node:
            yield from page_entries(item)


def resolves(page):
    if page.startswith(("http://", "https://")):
        return True
    return (ROOT / f"{page}.mdx").is_file() or (ROOT / page / "index.mdx").is_file()


def tab_ownership_conflicts(navigation):
    """Return local routes listed under more than one top-level tab."""
    owners = {}
    for index, tab in enumerate(navigation.get("tabs", [])):
        name = tab.get("tab", f"Tab {index + 1}")
        pages = {
            page.strip("/")
            for page in page_entries(tab)
            if not page.startswith(("http://", "https://"))
        }
        for page in sorted(pages):
            owners.setdefault(page, []).append(name)
    return {page: tabs for page, tabs in owners.items() if len(tabs) > 1}


def main():
    try:
        docs = json.loads(DOCS_JSON.read_text())
    except json.JSONDecodeError as exc:
        print(f"docs.json is not valid JSON: {exc}", file=sys.stderr)
        return 1

    pages = list(page_entries(docs))
    if not pages:
        print("no page entries found in docs.json — has the schema changed?", file=sys.stderr)
        return 1

    missing = sorted({p for p in pages if not resolves(p)})
    if missing:
        noun = "entry points" if len(missing) == 1 else "entries point"
        print(f"{len(missing)} navigation {noun} at a page that does not exist:", file=sys.stderr)
        for page in missing:
            print(f"  {page}  (expected {page}.mdx)", file=sys.stderr)
        print(
            "\nEach one is a 404 in the published navigation.",
            file=sys.stderr,
        )
        return 1

    conflicts = tab_ownership_conflicts(docs.get("navigation", {}))
    if conflicts:
        print("Local pages must belong to only one top-level tab:", file=sys.stderr)
        for page, tabs in sorted(conflicts.items()):
            print(f"  {page}: {', '.join(tabs)}", file=sys.stderr)
        print(
            "\nKeep each page in its own tab and use content links from other tabs.",
            file=sys.stderr,
        )
        return 1

    print(
        f"docs.json is valid; {len(pages)} navigation entries all resolve "
        "and local pages have unique tab ownership."
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
