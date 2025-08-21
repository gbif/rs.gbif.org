#!/bin/bash

set -e

# Retrive DWC Terms python 'module'
curl --output scripts/dwcterms.py https://raw.githubusercontent.com/tdwg/dwc/refs/heads/master/build/dwcterms.py

# Update translations
python3 scripts/build-xml.py
