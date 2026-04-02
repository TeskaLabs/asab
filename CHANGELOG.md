# CHANGELOG

## Release candidate

### Features
...

---


## v26.12

### Features
- Extend 401 and 403 responses with WWW-Authenticate header (#721)
- Filesystem supports reading from tenants(#722)
- Pass ID token through Authorization object to microservices (#723)
- Filesystem supports reading from tenants (#722)
- asab.library.git.GitProvider: When the repository is not initialized during provider init, retry is triggered once per minute(#727)
- Library service waits until it is ready or timeout (#737)
---


## v25.47

...

---


## v25.46

### Features
- Explicit tenant argument in Authorization's tenant access methods (#717)
- Library Git Provider: Add support for ssh (#713)

---


## v25.45

### Features
- Default mock authorization expiration is now 1 year (#708)
- Library readiness check (#670)

### Fixes
- Update endure ready to read disabled (#706, #707)

---


## v25.43

### Features
- Library GIT provider: Custom CA certificate (#702)
- Add get method into KazooWrapper (#700)
- Strict mode for TenantService (#679)
- Add transactions to MongoDB storage (#695)

### Fixes
- Do not apply tenant and auth handling to OPTIONS routes; improve init logging (#701)
- Remove race condition from service advertisement in asab.api (#694)

---


## v25.36

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
