#!/usr/bin/env python3
#
# Run script manually to generate a new index.json
#

import json
import os

# Ask the user which environment to use
env = input("Which environment would you like to use? (prod/sandbox): ").strip().lower()

# Check the user's input and execute accordingly
if env == "prod":
    print("Running in the production environment...")
    # Paths to the directories containing index.json files (production)
    main_index_path = 'data-packages/index.json'
    directories_to_scan = ['data-packages']
elif env == "sandbox":
    print("Running in the sandbox environment...")
    # Paths to the directories containing index.json files (sandbox)
    main_index_path = 'sandbox/data-packages/index.json'
    directories_to_scan = ['sandbox/data-packages', 'sandbox/experimental/data-packages']
    # Add your sandbox environment logic here
else:
    print("Invalid input. Please enter 'prod' or 'sandbox'.")


def find_package_files(directories, main_index_path):
    package_files = []
    for base_dir in directories:
        for root, _, files in os.walk(base_dir):
            if 'index.json' in files:
                package_file_path = os.path.join(root, 'index.json')
                if package_file_path != main_index_path:
                    package_files.append(package_file_path)
    return package_files


def load_package_data(package_file_path):
    with open(package_file_path, 'r') as package_file:
        return json.load(package_file)


def load_main_index_file(main_index_path):
    if os.path.exists(main_index_path):
        try:
            with open(main_index_path, 'r') as main_index_file:
                return json.load(main_index_file)
        except json.JSONDecodeError:
            print(f"Warning: '{main_index_path}' is empty or invalid, initializing as an empty index.")
            return {"dataPackages": []}
    else:
        return {"dataPackages": []}


def update_main_index(main_index_data, package_data):
    package_identifier = package_data.get("identifier")

    for existing_package in main_index_data['dataPackages']:
        if existing_package.get("identifier") == package_identifier:
            existing_package.update(package_data)
            print(f"Updated package '{package_identifier}'.")
            return

    main_index_data['dataPackages'].append(package_data)
    print(f"Added new package '{package_identifier}'.")


all_package_files = find_package_files(directories_to_scan, main_index_path)

main_index_data = load_main_index_file(main_index_path)

# After validation, proceed with updating the main index
for package_file in all_package_files:
    package_data = load_package_data(package_file)

    if isinstance(package_data, dict) and "dataPackages" not in package_data:
        update_main_index(main_index_data, package_data)
    else:
        print(f"Warning: The package data from '{package_file}' is invalid or contains nested 'dataPackages'.")

# Write back the updated main index data
with open(main_index_path, 'w') as main_index_file:
    json.dump(main_index_data, main_index_file, indent=2)

print(f"Updated {main_index_path} with schema-specific packages from {directories_to_scan}.")
