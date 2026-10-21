#!/usr/bin/env python3
"""
sync-dwc-dp.py

Copy a DwC-DP version from tdwg/rs.tdwg.org into this repository.

DwC-DP is maintained by TDWG in https://github.com/tdwg/rs.tdwg.org/tree/master/dwc-dp
and copied here. For the given version this script:

1. fetches dwc-dp/<version> from tdwg/rs.tdwg.org at the given ref;
2. copies the profile and the table schemas unchanged, except that each table
   schema's relative "url" (table-schemas/agent.json) is rewritten to its
   absolute rs.gbif.org URL;
3. writes version.json, unless it already exists;
4. generates index.json from the table schemas;
5. replaces the dwc-dp entry in the sandbox registry if this is the latest version.

Usage
-----
    python3 sync-dwc-dp.py 1.0 --issued 2026-10-13

Older versions are not updated: set "isLatest" to false and update
"latestCompatibleVersion" in them by hand, then run
data-packages-validation-checks.py. Note the upstream commit, printed at the end,
in the commit message.
"""

import argparse
import datetime
import importlib.util
import json
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

UPSTREAM_REPO = "https://github.com/tdwg/rs.tdwg.org.git"
RS_URL = "https://rs.gbif.org/"
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

RELATIVE_URL = re.compile(r'"url": "table-schemas/')


def load_index_builder():
    # build-dp-local-index-file.py has dashes in its name, so it cannot be imported normally
    path = Path(__file__).resolve().parent / "build-dp-local-index-file.py"
    spec = importlib.util.spec_from_file_location("build_dp_local_index_file", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def fetch_upstream(ref, workdir):
    """Sparse checkout of dwc-dp at ref; returns the checkout path and the resolved commit."""
    checkout = Path(workdir) / "rs.tdwg.org"
    git = ["git", "-C", str(checkout)]
    # tree:0 fetches commits only; trees and files are fetched on checkout, for dwc-dp only
    subprocess.run(["git", "clone", "--quiet", "--filter=tree:0", "--no-checkout", "--sparse",
                    UPSTREAM_REPO, str(checkout)], check=True)
    subprocess.run(git + ["sparse-checkout", "set", "dwc-dp"], check=True)
    subprocess.run(git + ["checkout", "--quiet", ref], check=True)
    commit = subprocess.run(git + ["rev-parse", "HEAD"], check=True,
                            capture_output=True, text=True).stdout.strip()
    return checkout, commit


def copy_version(source, dest, table_schemas_url):
    """Copy the profile and table schemas, rewriting each table schema's relative url."""
    if (source / PROFILE).exists():
        shutil.copyfile(source / PROFILE, dest / PROFILE)
    else:
        print(f"Warning: no {PROFILE} in upstream {source.name}")

    table_schemas = sorted((source / "table-schemas").glob("*.json"))
    if not table_schemas:
        sys.exit(f"Error: no table schemas found in upstream {source}/table-schemas")

    (dest / "table-schemas").mkdir(parents=True)
    for schema in table_schemas:
        text = schema.read_text(encoding="utf-8")
        text, count = RELATIVE_URL.subn(f'"url": "{table_schemas_url}', text)
        if count != 1:
            sys.exit(f"Error: expected one relative url in {schema.name}, found {count}")
        (dest / "table-schemas" / schema.name).write_text(text, encoding="utf-8")

    return len(table_schemas)


def write_index(dest, metadata):
    builder = load_index_builder()
    table_schemas = builder.build_index(dest / "table-schemas", "*.json", set())

    index = dict(metadata)
    index["tableSchemas"] = table_schemas

    with (dest / "index.json").open("w", encoding="utf-8") as f:
        json.dump(index, f, indent=2, ensure_ascii=False)
        f.write("\n")
    return index


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
        description="Copy a DwC-DP version from tdwg/rs.tdwg.org into this repository.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    p.add_argument("version", help="DwC-DP version, the folder name upstream (e.g. 1.0)")
    p.add_argument("--issued", required=True, help="Release date of the version, YYYY-MM-DD")
    p.add_argument("--ref", default="master", help="Upstream branch, tag or commit (default: master)")
    p.add_argument("--profile-url",
                   help="Profile URL for index.json (default: https://rs.tdwg.org/dwc-dp/<version>/dwc-dp-profile.json)")
    p.add_argument("--not-latest", dest="is_latest", action="store_false",
                   help="Set isLatest to false and leave the registry unchanged")
    p.add_argument("--force", action="store_true",
                   help="Replace the profile, table schemas and index.json if the folder already exists")
    return p.parse_args()


def main():
    args = parse_args()

    try:
        if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", args.issued):
            raise ValueError
        datetime.date.fromisoformat(args.issued)
    except ValueError:
        sys.exit(f"Error: --issued must be a date as YYYY-MM-DD, got {args.issued}")
    if shutil.which("git") is None:
        sys.exit("Error: git is required but was not found")
    if not REGISTRY.exists():
        sys.exit(f"Error: {REGISTRY} not found, run this script from the repository root")

    dest = DEST / args.version
    base_url = RS_URL + dest.as_posix() + "/"

    if dest.exists() and not args.force:
        sys.exit(f"Error: {dest} already exists, pass --force to replace it")

    with tempfile.TemporaryDirectory() as workdir:
        try:
            checkout, commit = fetch_upstream(args.ref, workdir)
        except subprocess.CalledProcessError:
            sys.exit(f"Error: could not fetch {args.ref} from {UPSTREAM_REPO}, see the git output above")
        source = checkout / "dwc-dp" / args.version
        if not source.is_dir():
            available = sorted(p.name for p in (checkout / "dwc-dp").iterdir() if p.is_dir())
            sys.exit(f"Error: no dwc-dp/{args.version} upstream at {args.ref}, available: {available}")

        # Build the new files in a staging folder, so dest is only touched once everything succeeded
        staging = Path(workdir) / "staging"
        staging.mkdir()
        count = copy_version(source, staging, base_url + "table-schemas/")

        metadata = {
            "identifier": PACKAGE_METADATA["identifier"],
            "url": base_url + "index.json",
            "profile": args.profile_url or f"https://rs.tdwg.org/dwc-dp/{args.version}/{PROFILE}",
            "name": PACKAGE_METADATA["name"],
            "version": args.version,
            "title": PACKAGE_METADATA["title"],
            "shortTitle": PACKAGE_METADATA["shortTitle"],
            "description": PACKAGE_METADATA["description"],
            "issued": args.issued,
            "isLatest": args.is_latest,
        }
        index = write_index(staging, metadata)

        if dest.exists():
            shutil.rmtree(dest / "table-schemas", ignore_errors=True)
            (dest / PROFILE).unlink(missing_ok=True)
            (dest / "index.json").unlink(missing_ok=True)
        dest.mkdir(parents=True, exist_ok=True)
        for path in staging.iterdir():
            shutil.move(str(path), str(dest / path.name))

    version_file = dest / "version.json"
    if not version_file.exists():
        version = {"version": args.version, "latestCompatibleVersion": args.version}
        version_file.write_text(json.dumps(version, indent=2) + "\n", encoding="utf-8")

    if args.is_latest:
        update_registry(index)

    print(f"Copied DwC-DP {args.version} ({count} table schemas) from tdwg/rs.tdwg.org "
          f"{commit[:7]} into {dest}")
    if args.is_latest:
        print(f"Updated {REGISTRY}")
        print("Now set isLatest to false and update latestCompatibleVersion in older versions, "
              "then run data-packages-validation-checks.py")


if __name__ == "__main__":
    main()
