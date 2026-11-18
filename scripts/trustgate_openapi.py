#!/usr/bin/env python3
"""Build and validate the published TrustGate Admin API spec.

trustgate/api/openapi.json is TrustGate's generated spec filtered to the
operations listed in scripts/trustgate_openapi_allowlist.json. The allowlist is
the publication decision: add an operation there to publish it, never edit the
generated file by hand.

Refresh from a TrustGate ref:

    git -C <TrustGate> show <ref>:docs/openapi.json > /tmp/x.json
    python3 scripts/trustgate_openapi.py generate /tmp/x.json

Validate (also run in CI):

    python3 scripts/trustgate_openapi.py check [--file path]

Generation keeps the source key order and prunes every component that no
published operation references, directly or transitively. The source info and
servers are published as they are; there are no docs-specific overrides.
"""

import argparse
import json
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
TARGET = ROOT / "trustgate" / "api" / "openapi.json"
ALLOWLIST = pathlib.Path(__file__).with_name("trustgate_openapi_allowlist.json")
METHODS = ("get", "put", "post", "delete", "options", "head", "patch", "trace")
REF_PREFIX = "#/components/"


def load_allowlist(path=ALLOWLIST):
    entries = json.loads(pathlib.Path(path).read_text())
    return {(e["method"].lower(), e["path"]) for e in entries}


def operations(spec):
    """Return the set of (method, path) operations in a spec."""
    return {
        (method, path)
        for path, item in spec.get("paths", {}).items()
        for method in item
        if method in METHODS
    }


def refs(node):
    """Yield every local $ref target inside node."""
    if isinstance(node, dict):
        for key, value in node.items():
            if key == "$ref" and isinstance(value, str):
                yield value
            else:
                yield from refs(value)
    elif isinstance(node, list):
        for item in node:
            yield from refs(item)


def security_names(node):
    """Yield every security scheme name used by an operation or the root."""
    if isinstance(node, dict):
        for key, value in node.items():
            if key == "security" and isinstance(value, list):
                for requirement in value:
                    if isinstance(requirement, dict):
                        yield from requirement
            else:
                yield from security_names(value)
    elif isinstance(node, list):
        for item in node:
            yield from security_names(item)


def reachable(spec):
    """Return the (section, name) components reachable from paths and security."""
    components = spec.get("components", {})
    seen = set()
    pending = list(refs(spec.get("paths", {})))
    for name in security_names({"paths": spec.get("paths", {}), **{k: v for k, v in spec.items() if k == "security"}}):
        seen.add(("securitySchemes", name))
    while pending:
        ref = pending.pop()
        if not ref.startswith(REF_PREFIX):
            continue
        section, _, name = ref[len(REF_PREFIX):].partition("/")
        if (section, name) in seen:
            continue
        seen.add((section, name))
        target = components.get(section, {}).get(name)
        if target is not None:
            pending.extend(refs(target))
    return seen


def prune(spec, allowed):
    """Keep only allowed operations and the components they reference."""
    out = dict(spec)
    paths = {}
    for path, item in spec.get("paths", {}).items():
        kept = {k: v for k, v in item.items() if k not in METHODS or (k, path) in allowed}
        if any(k in METHODS for k in kept):
            paths[path] = kept
    out["paths"] = paths
    used = reachable(out)
    components = {}
    for section, entries in spec.get("components", {}).items():
        kept = {n: v for n, v in entries.items() if (section, n) in used}
        if kept:
            components[section] = kept
    if components:
        out["components"] = components
    else:
        out.pop("components", None)
    return out


def problems(spec, allowed):
    """Return human-readable problems with a published spec."""
    found = []
    ops = operations(spec)
    for method, path in sorted(allowed - ops):
        found.append(f"missing allowlisted operation: {method.upper()} {path}")
    for method, path in sorted(ops - allowed):
        found.append(f"operation not in allowlist: {method.upper()} {path}")
    components = spec.get("components", {})
    for ref in sorted(set(refs(spec))):
        if not ref.startswith(REF_PREFIX):
            found.append(f"unsupported $ref: {ref}")
            continue
        section, _, name = ref[len(REF_PREFIX):].partition("/")
        if name not in components.get(section, {}):
            found.append(f"unresolved $ref: {ref}")
    for name in sorted(set(security_names(spec))):
        if name not in components.get("securitySchemes", {}):
            found.append(f"unknown security scheme: {name}")
    used = reachable(spec)
    for section, entries in components.items():
        for name in entries:
            if (section, name) not in used:
                found.append(f"orphan component: {REF_PREFIX}{section}/{name}")
    return found


def dump(spec):
    return json.dumps(spec, indent=4, ensure_ascii=False) + "\n"


def cmd_generate(args):
    source = json.loads(pathlib.Path(args.source).read_text())
    allowed = load_allowlist()
    missing = allowed - operations(source)
    if missing:
        for method, path in sorted(missing):
            print(f"source spec lacks allowlisted operation: {method.upper()} {path}", file=sys.stderr)
        return 1
    TARGET.write_text(dump(prune(source, allowed)))
    print(f"wrote {TARGET.relative_to(ROOT)}")
    return 0


def cmd_check(args):
    path = pathlib.Path(args.file)
    found = problems(json.loads(path.read_text()), load_allowlist())
    for line in found:
        print(line, file=sys.stderr)
    if found:
        print(f"{path}: {len(found)} problem(s); fix the allowlist or regenerate", file=sys.stderr)
        return 1
    print(f"{path}: ok")
    return 0


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = parser.add_subparsers(dest="cmd", required=True)
    gen = sub.add_parser("generate", help="filter a TrustGate spec into trustgate/api/openapi.json")
    gen.add_argument("source")
    gen.set_defaults(func=cmd_generate)
    chk = sub.add_parser("check", help="validate the published spec")
    chk.add_argument("--file", default=str(TARGET))
    chk.set_defaults(func=cmd_check)
    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
