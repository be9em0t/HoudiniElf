# HANDOFF

## Summary
The QGIS launcher in `dbQGIS/dbMCRai.py` is failing at startup because the configured macOS Keychain item no longer exists.

## Failing Path
- `dbQGIS/dbMCRai.py` reads `dbQGIS/b9QGISdata.ini`
- `access_token` is configured as `__KEYCHAIN__`
- `dbQGIS/secure_config.py` resolves the secret with:
  - service: `qgis/databricks/mcr`
  - account: `databricks-mcr`

## Verified Result
Running the same lookup manually returns:
- `security find-generic-password -s 'qgis/databricks/mcr' -a 'databricks-mcr' -w`
- Result: item not found

## Important Finding
A valid Databricks secret does exist in the login keychain, but under a different identity:
- service: `mcp/databricks/main`
- account: `readonly`
- manual lookup succeeds and returns a Databricks PAT

## Likely Cause
The secret was renamed, recreated, or migrated, but `b9QGISdata.ini` still points at the old service/account pair.

## Recommended Fix
Update `dbQGIS/b9QGISdata.ini` so the MCR token points to the working keychain item:
- `access_token_service = mcp/databricks/main`
- `access_token_account = readonly`

If backward compatibility is preferred, `dbQGIS/secure_config.py` can also be taught to try the new pair as a fallback when the old one is missing.

## Notes
- No workspace was open at the time of inspection.
- The repo currently has no existing `HANDOFF.md`.
