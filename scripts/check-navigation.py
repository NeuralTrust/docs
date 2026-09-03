#!/usr/bin/env python3
"""Check that docs.json is valid and every page it lists exists.

A page entry is any string inside a "pages" array. Group and tab names are not
paths, so they are not checked — that distinction matters, because a group can
legitimately be called "Edge / WAF" and would look like a path to a looser rule.

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

    print(f"docs.json is valid; {len(pages)} navigation entries all resolve.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
