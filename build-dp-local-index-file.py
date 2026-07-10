#!/usr/bin/env python3
"""
build-dp-local-index-file.py

Build a Frictionless-style data-package `index.json` from a directory of
individual table-schema JSON files (e.g. agent.json, event.json, ...).

For each schema file found, it pulls out the package-level "summary" fields
(identifier, url, name, title, description, comments, examples, namespace,
dcterms:isVersionOf, dcterms:references, rdfs:comment) -- i.e. every
top-level key in the schema file EXCEPT "fields" and "primaryKey" (and any
other keys you choose to drop) -- and adds it as an entry to the
"tableSchemas" array of the index.

Usage
-----
    python build-dp-local-index-file.py SCHEMA_DIR -o index.json \\
        --identifier "http://rs.tdwg.org/dwc/dwc-dp" \\
        --url "https://rs.gbif.org/sandbox/experimental/data-packages/dwc-dp/1.0_DEV/index.json" \\
        --name "dwc-dp" \\
        --version "1.0_DEV" \\
        --title "Darwin Core Data Package" \\
        --short-title "dwc-dp" \\
        --description "A data package for sharing biodiversity data using Darwin Core." \\
        --issued 2026-07-09 \\
        --is-latest

Or, if you'd rather keep the package-level metadata in a file instead of a
long CLI command, pass --meta meta.json where meta.json looks like:

    {
      "identifier": "http://rs.tdwg.org/dwc/dwc-dp",
      "url": "https://rs.gbif.org/sandbox/experimental/data-packages/dwc-dp/1.0_DEV/index.json",
      "name": "dwc-dp",
      "version": "1.0_DEV",
      "title": "Darwin Core Data Package",
      "shortTitle": "dwc-dp",
      "description": "A data package for sharing biodiversity data using Darwin Core.",
      "issued": "2026-07-09",
      "isLatest": true
    }

CLI options always override values from --meta if both are given.

If you don't pass ANY package-level metadata, the script will still run and
produce an index.json containing just "tableSchemas" -- fill in the rest by
hand, or re-run with --meta / the CLI flags.
"""

import argparse
import json
import sys
from pathlib import Path

# Keys to drop from each schema file before it's embedded in tableSchemas.
# "fields" is the (often long) column list, and "primaryKey" is schema-
# internal -- neither belongs in the lightweight package-level index.
DROP_KEYS = {"fields", "primaryKey", "weakPrimaryKey", "foreignKeys", "weakForeignKeys"}


def load_schema_summary(path: Path) -> dict:
    """Read one table-schema JSON file and return its index-entry form."""
    with path.open("r", encoding="utf-8") as f:
        data = json.load(f)

    if not isinstance(data, dict):
        raise ValueError(f"{path}: expected a JSON object at the top level")

    return {k: v for k, v in data.items() if k not in DROP_KEYS}


def find_schema_files(schema_dir: Path, pattern: str, exclude: set) -> list:
    files = sorted(
        p for p in schema_dir.glob(pattern)
        if p.is_file() and p.name not in exclude
    )
    return files


def build_index(schema_dir: Path, pattern: str, exclude_names: set) -> list:
    table_schemas = []
    errors = []

    for path in find_schema_files(schema_dir, pattern, exclude_names):
        try:
            table_schemas.append(load_schema_summary(path))
        except (json.JSONDecodeError, ValueError) as e:
            errors.append(f"  - {path.name}: {e}")

    if errors:
        print("Warning: skipped file(s) that could not be parsed:", file=sys.stderr)
        print("\n".join(errors), file=sys.stderr)

    # Sort entries by their "name" field (falls back to filename-derived
    # value if "name" is missing) so the index is stable and alphabetical,
    # matching the convention used in the example index.json.
    table_schemas.sort(key=lambda entry: entry.get("name", ""))

    return table_schemas


def parse_args():
    p = argparse.ArgumentParser(
        description="Build an index.json from a directory of table-schema JSON files.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    p.add_argument("schema_dir", type=Path, help="Directory containing the schema JSON files")
    p.add_argument("-o", "--output", type=Path, default=Path(
        "sandbox/experimental/data-packages/dwc-dp/1.0_DEV/index.json"),
                   help="Path to write the resulting index.json (default: ./index.json)")
    p.add_argument("--pattern", default="*.json",
                   help="Glob pattern (relative to schema_dir) for schema files (default: *.json)")
    p.add_argument("--exclude", nargs="*", default=[],
                   help="Filenames to exclude from the scan (e.g. an existing index.json in the same folder)")
    p.add_argument("--meta", type=Path,
                   help="Optional JSON file with package-level metadata "
                        "(identifier, url, name, version, title, shortTitle, "
                        "description, issued, isLatest, ...)")

    # Individual package-level metadata fields (override --meta if both given)
    p.add_argument("--identifier")
    p.add_argument("--url")
    p.add_argument("--name")
    p.add_argument("--version")
    p.add_argument("--title")
    p.add_argument("--short-title", dest="shortTitle")
    p.add_argument("--description")
    p.add_argument("--issued")
    p.add_argument("--is-latest", dest="isLatest", action="store_true", default=None)
    p.add_argument("--indent", type=int, default=2, help="JSON indent for output (default: 2)")

    return p.parse_args()


def main():
    args = parse_args()

    if not args.schema_dir.is_dir():
        sys.exit(f"Error: {args.schema_dir} is not a directory")

    # Always exclude the output file itself if it lives inside schema_dir,
    # plus anything the user explicitly excluded.
    exclude_names = set(args.exclude)
    try:
        if args.output.resolve().parent == args.schema_dir.resolve():
            exclude_names.add(args.output.name)
    except OSError:
        pass

    table_schemas = build_index(args.schema_dir, args.pattern, exclude_names)

    # Assemble package-level metadata: start with --meta file, then let
    # individual CLI flags override.
    meta = {}
    if args.meta:
        with args.meta.open("r", encoding="utf-8") as f:
            meta = json.load(f)

    for key in ("identifier", "url", "name", "version", "title", "shortTitle",
                "description", "issued", "isLatest"):
        value = getattr(args, key)
        if value is not None:
            meta[key] = value

    index = {}
    # Preserve a sensible key order: known metadata keys first (in the
    # canonical order), then any extra keys from --meta, then tableSchemas.
    canonical_order = ["identifier", "url", "name", "version", "title",
                       "shortTitle", "description", "issued", "isLatest"]
    for key in canonical_order:
        if key in meta:
            index[key] = meta[key]
    for key, value in meta.items():
        if key not in index:
            index[key] = value

    index["tableSchemas"] = table_schemas

    with args.output.open("w", encoding="utf-8") as f:
        json.dump(index, f, indent=args.indent, ensure_ascii=False)
        f.write("\n")

    print(f"Wrote {args.output} with {len(table_schemas)} table schema entr"
          f"{'y' if len(table_schemas) == 1 else 'ies'}.")


if __name__ == "__main__":
    main()