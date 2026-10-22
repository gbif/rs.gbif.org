#!/usr/bin/env python3
"""
sync-dwc-dp.py

Add a DwC-DP version, published by TDWG on rs.tdwg.org, to the sandbox data packages.

DwC-DP is maintained by TDWG in https://github.com/tdwg/rs.tdwg.org/tree/master/dwc-dp
and published on rs.tdwg.org. Its table schemas are not copied here: the IPT downloads
them from rs.tdwg.org, following the urls in index.json. For the given version this script:

1. downloads the profile from rs.tdwg.org, which lists the table schemas;
2. downloads the table schemas and generates index.json from them, with each table
   schema's "url" pointing to rs.tdwg.org (the table schemas themselves have a relative
   url, e.g. table-schemas/agent.json, which the IPT replaces with the url in index.json);
3. writes version.json, unless it already exists;
4. replaces the dwc-dp entry in the sandbox registry if this is the latest version.

Usage
-----
    pip install requests
    python3 sync-dwc-dp.py 1.0 --issued 2026-10-13

Older versions are not updated: set "isLatest" to false and update
"latestCompatibleVersion" in them by hand, then run
data-packages-validation-checks.py.
"""

import argparse
import datetime
import json
import sys
from pathlib import Path

import requests

RS_GBIF_URL = "https://rs.gbif.org/"
RS_TDWG_URL = "https://rs.tdwg.org/dwc-dp/"
REGISTRY = Path("sandbox/data-packages/index.json")
DEST = Path("sandbox/data-packages/dwc-dp")
PROFILE = "dwc-dp-profile.json"

PACKAGE_METADATA = {
    "identifier": "http://rs.tdwg.org/dwc/dwc-dp",
    "name": "dwc-dp",
    "title": "Darwin Core Data Package",
    "shortTitle": "dwc-dp",
    "description": "A data package for sharing biodiversity data using Darwin Core.",
}

# Keys of a table schema that are not copied into index.json
TABLE_SCHEMA_ONLY_KEYS = {"fields", "primaryKey", "weakPrimaryKey", "foreignKeys", "weakForeignKeys"}


def download_json(url):
    try:
        response = requests.get(url, timeout=30)
        response.raise_for_status()
        return response.json()
    except (requests.RequestException, ValueError) as e:
        sys.exit(f"Error: can't download {url}: {e}")


def build_table_schemas(tdwg_url):
    """The tableSchemas entries of index.json, for the table schemas listed in the profile."""
    profile = download_json(tdwg_url + PROFILE)
    try:
        names = profile["$defs"]["dwc-dp-resource-names"]["enum"]
    except (KeyError, TypeError):
        sys.exit(f"Error: no table schema names ($defs/dwc-dp-resource-names/enum) in {tdwg_url + PROFILE}")

    table_schemas = []
    for name in sorted(names):
        url = f"{tdwg_url}table-schemas/{name}.json"
        table_schema = download_json(url)
        if not isinstance(table_schema, dict):
            sys.exit(f"Error: {url} is not a table schema")
        if table_schema.get("name") != name:
            sys.exit(f"Error: unexpected name in {url}: {table_schema.get('name')}")
        if table_schema.get("url") not in (f"table-schemas/{name}.json", url):
            sys.exit(f"Error: unexpected url in {url}: {table_schema.get('url')}")

        entry = {key: value for key, value in table_schema.items() if key not in TABLE_SCHEMA_ONLY_KEYS}
        entry["url"] = url
        table_schemas.append(entry)
    return table_schemas


def update_registry(index):
    registry = json.loads(REGISTRY.read_text(encoding="utf-8"))
    packages = registry["dataPackages"]
    names = [p.get("name") for p in packages]
    if index["name"] in names:
        packages[names.index(index["name"])] = index
    else:
        packages.append(index)
    # The registry is stored with ASCII escapes and no trailing newline
    REGISTRY.write_text(json.dumps(registry, indent=2, ensure_ascii=True), encoding="utf-8")


def parse_args():
    p = argparse.ArgumentParser(
        description="Add a DwC-DP version, published by TDWG on rs.tdwg.org, to the sandbox data packages.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    p.add_argument("version", help="DwC-DP version, as on rs.tdwg.org (e.g. 1.0)")
    p.add_argument("--issued", required=True, help="Release date of the version, YYYY-MM-DD")
    p.add_argument("--tdwg-url",
                   help="URL of the version, with the profile and table schemas under it, e.g. for a pre-release "
                        "on the TDWG sandbox (default: https://rs.tdwg.org/dwc-dp/<version>/)")
    p.add_argument("--not-latest", dest="is_latest", action="store_false",
                   help="Set isLatest to false and leave the registry unchanged")
    p.add_argument("--force", action="store_true", help="Replace index.json if it already exists")
    return p.parse_args()


def main():
    args = parse_args()

    try:
        datetime.datetime.strptime(args.issued, "%Y-%m-%d")
    except ValueError:
        sys.exit(f"Error: --issued must be a date as YYYY-MM-DD, got {args.issued}")
    if not REGISTRY.exists():
        sys.exit(f"Error: {REGISTRY} not found, run this script from the repository root")

    dest = DEST / args.version
    index_file = dest / "index.json"
    tdwg_url = args.tdwg_url or f"{RS_TDWG_URL}{args.version}/"
    if not tdwg_url.endswith("/"):
        tdwg_url += "/"

    if index_file.exists() and not args.force:
        sys.exit(f"Error: {index_file} already exists, pass --force to replace it")

    table_schemas = build_table_schemas(tdwg_url)

    index = {
        "identifier": PACKAGE_METADATA["identifier"],
        "url": RS_GBIF_URL + index_file.as_posix(),
        "profile": tdwg_url + PROFILE,
        "name": PACKAGE_METADATA["name"],
        "version": args.version,
        "title": PACKAGE_METADATA["title"],
        "shortTitle": PACKAGE_METADATA["shortTitle"],
        "description": PACKAGE_METADATA["description"],
        "issued": args.issued,
        "isLatest": args.is_latest,
        "tableSchemas": table_schemas,
    }

    dest.mkdir(parents=True, exist_ok=True)
    with index_file.open("w", encoding="utf-8") as f:
        json.dump(index, f, indent=2, ensure_ascii=False)
        f.write("\n")

    version_file = dest / "version.json"
    if not version_file.exists():
        version = {"version": args.version, "latestCompatibleVersion": args.version}
        version_file.write_text(json.dumps(version, indent=2) + "\n", encoding="utf-8")

    if args.is_latest:
        update_registry(index)

    print(f"Wrote {index_file} for DwC-DP {args.version} ({len(table_schemas)} table schemas on {tdwg_url})")
    if args.is_latest:
        print(f"Updated {REGISTRY}")
        print("Now set isLatest to false and update latestCompatibleVersion in older versions, "
              "then run data-packages-validation-checks.py")


if __name__ == "__main__":
    main()
