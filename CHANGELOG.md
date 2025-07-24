# CHANGELOG

## v25.29

### Breaking Changes
- Tenant-aware applications must choose whether to use strict or non-strict mode and adjust their web routes accordingly.
  Strict mode is considered the default. (#679)

### Fix
- Do not apply tenant and auth handling to OPTIONS routes (#701)
- Remove race condition from service advertisement in asab.api (#694)

### Features
- Improve mock auth mode customization (#703)
- Add path info to "Failed to initialize tenant context" error message (#701)
- Introducing multi-tenancy modes (#679)

### Refactoring
- XX

---


## v25.25
