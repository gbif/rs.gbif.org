#!/usr/bin/env python3
#
# Script to build DWCA XML definition files.
# Based on an earlier script by John Wieczorek: https://github.com/tdwg/dwc/blob/8ea35d29e321c623002475744c080080ded9e388/build/xml/build_extension.py

import re
import requests
import json
import os
import sys
import pandas as pd
import html
from datetime import date

import dwcterms

# -----------------
# Configuration section
# -----------------
languages = ['en', 'ar', 'cs', 'de', 'es', 'fr', 'ja', 'ko', 'pt', 'ru', 'zh-Hant']

# -----------------
# Command line arguments
# -----------------
arg_vals = sys.argv[1:]
opts = [opt for opt in arg_vals if opt.startswith('-')]
args = [arg for arg in arg_vals if not arg.startswith('-')]

# Only allow creating a new version (new file) if this flag is present.
permitNewVersion = '--permit-new-version' in opts

scriptDir = os.path.dirname(os.path.realpath(__file__))
repoRoot = os.path.dirname(scriptDir)
ac = False


def is_missing(value):
    """Return True for None, pandas NaN/NA, or an empty string."""
    if value is None:
        return True
    if isinstance(value, str):
        return value == ''
    try:
        return bool(pd.isna(value))
    except (TypeError, ValueError):
        return False


def xml_escape(value):
    """Convert a scalar value to XML-safe text; missing values become empty."""
    if is_missing(value):
        return ''
    return html.escape(str(value))

# -----------------
# Command line arguments
# -----------------

arg_vals = sys.argv[1:]
opts = [opt for opt in arg_vals if opt.startswith('-')]
args = [arg for arg in arg_vals if not arg.startswith('-')]

# This is the base URL for raw files from the branch of the repo that has been pushed to GitHub
# Read the value that follows --rs-path in the raw argument list. (Indexing args by the
# position of the flag within opts only worked when --rs-path was the first flag given.)
if '--rs-path' in arg_vals:
    rsPathIndex = arg_vals.index('--rs-path') + 1
    if rsPathIndex >= len(arg_vals):
        raise SystemExit('--rs-path requires a path argument')
    rsPath = arg_vals[rsPathIndex]
else:
    rsPath = None

class DwcaXml:
    def __init__(self, terms, xmlTemplate, xmlTerms=None, gbifAlternatives=None):
        """
        Tables of terms.

        Keyword arguments:
        terms -- the loaded dwcterms term lists
        xmlTemplate -- XML header
        xmlTerms -- terms to include
        gbifAlternatives -- vocabulary server URL template
        """

        self.terms = terms
        self.xmlTemplate = xmlTemplate
        self.xmlTerms = xmlTerms
        self.gbifAlternatives = gbifAlternatives
        pass

    def t_xml(self, row, key, l):
        """
        Retrieve the value of the given term in the given locale, escaped for XML.
        """
        if key+l in row and not is_missing(row[key+l]):
            return xml_escape(row[key+l])
        else:
            return None

    def create_extension_xml(self, languages, file_template):
        """Build a Darwin Core Extension XML file"""

        # Use ratification date in filenames for stability.
        ratification_date = self.terms.document_configuration_yaml['doc_modified']

        file_output = os.path.join(
            repoRoot,
            file_template + ratification_date + ".xml"
        )
        os.makedirs(os.path.dirname(file_output), exist_ok=True)

        if not os.path.isfile(file_output) and not permitNewVersion:
            raise Exception("Standard has a new version, but %s doesn't exist.  Manual review/sandbox required, e.g. touch the file %s and rerun." % (file_output, file_output))

        with open(file_output, 'w', encoding='utf-8') as output_file:
            # Open the XML declaration file
            template_file = open(scriptDir + '/' + self.xmlTemplate, 'r')
            # Write the entire XML declaration section to the output file
            header = template_file.read()
            header = header.replace('{issued_date}', date.today().isoformat())
            output_file.write(header)

            # Process the list of terms for the extension combining properties from the
            # extension term list with the properties of the term definitions from Darwin
            # Core.

            # Load the terms from the Extension term list file
            termlist = pd.read_csv(
                scriptDir + '/' + self.xmlTerms,
                keep_default_na=False
            )
            previous_group = 'None'

            for ext_index,ext_item in termlist.iterrows():
                # Process each row in the extension term list. The file must have the
                # following fields in the given order:
                #     class,iri,type,thesaurus,description,comments,examples,required
                # 1) The iri field must be populated.
                # 2) If there is supposed to be a datatype other than string for the term,
                #    that type must be provided.
                # 3) If there is supposed to be a controlled vocabulary for the term, the
                #    URL to the location of the controlled vocabulary must be provided.
                # 4) If there is supposed to be a definition, comment, or example for the
                #    term that differs from that in the standard, the custom value must be
                #    provided.
                # 5) If a term is required to be mapped to a field, the column 'required'
                #    must be populated with 'true'.

                # Find the term from the rs.tdwg.org data
                term_iri = str(ext_item['iri']).strip()

                try:
                    term_data = self.terms.get_term(term_iri)
                except (ValueError, IndexError) as exc:
                    raise ValueError(
                        f"Unable to build extension field {ext_index}. "
                        f"The IRI from {self.xmlTerms} was not found in the loaded term metadata:\n"
                        f"  {term_iri!r}"
                    ) from exc

                # Always set the group based on the value in the Extension term list
                group = ext_item['group']

                # Get the term name, namespace etc
                name = term_data['term_localName']
                namespace = term_data['pref_ns_uri']

                # The qualified name normally is the namespace plus the term's local name,
                # which is what the 'iri' column of the Extension term list file holds.
                # Some borrowed namespaces mint opaque IRIs that do not contain the name
                # used as a Darwin Core Archive column heading - MIxS identifies samp_name
                # as https://w3id.org/mixs/0001107 - so those terms carry the real IRI in
                # the optional 'qualname' column and use 'iri' only as the lookup key.
                qualName = ext_item['qualname'] if 'qualname' in ext_item.index else ''
                if is_missing(qualName) or not str(qualName).strip():
                    qualName = ext_item['iri']
                else:
                    qualName = str(qualName).strip()

                # The datatype, if it is other than 'string' must come from the type field
                # in the Extension term list file
                datatype = ext_item['type']

                # The thesaurus, if there is one, must come from the type field in the
                # Extension term list file
                thesaurus = ext_item['thesaurus']

                # The English label for the term
                label = term_data['label']

                # Create a dc:relation to the URL for the term in the Quick Reference
                # Guide, if there is one
                dc_relation = None
                if namespace == 'http://rs.tdwg.org/dwc/terms/':
                    # Example: https://dwc.tdwg.org/terms/#dwc:behavior
                    dc_relation = f'https://dwc.tdwg.org/terms/#dwc:{name}'
                elif namespace == 'http://rs.tdwg.org/dwc/iri/':
                    # Example: https://dwc.tdwg.org/terms/#dwciri:recordedBy
                    dc_relation = f'https://dwc.tdwg.org/terms/#dwciri:{name}'
                elif namespace == 'http://purl.org/dc/elements/1.1/':
                    # Example: https://dwc.tdwg.org/terms/#dc:type
                    dc_relation = f'https://dwc.tdwg.org/terms/#dc:{name}'
                elif namespace == 'http://purl.org/dc/terms/':
                    # Example: https://dwc.tdwg.org/terms/#dcterms:references
                    dc_relation = f'https://dwc.tdwg.org/terms/#dcterms:{name}'
                elif namespace == 'http://purl.org/chrono/terms/':
                    # Example: https://chrono.tdwg.org/terms/#chrono:materialDated
                    dc_relation = f'https://chrono.tdwg.org/terms/#chrono:{name}'
                elif namespace == 'http://rs.tdwg.org/eco/terms/':
                    # Example: https://eco.tdwg.org/terms/#eco:samplingPerformedBy
                    dc_relation = f'https://eco.tdwg.org/terms/#eco:{name}'
                elif namespace == 'https://w3id.org/mixs/':
                    # MIxS term pages are keyed by the numeric identifier, which is the
                    # local part of the real term IRI rather than the name used as a column
                    # heading. Example for samp_name, MIXS:0001107:
                    # https://genomicsstandardsconsortium.github.io/mixs/0001107/
                    mixs_id = str(qualName).rstrip('/').rsplit('/', 1)[-1]
                    dc_relation = f'https://genomicsstandardsconsortium.github.io/mixs/{mixs_id}/'
                elif namespace == 'http://data.ggbn.org/schemas/ggbn/terms/':
                    # Example: https://terms.tdwg.org/wiki/ggbn:concentration
                    dc_relation = f'https://terms.tdwg.org/wiki/ggbn:{name}'
                elif namespace in ('http://rs.gbif.org/terms/', 'http://rs.gbif.org/terms/miqe/'):
                    # GBIF-minted terms have no separate quick reference guide page.
                    dc_relation = ''
                # Fall back to an empty attribute rather than the literal string 'None'
                # for any namespace not listed above.
                if dc_relation is None:
                    dc_relation = ''
                # Different for the AC documentation
                if ac:
                    prefix = term_data['pref_ns_prefix']
                    dc_relation = f'http://rs.tdwg.org/ac/doc/termlist/#{prefix}_{name}'

                # Get the term definition (dc:description) from the description field of
                # the Extension term list file. Otherwise use the description from the standard.
                dc_description = ext_item['description']
                if is_missing(dc_description):
                    dc_description = term_data['rdfs_comment']

                # Get the term comments from the description field of the Extension
                # term list file. Otherwise use the comments from the standard.
                comments = ext_item['comments']
                if is_missing(comments):
                    comments = term_data['dcterms_description']

                # Get the term examples from the description field of the Extension term
                # list file. Otherwise use the examples from the standard.
                examples = ext_item['examples']
                if is_missing(examples):
                    examples = term_data['examples']

                # Set the attribute 'required' to 'false' unless it is provided in the
                # Extension term list file
                required = ext_item['required']
                if is_missing(required) or not required:
                    required = 'false'
                else:
                    required = 'true'

                # HTML encode description, comment, and examples
                dc_description = xml_escape(dc_description)
                comments = xml_escape(comments)
                examples = xml_escape(examples)

                # Construct the property entry for the output file
                s = f"    <property group='{group}' "
                s += f"name='{name}' "
                if datatype is not None and datatype.strip()!='':
                    s += f"type='{datatype}' "
                if thesaurus is not None and thesaurus.strip()!='':
                    s += f"thesaurus='{thesaurus}' "
                s += f"namespace='{namespace}' "
                s += f"qualName='{qualName}' "
                s += f"label='{label}' "
                s += f"dc:relation='{dc_relation}' "
                s += f"dc:description='{dc_description}' "
                if comments:
                    s += f"comments='{comments}' "
                if examples:
                    s += f"examples='{examples}' "
                s += f"required='{required}'"

                # Add translations
                hasLang = False
                for lang in languages:
                    # Currently the IPT only supports Traditional Chinese with the code zh.
                    if lang == 'en':
                        continue
                    elif lang == 'zh-Hant':
                        xmllang = 'zh'
                    elif lang == 'zh-Hans':
                        continue
                    else:
                        xmllang = lang

                    l_label = self.t_xml(term_data, 'label_', lang)
                    l_description = self.t_xml(term_data, 'rdfs_comment_', lang)
                    l_comments = self.t_xml(term_data, 'dcterms_description_', lang)
                    l_examples = self.t_xml(term_data, 'examples_', lang)

                    if l_label is not None or l_comments is not None or l_description is not None or l_examples is not None:
                        if not hasLang:
                            s += ">\n"
                            hasLang = True

                        s += f"      <translation xml:lang='{xmllang}'"
                        if l_label is not None:
                            s += f" label='{l_label}'"
                        if l_comments is not None:
                            s += f" comments='{l_comments}'"
                        if l_examples is not None:
                            s += f" examples='{l_examples}'"
                        if l_description is not None:
                            s += f" dc:description='{l_description}'"
                        s += "/>\n"
                    #else:
                    #    with pd.option_context('display.max_rows', None, 'display.max_columns', None):
                    #        print("No translations in "+lang, term_data)

                if hasLang:
                    s += "    </property>\n"
                else:
                    s += "/>\n"

                if group != previous_group:
                    output_file.write(f'\n    <!-- {group} -->\n')

                output_file.write(s)
                previous_group = group

            output_file.write("</extension>\n")
            output_file.close()

    def create_vocabulary_xml(self, languages, file_template):
        """Build an Darwin Core Vocabulary XML file

        Parameters
        -----------
        file_output : str
            The relative path to the file to write the resulting file.
            (e.g., "vocabulary/dwc/pathway_")
        """

        # Use ratification date in filenames for stability.
        ratification_date = self.terms.document_configuration_yaml['doc_modified']

        file_output = os.path.join(
            repoRoot,
            file_template + ratification_date + ".xml"
        )
        os.makedirs(os.path.dirname(file_output), exist_ok=True)

        if not os.path.isfile(file_output) and not permitNewVersion:
            raise Exception("Standard has a new version, but %s doesn't exist.  Manual review/sandbox required." % file_output)

        with open(file_output, 'w', encoding='utf-8') as output_file:
            # Open the XML declaration file
            template_file = open(scriptDir + '/' + self.xmlTemplate, 'r')
            # Write the entire XML declaration section to the output file
            header = template_file.read()
            header = header.replace('{issued_date}', date.today().isoformat())
            output_file.write(header)
            output_file.write("\n")

            # Process each term in the vocabulary
            for term_index,term in self.terms.terms_sorted_by_localname.iterrows():
                name = term['term_localName']
                namespace = term['pref_ns_uri']
                qualName = term['term_iri']
                controlled_value_string = term['controlled_value_string']
                dc_issued = term['term_created']
                dc_title = xml_escape(term['label'])
                dc_description = xml_escape(term['definition'])
                comments = xml_escape(term['notes'])
                usage = xml_escape(term['usage'])

                if controlled_value_string == '':
                    continue

                s  = f"  <concept"
                s += f"\n    dc:identifier='{controlled_value_string}'"
                s += f"\n    dc:URI='{qualName}'"
                s += f"\n    dc:subject='{qualName}'"
                s += f"\n    dc:relation='https://doi.org/10.3897/biss.3.38084'"
                s += f"\n    dc:issued='{dc_issued}'"
                s += f"\n    dc:description='{dc_description}'"
                if comments:
                    s += f"\n    comments='{comments}'"
                s += f">\n"

                s += f"    <preferred>\n"
                for lang in languages:
                    if 'label_'+lang in term:
                        title_lang = xml_escape(term['label_'+lang])
                        # Currently the IPT only supports Traditional Chinese with the code zh.
                        if lang == 'zh-Hant':
                            lang = 'zh'
                        elif lang == 'zh-Hans':
                            continue
                        if title_lang.strip() != '':
                            s += f"      <term dc:source='Darwin Core' dc:title='{title_lang}' xml:lang='{lang}'/>\n"
                s += f"    </preferred>\n"

                # Fetch alternative words for this term from the GBIF vocabulary server
                alternatives = requests.get(self.gbifAlternatives % controlled_value_string)
                if (alternatives.status_code == 200):
                    alternatives_json = alternatives.json()['results']
                    present = False
                    for alt in alternatives_json:
                        if not present:
                            s += f"    <alternative>\n"
                            present = True
                        title = xml_escape(alt['value'])
                        lang = alt['language'].split('-')[0]
                        s += f"      <term dc:source='GBIF Vocabulary Server' dc:title='{title}' xml:lang='{lang}'/>\n"
                    if present:
                        s += f"    </alternative>\n"

                s += f"  </concept>\n"
                s += f"\n"

                output_file.write(s)

            output_file.write("</thesaurus>\n")
            output_file.close()

# Darwin Core
dwc = dwcterms.DwcTerms(
    termLists = ['terms', 'dc-for-dwc', 'dcterms-for-dwc', 'ac-for-dwc'],
    docMetadataFilePath = 'dwc_doc_list/',
    rsPath = rsPath)

# Occurrence Core
dwc_xml = DwcaXml(
    terms = dwc,
    xmlTemplate = "xml/occurrence_core.tmpl",
    xmlTerms = "xml/occurrence_core_list.csv"
    )
dwc_xml.create_extension_xml(languages, 'sandbox/core/dwc_occurrence_')

# Darwin Core Taxon Core
dwc_xml = DwcaXml(
    terms = dwc,
    xmlTemplate = "xml/taxon_core.tmpl",
    xmlTerms = "xml/taxon_core_list.csv"
    )
dwc_xml.create_extension_xml(languages, 'sandbox/core/dwc_taxon_')

# Darwin Core Event Core
dwc_xml = DwcaXml(
    terms = dwc,
    xmlTemplate = "xml/event_core.tmpl",
    xmlTerms = "xml/event_core_list.csv"
    )
dwc_xml.create_extension_xml(languages, 'sandbox/core/dwc_event_')

# Darwin Core Resource Relationship extension
dwc_xml = DwcaXml(
    terms = dwc,
    xmlTemplate = "xml/resource_relationship.tmpl",
    xmlTerms = "xml/resource_relationship_list.csv"
    )
dwc_xml.create_extension_xml(languages, 'sandbox/extension/dwc/resource_relationship_')

# Darwin Core Measurements or Facts extension
dwc_xml = DwcaXml(
    terms = dwc,
    xmlTemplate = "xml/measurements_or_facts.tmpl",
    xmlTerms = "xml/measurements_or_facts_list.csv"
    )
dwc_xml.create_extension_xml(languages, 'sandbox/extension/dwc/measurements_or_facts_')

# Darwin Core Identification History extension
dwc_xml = DwcaXml(
    terms = dwc,
    xmlTemplate = "xml/identification_history.tmpl",
    xmlTerms = "xml/identification_history_list.csv"
    )
dwc_xml.create_extension_xml(languages, 'sandbox/extension/dwc/identification_history_')


# Humboldt
eco = dwcterms.DwcTerms(
    termLists = ['terms', 'humboldt'],
    docMetadataFilePath = 'dwc_doc_eco/',
    rsPath = rsPath)
# Humboldt Extension
eco_xml = DwcaXml(
    terms = eco,
    xmlTemplate = "xml/humboldt_eco.tmpl",
    xmlTerms = "xml/humboldt_eco_list.csv"
    )
eco_xml.create_extension_xml(languages, 'sandbox/extension/eco/humboldt_')


# Chronometric Age
chrono = dwcterms.DwcTerms(
    termLists = ['terms', 'chronometricage'],
    docMetadataFilePath = 'dwc_doc_chrono/',
    rsPath = rsPath)

# Chronometric Age Extension
chrono_xml = DwcaXml(
    terms = chrono,
    xmlTemplate = "xml/chronometric_age.tmpl",
    xmlTerms = "xml/chronometric_age_list.csv"
    )
chrono_xml.create_extension_xml(
    languages,
    'sandbox/extension/chrono/chronometric_age_'
    )


# Establishment Means Vocabulary
em = dwcterms.DwcTerms(
    termLists = ['establishmentMeans'],
    docMetadataFilePath = 'dwc_doc_em/',
    rsPath = rsPath)
em_xml = DwcaXml(
    terms = em,
    xmlTemplate = "xml/establishment_means.tmpl",
    gbifAlternatives = "https://api.gbif.org/v1/vocabularies/EstablishmentMeans/concepts/%s/alternativeLabels")
em_xml.create_vocabulary_xml(languages, 'sandbox/vocabulary/dwc/establishment_means_')


# Degree of Establishment Vocabulary
em = dwcterms.DwcTerms(
    termLists = ['degreeOfEstablishment'],
    docMetadataFilePath = 'dwc_doc_doe/',
    rsPath = rsPath)
em_xml = DwcaXml(
    terms = em,
    xmlTemplate = "xml/degree_of_establishment.tmpl",
    gbifAlternatives = "https://api.gbif.org/v1/vocabularies/DegreeOfEstablishment/concepts/%s/alternativeLabels")
em_xml.create_vocabulary_xml(languages, 'vocabulary/dwc/degree_of_establishment_')


# Pathway Vocabulary
em = dwcterms.DwcTerms(
    termLists = ['pathway'],
    docMetadataFilePath = 'dwc_doc_pw/',
    rsPath = rsPath)
em_xml = DwcaXml(
    terms = em,
    xmlTemplate = "xml/pathway.tmpl",
    gbifAlternatives = "https://api.gbif.org/v1/vocabularies/Pathway/concepts/%s/alternativeLabels")
em_xml.create_vocabulary_xml(languages, 'vocabulary/dwc/pathway_')


# DNA derived data
# NOTE: this block must stay ABOVE the Audiovisual Core section. The module-global 'ac'
# is used both as a DwcTerms object and as a boolean flag consulted when building
# dc:relation, so anything added after it is built would silently get AC-style values.
dna = dwcterms.DwcTerms(
    termLists = ['terms', 'mixs-for-dna', 'miqe-for-dna', 'gbif-for-dna', 'ggbn-for-dna'],
    docMetadataFilePath = 'dwc_doc_dna/',
    rsPath = rsPath)
# DNA derived data Extension
dna_xml = DwcaXml(
    terms = dna,
    xmlTemplate = "xml/dna_derived_data.tmpl",
    xmlTerms = "xml/dna_derived_data_list.csv"
    )
dna_xml.create_extension_xml(languages, 'sandbox/extension/gbif/1.0/dna_derived_data_')


# Audiovisual Core
ac = dwcterms.DwcTerms(
    termLists = ['audubon', 'dc-for-ac', 'dcterms-for-ac', 'dwc-for-ac', 'exif-for-ac', 'Iptc4xmpExt-for-ac', 'mo-for-ac', 'photoshop-for-ac', 'xmp-for-ac', 'xmpRights-for-ac'],
    docMetadataFilePath = 'ac_doc_termlist/',
    rsPath = rsPath)
# Audiovisual Extension
ac_xml = DwcaXml(
    terms = ac,
    xmlTemplate = "xml/audiovisual.tmpl",
    xmlTerms = "xml/audiovisual_list.csv"
    )
ac = True
ac_xml.create_extension_xml(languages, 'extension/ac/audiovisual_')
ac = False
