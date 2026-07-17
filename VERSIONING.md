# Versioning

This document explains how to update the project version for future releases.

## Single Source of Truth

The application version is defined in a single location:

```
backend/version.py
```

This file contains:
- `APP_VERSION` - current version string (e.g. "2.5.0")
- `RELEASE_NAME` - release codename (e.g. "RCON Edition")
- `BUILD_DATE` - release date in YYYY-MM-DD format

All other parts of the project import from this file. Never hardcode version numbers elsewhere.

## Version Bump Rules

### Patch version (2.5.0 -> 2.5.1)

Use for bug fixes and small corrections that do not add new functionality.

```
APP_VERSION = "2.5.1"
```

### Minor version (2.5.0 -> 2.6.0)

Use for new features and improvements that remain backward compatible.

```
APP_VERSION = "2.6.0"
RELEASE_NAME = "New Feature Name"
BUILD_DATE = "YYYY-MM-DD"
```

### Major version (2.x -> 3.0)

Use for breaking changes and incompatible API changes.

```
APP_VERSION = "3.0.0"
RELEASE_NAME = "Major Feature Name"
BUILD_DATE = "YYYY-MM-DD"
```

## Steps to Release

1. Update `backend/version.py` with the new version, release name, and build date.
2. Update `CHANGELOG.md` with the changes for the new version.
3. Update `ROADMAP.md` if planning new future versions.
4. Update `README.md` with the new version information.
5. Run tests to ensure everything works:
   ```bash
   pytest -q backend/tests
   ```
6. Commit the changes with a message like:
   ```
   chore: release 2.6.0 - Feature Name
   ```

## Files That Automatically Pick Up the Version

The following files consume the centralized version and do not need manual updates:

- `backend/app.py` - imports `APP_VERSION`
- `backend/routes/server_routes.py` - passes version to frontend templates
- `backend/routes/api_routes.py` - includes version in `/api/status` response
- `frontend/templates/index.html` - displays version in About page and stats
