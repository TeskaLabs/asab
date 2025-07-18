# CHANGELOG

## v25.29

### Breaking Changes
- Tenant-aware applications must choose whether to use strict or non-strict mode and adjust their web routes accordingly.
  Strict mode is considered the default. (#679)

### Fix
- Remove race condition from service advertisement in asab.api (#694)

### Features
- Introducing multi-tenancy modes (#679)
- Add path info to "Failed to initialize tenant context" error message (#701)

### Refactoring
- XX

---


## v25.25
