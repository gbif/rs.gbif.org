#!/usr/bin/env python3
#
# Data packages validation checks
#

import json
import os
import requests
import sys

# Paths to the directories containing index.json files
directories_to_scan = ['sandbox/data-packages', 'sandbox/experimental/data-packages']

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
        try:
            response = requests.head(url, allow_redirects=True, timeout=5)
            if response.status_code >= 400:
                print(f"Error: Unreachable URL: {url}")
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
    if package_file_path == 'sandbox/data-packages/index.json':
        return

    package_dir = os.path.dirname(package_file_path)
    table_schemas_dir = os.path.join(package_dir, 'table-schemas')

    if not os.path.exists(table_schemas_dir):
        print(f"Error: Table schemas directory missing: {table_schemas_dir}")
        error_found = True
        return False
    # else:
    #     print(f"Table schemas directory present: {table_schemas_dir}")

    declared_schemas = []
    if "tableSchemas" in package_data:
        declared_schemas = [os.path.basename(schema['url']) for schema in package_data['tableSchemas']]

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


def find_package_files(directories):
    package_files = []
    for base_dir in directories:
        for root, _, files in os.walk(base_dir):
            if 'index.json' in files:
                package_file_path = os.path.join(root, 'index.json')
                package_files.append(package_file_path)
    return package_files


# Validation: Check all package files and their schemas
all_package_files = find_package_files(directories_to_scan)

for package_file in all_package_files:
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
