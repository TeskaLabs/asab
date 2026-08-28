# CHANGELOG

## Release candidate

### Features
- `asab.web.cors`: Rewrote web CORS with origin allowlist, credentials, and `WebContainer.enable_cors()` (#812)

---

## v26.36

### Breaking Changes

- `asab.web.auth.Authorization`: `has_*_access` methods now return `False` when the authorization is expired instead of raising `NotAuthenticatedError` (#743)

### Features

- `asab.zookeeper.LeaderService`: Created a dedicated service for Zookeeper-driven election of leader/follower (#798)
- `asab.zookeeper.LeaderService`: Added `StepDown()` and `SetUp()` methods to voluntarily step down from or rejoin leader election (#801)
- `asab.api.DiscoveryService`: Implemented ZooKeeper persistent watcher for service discovery change notifications (#728)
- `asab.library.LibrarySchemaService`: Added `read_schema()` with schema extension discovery, validation, and additive merge into base schemas (#749)
- `asab.library.CacheLibraryProvider`: Implemented cache library provider that mirrors remote library content to a local filesystem (#758)
- `asab.library.GitProvider`: Added configurable pull interval for periodic repository synchronization (#745)
- `asab.web.rest`: Extended REST API handlers to accept YAML request and response bodies in addition to JSON (#810)
- `asab.web.auth.AccessTokenAuthProvider`: Added support for ApiKey tokens in development authentication mode (#759)
- `asab.web.auth.Authorization`: Added OR-check for resource access control with `match="any"` or `match="all"` parameter (#761)
- `asab.web.accesslog`: Added authenticated user and tenant information to HTTP access log records (#792)
- `asab.web.auth.IdTokenAuthProvider`: Added ability to extract ID token from WebSocket request headers (#757)
- `asab.library.LibsRegProvider`: Publish `library.change!` PubSub event when repository etag changes (#789)
- `asab.task`: Print full stack trace when a scheduled task execution fails (#764)
- `asab.task`: Added wrapper around `task.exception()` for safer exception retrieval from completed tasks (#768)
- `asab.library.LibraryService`: Write provider URL into library cache metadata on initialization (#762)

### Fixes

- `asab.web.auth.IdTokenAuthProvider`: Fixed order of WebSocket authentication to validate ID token before access token (#770)
- `asab.web.auth`: Fixed WebSocket authentication handling and improved auth failure logging (#795)
- `asab.web.auth.AccessTokenAuthProvider`: Fixed authentication of WebSocket requests with multivalued Upgrade header (#748)
- `asab.web.auth`: Treat HTTP Authorization scheme as case-insensitive per RFC 7235 (#759)
- `asab.web.auth`: Log authentication failure reasons reported by auth providers (#788)
- `asab.api`: Fixed OpenAPI tags for wrapped handler methods and improved ASAB API documentation (#796)
- `asab.library.LibrarySchemaService`: Fixed base schema handling when loading and merging schema extensions (#794)
- `asab.library.LibrarySchemaService`: Improved error message for invalid nested base schema paths (#806)
- `asab.library.LibrarySchemaService`: Aggregate skipped schema extension fields into a single log message (#813)
- `asab.web.auth.Authorization`: Fixed `__repr__` output for expired and valid authorization objects (#742)
- `asab.library.GitProvider`: Do not pull after init; mark library as not ready when initial pull fails (#753)
- `asab.library.GitProvider`: Delete and re-clone repository when remote repo is empty (#754)
- `asab.library.GitProvider`: Pull immediately after init when existing cached library content is detected (#785)
- `asab.library.LibraryService`: Do not fail startup when cache URL metadata file is read-only (#765)
- `asab.library.FileSystemProvider`: Store inotify file change events in AggrEvents to avoid duplicate change notifications (#782)
- `asab.library.ZooKeeperLibraryProvider`: Handle transient ZooKeeper reconnects without clearing library state (#744)
- `asab.library.ZooKeeperLibraryProvider`: Add descriptive error message when ZooKeeper module is not initialized (#797)
- `asab.zookeeper.LeaderService`: Fixed incorrect `Application.tick60!` PubSub callback reference (#808)
- `asab.zookeeper`: Cache ZooKeeper `session_id` and `connected_node` for log lines outside CONNECTED state (#780)
- `asab.Application`: Fixed asyncio event loop initialization for Python 3.14 compatibility (#763)
- `asab.web`: Improved logging across web, auth, and REST modules (#771)
- `asab.library`, `asab.zookeeper`: Improved logging across library providers and ZooKeeper container (#772)
- `asab.metrics`: Improved logging in metrics service and exporters (#793)
- `docs`: Fixed REST API tutorial and getting started documentation (#774)

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
