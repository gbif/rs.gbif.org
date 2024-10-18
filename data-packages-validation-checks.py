#!/usr/bin/env python3
#
# Data packages validation checks (executed in Jenkins).
# In the case of a PR is supposed to be run manually.
# Checks are:
# 1. Index and table schema files are valid JSON
# 2. All URLs are resolvable
# 3. Table schemas declarations are valid, all actual files are present
# 4. No duplicate nodes in index.json
# 5. Compares primary properties (identifier, url, name) between index.json and table schema file
#

import json
import os
import re
import requests
import sys

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


def check_urls_are_resolvable(package_data):
    global error_found

    def resolve_url(url):
        global error_found
        try:
            response = requests.head(url, allow_redirects=True, timeout=5)
            if response.status_code >= 400:
                relative_path = re.sub(r'^https?://rs\.gbif\.org/', '', url)
                if not os.path.exists(relative_path):
                    print(f"Error: Unreachable URL: {url}")
                    print(f"Error: File does not exist {relative_path}")

                # Might be a new declaration, check a directory path
                error_found = True
            # else:
            #     print(f"URL is valid: {url}")
        except requests.RequestException:
            print(f"Error: Error resolving URL: {url}")
            error_found = True

    def find_and_resolve_urls(data):
        if isinstance(data, dict):
            for key, value in data.items():
                if key == "url" and isinstance(value, str):
                    resolve_url(value)
                elif isinstance(value, (dict, list)):
                    find_and_resolve_urls(value)
        elif isinstance(data, list):
            for item in data:
                find_and_resolve_urls(item)

    find_and_resolve_urls(package_data)


def check_table_schemas(package_file_path, package_data):
    global error_found

    # Skip a directory with the main index.json file
    if package_file_path == 'sandbox/data-packages/index.json' or package_file_path == 'data-packages/index.json':
        return

    print(f"Checking file: {package_file_path}")

    package_dir = os.path.dirname(package_file_path)
    table_schemas_dir = os.path.join(package_dir, 'table-schemas')

    if not os.path.exists(table_schemas_dir):
        print(f"Error: Table schemas directory missing: {table_schemas_dir}")
        error_found = True
        return False
    # else:
    #     print(f"Table schemas directory present: {table_schemas_dir}")

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

    actual_schemas = [f for f in os.listdir(table_schemas_dir) if f.endswith('.json')]

    missing_files = [schema for schema in declared_schemas if schema not in actual_schemas]
    extra_files = [schema for schema in actual_schemas if schema not in declared_schemas]

    if missing_files:
        print(f"Error: Missing table schema files: {missing_files}")
        error_found = True
    if extra_files:
        print(f"Warning: Extra table schema files in directory: {extra_files}")

    for schema_file in actual_schemas:
        schema_file_path = os.path.join(table_schemas_dir, schema_file)
        if not check_valid_json(schema_file_path):
            print(f"Error: Invalid table schema JSON: {schema_file_path}")
            error_found = True
        else:
            # check table schema file properties
            with open(schema_file_path, 'r') as f:
                table_schema = json.load(f)
                table_schema_name = table_schema['name']

                # Compare URLs from index.json and table-schema.json
                if table_schema_name in declared_schemas_map:
                    declared_table_schema_url = declared_schemas_map[table_schema_name]['url']
                    actual_table_schema_url = table_schema['url']
                else:
                    print(f"Error: couldn't find table schema {table_schema_name}")
                    error_found = True
                    return

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


def find_package_files(directories):
    package_files = []
    for base_dir in directories:
        for root, _, files in os.walk(base_dir):
            if 'index.json' in files:
                package_file_path = os.path.join(root, 'index.json')
                package_files.append(package_file_path)
    return package_files


# Validation: Check all package files and their schemas
all_package_files_sandbox = find_package_files(directories_to_scan_sandbox)
all_package_files_prod = find_package_files(directories_to_scan_prod)

for package_file in all_package_files_sandbox:
    # First, validate the JSON structure
    if not check_valid_json(package_file):
        continue  # Skip further checks for invalid JSON files

    # If JSON is valid, load and perform the remaining checks
    with open(package_file, 'r') as f:
        package_data = json.load(f)

    check_urls_are_resolvable(package_data)
    check_table_schemas(package_file, package_data)

for package_file in all_package_files_prod:
    # First, validate the JSON structure
    if not check_valid_json(package_file):
        continue  # Skip further checks for invalid JSON files

    # If JSON is valid, load and perform the remaining checks
    with open(package_file, 'r') as f:
        package_data = json.load(f)

    check_urls_are_resolvable(package_data)
    check_table_schemas(package_file, package_data)

if error_found:
    print("Validation failed. Please fix the issues above.")
    sys.exit(1)  # Exit with a non-zero code if errors were found

print("All validations passed.")
sys.exit(0)  # Exit successfully if no issues were found
