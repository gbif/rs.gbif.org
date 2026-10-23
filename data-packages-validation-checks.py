#!/usr/bin/env python3
#
# Data packages validation checks (executed in Jenkins).
# In the case of a PR is supposed to be run manually.
# Checks are:
# 1. Index and table schema files are valid JSON
# 2. All URLs are resolvable
# 3. Table schemas declarations are valid, all actual files are present. Table schemas maintained elsewhere
#    (DwC-DP, without a local table-schemas folder) are downloaded from their urls
# 4. Valid frictionless schema
# 5. No duplicate nodes in index.json
# 6. Compares primary properties (identifier, url, name) between index.json and table schema file
# 7. Foreign keys refer to existing table schemas and fields
# 8. Package versions: folder names, version.json, isLatest, latestCompatibleVersion and the registries
#

import json
import os
import re
import requests
import sys
from pathlib import Path
from frictionless import Schema

# Paths to the directories containing index.json files
directories_to_scan_sandbox = ['sandbox/data-packages', 'sandbox/experimental/data-packages']
directories_to_scan_prod = ['data-packages']

# Flag to track errors
error_found = False


def check_valid_json(file_path):
    global error_found
    try:
        with open(file_path, 'r') as f:
            json.load(f)
        return True
    except (json.JSONDecodeError, FileNotFoundError):
        print(f"Error: Invalid JSON or missing file: {file_path}")
        error_found = True
        return False


def check_urls_are_resolvable(package_data, skip_urls=()):
    global error_found

    def resolve_url(url):
        global error_found
        try:
            response = requests.head(url, allow_redirects=True, timeout=5)
            if response.status_code >= 400:
                # Might be a new declaration, check a directory path too
                relative_path = re.sub(r'^https?://rs\.gbif\.org/', '', url)
                if not os.path.exists(relative_path):
                    print(f"Error: Unreachable URL: {url}")
                    print(f"Error: File does not exist {relative_path}")
                    error_found = True
            # else:
            #     print(f"URL is valid: {url}")
        except requests.RequestException:
            print(f"Error: Error resolving URL: {url}")
            error_found = True

    def find_and_resolve_urls(data):
        if isinstance(data, dict):
            for key, value in data.items():
                if key == "url" and isinstance(value, str) and value not in skip_urls:
                    resolve_url(value)
                elif isinstance(value, (dict, list)):
                    find_and_resolve_urls(value)
        elif isinstance(data, list):
            for item in data:
                find_and_resolve_urls(item)

    find_and_resolve_urls(package_data)


def load_table_schemas(package_file_path, package_data):
    """
    Returns the table schemas of a package version by file name (e.g. agent.json), None for invalid ones, and whether
    they are local. They are read from the version's table-schemas folder or, for packages maintained elsewhere such
    as DwC-DP, downloaded from their urls.
    """
    global error_found

    table_schemas_dir = os.path.join(os.path.dirname(package_file_path), 'table-schemas')
    table_schemas = {}

    if os.path.exists(table_schemas_dir):
        for schema_file in sorted(f for f in os.listdir(table_schemas_dir) if f.endswith('.json')):
            schema_file_path = os.path.join(table_schemas_dir, schema_file)
            # check_valid_json reports invalid files
            if check_valid_json(schema_file_path):
                with open(schema_file_path, 'r') as f:
                    table_schemas[schema_file] = json.load(f)
            else:
                table_schemas[schema_file] = None
        return table_schemas, True

    for schema in package_data.get('tableSchemas', []):
        url = schema.get('url')
        if not isinstance(url, str) or not is_absolute_url(url):
            print(f"Error: Table schemas directory missing and table schema url is not absolute: {url}")
            error_found = True
            continue
        try:
            response = requests.get(url, timeout=30)
            response.raise_for_status()
            table_schemas[os.path.basename(url)] = response.json()
        except (requests.RequestException, ValueError) as e:
            print(f"Error: Can't download table schema {url}: {e}")
            table_schemas[os.path.basename(url)] = None
            error_found = True
    return table_schemas, False


def is_absolute_url(url):
    return re.match(r'^https?://', url) is not None


def check_table_schemas(package_file_path, package_data, table_schemas, local):
    global error_found

    print(f"Checking file: {package_file_path}")

    declared_schemas = []
    declared_schemas_map = {}
    # To check no duplicates in the index file
    table_schema_identifiers = set()
    table_schema_urls = set()
    table_schema_names = set()
    table_schema_titles = set()
    table_schema_descriptions = set()

    if "tableSchemas" in package_data:
        for schema in package_data['tableSchemas']:
            if 'identifier' in schema:
                if schema['identifier'] in table_schema_identifiers:
                    print(f"Error: Duplicate 'identifier' for table schema: {schema}")
                    error_found = True
                else:
                    table_schema_identifiers.add(schema['identifier'])
            else:
                print(f"Error: Missing 'identifier' for table schema: {schema}")
                error_found = True

            if 'name' in schema:
                if schema['name'] in table_schema_names:
                    print(f"Error: Duplicate 'name' for table schema: {schema}")
                    error_found = True
                else:
                    table_schema_names.add(schema['name'])
            else:
                print(f"Error: Missing 'name' for table schema: {schema}")
                error_found = True

            if 'title' in schema:
                if schema['title'] in table_schema_titles:
                    print(f"Error: Duplicate 'title' for table schema: {schema}")
                    error_found = True
                else:
                    table_schema_titles.add(schema['title'])
            else:
                print(f"Error: Missing 'title' for table schema: {schema}")
                error_found = True

            if 'description' in schema:
                if schema['description'] in table_schema_descriptions:
                    print(f"Warning: Duplicate 'description' for table schema: {schema}")
                else:
                    table_schema_descriptions.add(schema['description'])
            else:
                print(f"Warning: Missing 'description' for table schema: {schema}")

            if 'url' in schema:
                if schema['url'] in table_schema_urls:
                    print(f"Error: Duplicate 'url' for table schema: {schema}")
                    error_found = True
                else:
                    table_schema_urls.add(schema['url'])

                schema_file = os.path.basename(schema['url'])
                declared_schemas.append(schema_file)
                declared_schemas_map[schema_file.replace(".json", "")] = schema
            else:
                print(f"Error: Missing 'url' for table schema: {schema}")
                error_found = True

    if local:
        actual_schemas = list(table_schemas)
        missing_files = [schema for schema in declared_schemas if schema not in actual_schemas]
        extra_files = [schema for schema in actual_schemas if schema not in declared_schemas]

        if missing_files:
            print(f"Error: Missing table schema files: {missing_files}")
            error_found = True
        if extra_files:
            print(f"Warning: Extra table schema files in directory: {extra_files}")

    for schema_file, table_schema in table_schemas.items():
        if table_schema is None:
            error_found = True
            continue

        # check table schema file properties
        missing_keys = [key for key in ('identifier', 'url', 'name') if key not in table_schema]
        if missing_keys:
            print(f"Error: Missing {missing_keys} in table schema {schema_file} of {package_file_path}")
            error_found = True
            continue

        table_schema_name = table_schema['name']

        # Compare URLs from index.json and table-schema.json
        if table_schema_name in declared_schemas_map:
            declared_table_schema_url = declared_schemas_map[table_schema_name]['url']
            actual_table_schema_url = table_schema['url']
        else:
            print(f"Error: couldn't find table schema {table_schema_name}")
            error_found = True
            continue

        # Downloaded table schemas may have a relative url (DwC-DP), which the IPT replaces with the declared one
        if local or is_absolute_url(actual_table_schema_url):
            if declared_table_schema_url != actual_table_schema_url:
                print(f"Error: urls do not match for table schema {table_schema_name}. "
                      f"Declared: {declared_table_schema_url}, actual: {actual_table_schema_url}")
                error_found = True

        # Compare identifiers from index.json and table-schema.json
        declared_table_schema_identifier = declared_schemas_map[table_schema_name]['identifier']
        actual_table_schema_identifier = table_schema['identifier']

        if declared_table_schema_identifier != actual_table_schema_identifier:
            print(f"Error: identifiers do not match for table schema {table_schema_name}. "
                  f"Declared: {declared_table_schema_identifier}, actual: {actual_table_schema_identifier}")
            error_found = True

        # Compare names from index.json and table-schema.json
        declared_table_schema_name = declared_schemas_map[table_schema_name]['name']
        actual_table_schema_name = table_schema['name']

        if declared_table_schema_name != actual_table_schema_name:
            print(f"Error: names do not match for table schema {table_schema_name}. "
                  f"Declared: {declared_table_schema_name}, actual: {actual_table_schema_name}")
            error_found = True


def check_valid_frictionless(package_file_path, table_schemas):
    global error_found

    for schema_file, table_schema in table_schemas.items():
        if table_schema is None:
            continue
        try:
            Schema.from_descriptor(table_schema)
            # print(f"{schema_file}: Valid frictionless")
        except Exception as e:
            print(f"Error: Invalid frictionless table schema {schema_file} of {package_file_path}: {str(e)}")
            error_found = True


def find_package_files(directories):
    package_files = []
    for base_dir in directories:
        for root, _, files in os.walk(base_dir):
            if 'index.json' in files:
                package_file_path = os.path.join(root, 'index.json')
                package_files.append(package_file_path)
    return package_files


def check_foreign_keys(package_file, table_schemas):
    global error_found

    # print(f"Checking foreign keys for {package_file}")

    for schema_file, table_schema_json in table_schemas.items():
        # Invalid table schemas and missing names are reported by check_table_schemas
        if table_schema_json is None or 'name' not in table_schema_json:
            continue
        table_schema_name = table_schema_json['name']
        # print(f"Checking table schema {table_schema_name}")

        if "foreignKeys" in table_schema_json:
            for foreign_key in table_schema_json['foreignKeys']:
                fk_field = foreign_key['fields']
                fk_reference_resource = foreign_key['reference']['resource']
                fk_reference_field = foreign_key['reference']['fields']

                # empty resource is a self-reference
                if fk_reference_resource == '':
                    fk_reference_resource = table_schema_name

                # print(f"Foreign key: {fk_field} references "
                #       f"to {fk_reference_resource}/{fk_reference_field}")

                is_field_present = any(field['name'] == fk_field for field in table_schema_json['fields'])

                if not is_field_present:
                    print(f"Error: There is no field {fk_field} in the table schema {schema_file} of {package_file}")
                    error_found = True

                reference_table_schema_json = table_schemas.get(fk_reference_resource + ".json")

                if reference_table_schema_json is not None:
                    is_fk_reference_field_present = (any(field['name'] == fk_reference_field for field in reference_table_schema_json['fields']))

                    if not is_fk_reference_field_present:
                        print(f"Error: Foreign key {table_schema_name}/{fk_field} references non existing "
                              f"field {fk_reference_resource}/{fk_reference_field}")
                        error_found = True
                elif fk_reference_resource + ".json" not in table_schemas:
                    print(f"Error: Foreign key {table_schema_name}/{fk_field} references non existing "
                          f"table schema {fk_reference_resource}")
                    error_found = True


def find_package_versions(directories):
    # Version index files are laid out as <base>/<package name>/<version>/index.json
    package_versions = {}
    for base_dir in directories:
        for index_file in sorted(Path(base_dir).glob('*/*/index.json')):
            # Invalid index files are already reported by check_valid_json
            try:
                with open(index_file, 'r') as f:
                    index_data = json.load(f)
            except json.JSONDecodeError:
                continue

            version_file = index_file.parent / 'version.json'
            version_data = None
            version_invalid = False
            if version_file.exists():
                if check_valid_json(version_file):
                    with open(version_file, 'r') as f:
                        version_data = json.load(f)
                else:
                    version_invalid = True

            package_versions.setdefault(index_file.parent.parent.name, []).append(
                {'path': str(index_file), 'index': index_data, 'version': version_data,
                 'version_invalid': version_invalid})
    return package_versions


def check_package_versions(registry_file, directories):
    global error_found

    print(f"Checking package versions: {registry_file}")

    # An invalid registry file is already reported by check_valid_json
    try:
        with open(registry_file, 'r') as f:
            registry_data = json.load(f)
    except json.JSONDecodeError:
        return

    registry_entries = {}
    for entry in registry_data.get('dataPackages', []):
        if 'name' not in entry:
            print(f"Error: Registry entry without a name in {registry_file}: {entry.get('identifier')}")
            error_found = True
            continue
        if entry['name'] in registry_entries:
            print(f"Error: Duplicate registry entry for data package {entry['name']} in {registry_file}")
            error_found = True
        registry_entries[entry['name']] = entry

    package_versions = find_package_versions(directories)

    for name, versions in package_versions.items():
        versions_by_number = {}
        for v in versions:
            index_version = v['index'].get('version')
            dir_version = Path(v['path']).parent.name

            if v['index'].get('name') != name:
                print(f"Error: name {v['index'].get('name')} in {v['path']} does not match directory {name}")
                error_found = True
            if index_version != dir_version:
                print(f"Error: version {index_version} in {v['path']} does not match directory {dir_version}")
                error_found = True
            if index_version in versions_by_number:
                print(f"Error: Duplicate version {index_version} of data package {name}: "
                      f"{versions_by_number[index_version]['path']}, {v['path']}")
                error_found = True
            versions_by_number[index_version] = v

            # An invalid version.json is already reported by check_valid_json
            if v['version'] is None and not v['version_invalid']:
                print(f"Error: Missing version.json for {v['path']}")
                error_found = True
            elif v['version'] is not None and v['version'].get('version') != index_version:
                print(f"Error: version.json version {v['version'].get('version')} does not match "
                      f"index.json version {index_version} in {Path(v['path']).parent}")
                error_found = True

        # Exactly one version of a package is the latest
        latest = [v for v in versions if v['index'].get('isLatest') is True]
        if len(latest) != 1:
            print(f"Error: Data package {name} must have exactly one version with isLatest=true, "
                  f"found: {[v['path'] for v in latest]}")
            error_found = True

        # latestCompatibleVersion points to an existing version, which is its own latest compatible version
        for v in versions:
            if v['version'] is None:
                continue
            compatible = v['version'].get('latestCompatibleVersion')
            if compatible not in versions_by_number:
                print(f"Error: latestCompatibleVersion {compatible} of {name} {v['index'].get('version')} "
                      f"is not a known version of {name}")
                error_found = True
                continue
            compatible_version = versions_by_number[compatible]['version'] or {}
            if compatible_version.get('latestCompatibleVersion') != compatible:
                print(f"Error: latestCompatibleVersion of {name} {v['index'].get('version')} points to {compatible}, "
                      f"which itself points to {compatible_version.get('latestCompatibleVersion')}")
                error_found = True

        # The registry lists the latest version, identical to its index.json
        if name not in registry_entries:
            print(f"Error: Data package {name} is missing from {registry_file}")
            error_found = True
        elif len(latest) == 1 and registry_entries[name] != latest[0]['index']:
            print(f"Error: Registry entry for {name} in {registry_file} differs from {latest[0]['path']}")
            error_found = True

        for v in versions:
            url = v['index'].get('url', '')
            if url.startswith('http://'):
                print(f"Warning: Data package url uses http: {url}")
            if not url.endswith('/index.json'):
                print(f"Warning: Data package url does not point to index.json: {url}")

    for name in registry_entries:
        if name not in package_versions:
            print(f"Error: Registry entry {name} in {registry_file} has no version directories")
            error_found = True


# Validation: Check all package files and their schemas
registry_files = ['sandbox/data-packages/index.json', 'data-packages/index.json']
all_package_files = find_package_files(directories_to_scan_sandbox) + find_package_files(directories_to_scan_prod)

for package_file in all_package_files:
    # First, validate the JSON structure
    if not check_valid_json(package_file):
        continue  # Skip further checks for invalid JSON files

    # If JSON is valid, load and perform the remaining checks
    with open(package_file, 'r') as f:
        package_data = json.load(f)

    # Registries are checked in check_package_versions: each entry must be identical to the index.json of the latest
    # version, whose urls are checked here
    if package_file in registry_files:
        continue

    table_schemas, local = load_table_schemas(package_file, package_data)
    # Downloaded table schemas don't need their urls checked again
    downloaded_urls = [] if local else [schema.get('url') for schema in package_data.get('tableSchemas', [])]
    check_urls_are_resolvable(package_data, downloaded_urls)
    check_table_schemas(package_file, package_data, table_schemas, local)
    check_valid_frictionless(package_file, table_schemas)
    check_foreign_keys(package_file, table_schemas)

check_package_versions('sandbox/data-packages/index.json', directories_to_scan_sandbox)
check_package_versions('data-packages/index.json', directories_to_scan_prod)

if error_found:
    print("Validation failed. Please fix the issues above.")
    sys.exit(1)  # Exit with a non-zero code if errors were found

print("All validations passed.")
sys.exit(0)  # Exit successfully if no issues were found
