## Data Packages

This section contains the data package schemas supported by the IPT, such as Camtrap DP. They let datasets be published in richer, multi-table formats beyond Darwin Core Archives.

The schemas are presented using [Frictionless Table Schema](https://specs.frictionlessdata.io/table-schema/) definitions.

### Where data packages live

| Folder | Registry | Used by |
|---|---|---|
| [`data-packages`](.) | [`data-packages/index.json`](index.json) | Production IPTs |
| [`sandbox/data-packages`](../sandbox/data-packages) | [`sandbox/data-packages/index.json`](../sandbox/data-packages/index.json) | Test IPTs |

New versions go into the sandbox and are copied to production once they have been tested in the IPT.

[`sandbox/experimental/data-packages`](../sandbox/experimental/data-packages) has been used occasionally for packages whose model was still being worked out. The DwC-DP 1.0_DEV pre-release is there, for historical reasons. It is listed in the sandbox registry like any other sandbox package. New packages and versions should normally go into `sandbox/data-packages`.

The `frictionless` folder holds a copy of the Frictionless Data Package JSON schema.

### Layout of a version

Each version of a package has its own folder, `<name>/<version>/`:

```
camtrap-dp/1.0/
├── index.json                    package descriptor (see below)
├── version.json                  version and latest compatible version
├── table-schemas/                one Frictionless Table Schema per table
│   ├── deployments.json
│   ├── media.json
│   └── observations.json
└── profile/
    └── camtrap-dp-profile.json   JSON Schema profile
```

The folder names must match the descriptor: `<name>` is the package `name`, and `<version>` is its `version`.

### `index.json`

The package descriptor. Its keys are:

- `identifier`: the package identifier. It is the same for all versions of a package, e.g. `http://rs.gbif.org/data-packages/camtrap-dp`.
- `url`: the absolute URL of this version (see [URLs](#urls)).
- `profile` (optional): the URL of a JSON Schema profile that data packages of this type must also validate against.
- `name`, `version`, `title`, `shortTitle`, `description`.
- `issued`: the release date of this version, `YYYY-MM-DD`.
- `isLatest`: `true` for the latest version of the package, `false` for all others.
- `tableSchemas`: one entry per file in `table-schemas/`, with its `identifier`, `url`, `name`, `title` and `description`. The `identifier`, `url` and `name` must match the table schema file.
- `tableSchemasRequirements` (optional): a JSON Schema fragment listing the tables a data package must contain, e.g. `{"allOf": [{"description": "...", "required": ["deployments", "media", "observations"]}]}`.

### Registries

The registry (`index.json` at the top of `data-packages` and `sandbox/data-packages`) is what the IPT reads. It has a `dataPackages` array with one entry per package. Each entry is an exact copy of the `index.json` of the package's latest version, so when a new version is released, its whole `index.json` replaces the old entry.

Older versions are not listed in the registry. They stay available at their own URLs.

### `version.json` and compatible versions

```json
{
  "version": "1.0",
  "latestCompatibleVersion": "1.0"
}
```

- `version` is the version of this folder.
- `latestCompatibleVersion` is the newest version of the package this version is compatible with.

Camtrap DP 1.0 is the latest version, so it points to itself. If a compatible Camtrap DP 1.1 were released, 1.0 would point to `1.1`.

The rules are:

- The latest version points to itself.
- Every other version points directly to a version that points to itself. There are no chains: when a new compatible version is released, update `latestCompatibleVersion` in all older versions that are compatible with it, not only in the previous one.
- A version that is not compatible with any newer version keeps pointing to itself.

### URLs

All URLs are absolute and point to rs.gbif.org, including each table schema's `url`, so a version folder cannot be moved without rewriting them. The exception is DwC-DP, whose table schemas are on rs.tdwg.org (see [Packages maintained elsewhere](#packages-maintained-elsewhere)).

- For new versions, the package `url` uses `https` and points to the version's `index.json`, e.g. `https://rs.gbif.org/sandbox/data-packages/camtrap-dp/1.1/index.json` for a future Camtrap DP 1.1.
- Table schema `url`s point to the file, e.g. `https://rs.gbif.org/sandbox/data-packages/camtrap-dp/1.1/table-schemas/deployments.json`.

Existing versions of Camtrap DP and ColDP use `http` and point the package `url` to the version folder (e.g. `http://rs.gbif.org/data-packages/camtrap-dp/1.0`). The validation checks report these as warnings.

### Releasing a new version

1. Create `<name>/<version>/` in `sandbox/data-packages`, with the table schemas in `table-schemas/`. Set the `url` in each table schema.
2. Create `index.json`, usually by copying the previous version's and updating it.
3. Create `version.json`, with `latestCompatibleVersion` set to the new version.
4. Set `isLatest` to `false` in the previous version's `index.json`.
5. Update `latestCompatibleVersion` in the `version.json` of every older version that is compatible with the new one.
6. Replace the package's entry in the registry with the new `index.json`.
7. Run the [validation checks](#validation).

To move a tested version to production, copy its folder into `data-packages`, rewrite all `url`s from `https://rs.gbif.org/sandbox/data-packages/` to `https://rs.gbif.org/data-packages/`, and follow steps 4 to 7 against the production folder and registry.

#### Packages maintained elsewhere

DwC-DP schemas are maintained by TDWG in [tdwg/rs.tdwg.org](https://github.com/tdwg/rs.tdwg.org/tree/master/dwc-dp) and published on rs.tdwg.org. They are not copied here: a DwC-DP version folder only has `index.json` and `version.json`, and the `url` of each table schema in `index.json` points to rs.tdwg.org, e.g. `https://rs.tdwg.org/dwc-dp/1.0/table-schemas/agent.json`. The IPT finds DwC-DP in the registry like any other package, and downloads the table schemas from there. Changes to the schemas should be made upstream.

The table schemas on rs.tdwg.org have a relative `url` (`table-schemas/agent.json`). The IPT replaces it with the `url` from `index.json`.

`index.json` is generated with [`sync-dwc-dp.py`](../sync-dwc-dp.py). Run it from the repository root with the version and its release date:

```
pip install requests
python3 sync-dwc-dp.py 1.0 --issued 2026-10-13
```

It needs network access. The script:

- downloads the profile from rs.tdwg.org (`https://rs.tdwg.org/dwc-dp/<version>/` by default; pass `--tdwg-url` for another location, e.g. a pre-release on the TDWG sandbox). The profile lists the table schemas;
- downloads the table schemas and generates `sandbox/data-packages/dwc-dp/<version>/index.json` from them, with the `identifier` `http://rs.tdwg.org/dwc/dwc-dp`, and the table schema `url`s and the `profile` on rs.tdwg.org;
- writes `version.json`, unless it already exists;
- replaces the `dwc-dp` entry in the sandbox registry.

It refuses to overwrite an existing `index.json` unless `--force` is given, e.g. to pick up upstream fixes to the same version. Pass `--not-latest` for a version that is not the latest; it then leaves the registry alone. Older versions are not touched: set their `isLatest` to `false` and update their `latestCompatibleVersion` by hand (steps 4 and 5 above), then run the validation checks.

The older DwC-DP versions in `sandbox/experimental` (0.1 and 1.0_DEV) are copies, with their own table schemas.

#### Generating `index.json` for local table schemas

For packages with their own table schemas, the `tableSchemas` list of `index.json` can be generated with [`build-dp-local-index-file.py`](../build-dp-local-index-file.py). It reads every file in a `table-schemas/` folder and copies its top-level keys (everything except the fields and keys), and takes the package metadata from a JSON file passed with `--meta`:

```
python3 build-dp-local-index-file.py sandbox/data-packages/camtrap-dp/1.1/table-schemas \
    -o sandbox/data-packages/camtrap-dp/1.1/index.json --meta meta.json
```

### Validation

[`data-packages-validation-checks.py`](../data-packages-validation-checks.py) checks the production and sandbox data packages. It runs on Jenkins, and should be run by hand before opening a pull request:

```
pip install requests frictionless
python3 data-packages-validation-checks.py
```

It needs network access, as it checks that every `url` resolves (URLs of files that are not deployed yet are checked against the local files instead). It checks that:

- all files are valid JSON, and all table schemas are valid Frictionless Table Schemas;
- the `tableSchemas` in each `index.json` match the files in `table-schemas/` (or, for DwC-DP, the files downloaded from their `url`s), and foreign keys refer to existing tables and fields;
- folder names, `index.json` and `version.json` agree on the package name and version;
- each package has exactly one version with `isLatest: true`, and its registry entry is identical to that version's `index.json`;
- every `latestCompatibleVersion` is an existing version that points to itself.
