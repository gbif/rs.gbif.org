#!/bin/bash

set -e

# Retrive DWC Terms python 'module'
curl --output scripts/dwcterms.py https://raw.githubusercontent.com/tdwg/dwc/refs/heads/master/build/dwcterms.py

# Update translations
if [[ -d ../tdwg/rs.tdwg.org ]]; then
    python3 scripts/build-xml.py --rs-path ../tdwg/rs.tdwg.org
else
    python3 scripts/build-xml.py
fi
