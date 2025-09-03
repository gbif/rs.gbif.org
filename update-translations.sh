#!/bin/bash

set -e

# Retrive DWC Terms python 'module'
curl -Ss --output scripts/dwcterms.py https://raw.githubusercontent.com/tdwg/dwc/refs/heads/master/build/dwcterms.py

# Update translations
if [[ -d ../tdwg/rs.tdwg.org ]]; then
    python3 scripts/build-xml.py --rs-path ../tdwg/rs.tdwg.org
else
    python3 scripts/build-xml.py
fi

# If an extension file has only the "issued" date changed, there's no need to release that.
# Undo the change in that case.
for i in $(git status --short | grep '^ M ' | awk '{print $2}'); do
    if [[ -z "$(git diff --numstat --ignore-matching-lines='^  dc:issued' $i)" ]]; then
        echo "No change in translations for $i"
        git checkout --quiet $i
    else
        echo "New/changed translations for $i"
    fi
done
