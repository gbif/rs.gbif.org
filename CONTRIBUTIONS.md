## Contributions are welcome through pull requests.

### Proposing a new extension
If you are proposing a new extension, please add the extension definition xml to the sandbox folder: https://github.com/gbif/rs.gbif.org/tree/master/sandbox/extension
The filename should have the version (date) appended, e.g. "fungaltraits_YYYY-MM-DD.xml".
Do the pull request.

### Adding attributes to an existing extension
If you are suggesting additional attributes for an existing extension you should duplicate the extension and append the current date to the filename of the duplicate, "speciesprofile_YYYY-MM-DD.xml".
Add your suggestions to the new version and place it in the sandbox folder: https://github.com/gbif/rs.gbif.org/tree/master/sandbox/extension
Do the pull request.

### Reviewing/testing your contribution
Once your pull request has been merged, IPTs running in test mode have access to the new version.
Go to the IPTs administration page and choose "Core Types and Extensions". Scroll to "Synchronise Extensions and Vocabularies" and click the "Synchronize" button. Please allow an hour for the IPT to be aware of the new extension/version.
The new extension / new version will now be available for review/test.

### From review/test to production
When the new extension/version has been tested, you can do a new pull request to get it into production. Simply copy the extension xml from the sandbox folder into the extensions folder https://github.com/gbif/rs.gbif.org/tree/master/extension, and place it in the appropriate subfolder.
Do a pull request. When this pull request has been merged, the new extension/version will be available for IPTs when they synchronize as described above.