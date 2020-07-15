[![Build Status](https://builds.gbif.org/job/rs.gbif.org/badge/icon)](https://builds.gbif.org/job/rs.gbif.org/)

# [rs.gbif.org](https://rs.gbif.org)
GBIF **R**epository of **S**chemas hosted at https://rs.gbif.org

## Build
The repository can be built locally.

```
git submodule update --init
./sync-extensions.py
```

(NB if an additional release of `eml-profile` is required, it should be added with a command like `git submodule add --name eml-profile-X.Y https://github.com/gbif/eml-profile.git schema/eml-gbif-profile/X.Y`.)

## Deploying
Deployment to rs.gbif.org uses rsync:
```
  rsync -nrlv --checksum --delete --exclude '.git*' ./ user@static.gbif.org:/var/www/html/rs/
```
This happens automatically for commits to the master branch, and by a daily cron trigger, on the Jenkins build server.

## Darwin Core Archive extensions and vocabularies
The folder [core](core) contains [IPT](https://www.gbif.org/ipt) XML definitions for [Darwin Core Archive](http://rs.tdwg.org/dwc/terms/guides/text/) core data files. [Production extensions](extension) and associated [vocabularies](vocabulary) are hosted here, as well as [sandbox](sandbox) definitions of those used by IPT test installations.

Instructions for how to create new versions of extensions and vocabularies can be found [here](versioning.md).

## Named Area Standards
The folder [areas](areas) lists geographic area standards and recommends a namespace prefix for each of them to be used as part of the [dwc:locationID](http://rs.tdwg.org/dwc/terms/locationID) in particular inside the [GNA Species Distribution Extension](http://rs.gbif.org/extension/gbif/1.0/distribution.xml)

## Conventions
Coding conventions and styles for IntelliJ and Eclipse.

## Dictionaries
Dictionaries for name parsing and finding.

## Schemas
XML schemas for extensions, vocabularies, EML, Dublin Core, etc.

## Templates
Crawling templates for DiGIR and BioCASe.

## Terms
Term definitions in RDF, including Darwin Core Term definitions translated into various languages.
