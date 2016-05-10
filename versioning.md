# How to Version Extensions and Vocabularies on rs.gbif.org

This documents the versioning policy for extensions and vocabularies hosted on http://rs.gbif.org. It also provides detailed instructions on how to create new versions of extensions and vocabularies.

## Table of Contents
* [Rationale for Versioning](#versioning.md#rationale-for-versioning)
* [Extensions Versioning Policy](#)
  * [What types of changes require a new version of an extension to be created?](versioning.md#what-types-of-changes-require-a-new-version-of-an-extension-to-be-created)
  * [What types of changes do not require a new version of an extension to be created?](#)
  * [How to create a new version of an extension](versioning.md#how-to-create-a-new-version-of-a-vocabulary)
* [Vocabularies Versioning Policy](#)
  * [What types of changes require a new version of a vocabulary to be created?](#)
  * [What types of changes do not require a new version of a vocabulary to be created?](#)
  * [How to create a new version of a vocabulary](#)
  
## Rationale for Versioning
An extension is immutable by design and software tools confidently rely on this fact. 

To avoid breaking tools such as the IPT, authors are encouraged to produce new versions of extensions and vocabularies as per these guidelines.

The IPT automatically detects when new versions of installed extensions become available. When an IPT administrator upgrades an extension to a newer version, the IPT ensures that existing mappings to this extension don't break. It does this by safely removing or migrating mappings to terms that have been removed or replaced. In addition, it will ensure that any new terms that have been added to the extension are made available to map to.

## Extensions Versioning Policy 
### What types of changes require a new version of an extension to be created?

-  Adding or removing properties. Note properties are no longer marked as deprecated, they are simply removed from the new version.
-  Modifying the vocabulary or vocabulary version for a property
-  Changing a property from being non-required to being required
-  Modifying a property's data type

### What types of changes do not require a new version of an extension to be created?
 
-  Modifying a property's description
-  Modifying a property's translations
-  Modifying a property's examples
-  Modifying a property's group
-  Changing a property from being required to being non-required

### How to create a new version of an extension

New versions are first quarantined in the [sandbox](http://rs.gbif.org/sandbox/). This allows the new version to be tested and undergo additional modifications prior to release. The version will be moved to [production](http://rs.gbif.org) at the discretion of the GBIF Development team. To create a new version of an extension, please follow the instructions below. Don't worry, the GBIF Development team will remove all traces of the sandbox when moving an extension to production.

1. Set the <extension> element dc:issued attribute to the date of release. The date format must be YYYY-MM-DD, e.g. 2015-04-24.
2. The file name must include the issued date. The date format must by YYYY-MM-DD, e.g. dwc_event_2015-04-24.xml. 
3. Update the <extension> element dc:description attribute, appending a change summary of what is new in this version.
4. Remove all properties that have been deprecated since the last version.
5. Ensure the extension XML validates against the latest version of the GBIF extension schema, currently in the Sandbox at: http://rs.gbif.org/sandbox/schema/extension.xsd
6. Update the <property> thesaurus attribute with the new vocabulary version URL (if its version was updated). Chances are new vocabulary versions will be in the sandbox also, e.g. http://rs.gbif.org/sandbox/vocabulary/gbif/rank_2015-04-24.xml.xml 

## Vocabularies Versioning Policy
### What types of changes require a new version of a vocabulary to be created?

-  Adding or removing concepts. Note concepts are no longer marked as deprecated, they are simply removed from the new version.

### What types of changes do not require a new version of a vocabulary to be created?

-  Modifying a concept's description
-  Modifying a concept's translations

### How to create a new version of a vocabulary

New versions are first quarantined in the [sandbox](http://rs.gbif.org/sandbox/). This allows the new version to be tested and undergo additional modifications prior to release. The version will be moved to [production](http://rs.gbif.org) at the discretion of the GBIF Development team. To create a new version of a vocabulary, please follow the instructions below. Don't worry, the GBIF Development team will remove all traces of the sandbox when moving a vocabulary to production.

1. Set the <thesaurus> element dc:issued attribute to the date of release. The date format must be YYYY-MM-DD, e.g. 2015-04-24.
2. The file name must include the issued date. The date format must by YYYY-MM-DD, e.g. quantity_type_2015-04-24.xml. 
3. Update the <thesaurus> element dc:description attribute, appending a change summary of what is new in this version.
4. Remove all concepts that have been deprecated since the last version.
5. Ensure the extension XML validates against the latest version of the GBIF thesaurus schema, currently in the Sandbox at: http://rs.gbif.org/sandbox/schema/thesaurus.xsd
6. Update the <thesaurus> element dc:URI attribute with the accurrate unique address URL, e.g. http://rs.gbif.org/sandbox/vocabulary/gbif/quantityType20150424/
