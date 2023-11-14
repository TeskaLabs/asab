# Library Service

The ASAB Library is the concept of shared data content across microservices in the cluster.
In the cluster/cloud microservice architectures, all microservices must have access to unified resources.
The Library provides a read-only interface for listing and reading this content.

The Library is designed to be read-only. It also allows to *"stack"* various libraries into one view (overlayed), merging the content of each library into one united space.

The library can also notify the ASAB microservice about changes, e.g. for automated update/reload.

## Library structure

The library content is organized in a simplified file system manner, with directories and files.

Example of the library structure:

```
+ /folder1/
  - /folder1/item1.yaml
  - /folder1/item2.json
+ /folder2/
  - /folder2/item3.yaml
  + /folder2/folder2.3/
    - /folder2/folder2.3/item4.json
```

## Library path rules

- Any path must start with "/", including the root path.
- The folder path must end with "/".
- The item path must end with a file extension (e.g. ".json").

## Layers

The library content can be organized into an unlimited number of layers.
Each layer is represented by a **provider** with a specific configuration.

The layers of the library are like slices of Swiss cheese layered on top of each other.
Only if there is a hole in the top layer can you see the layer that shows through underneath.
It means that files of the upper layer overwrite files with the same path in the lower layers.

The first provider is responsible for providing '/.disabled.yaml' that controls the visibility of items. 
If '/.disabled.yaml' is not present, then is considered empty.

## Library service

Example of the use:

```python
import asab
import asab.library

class MyApplication(asab.Application):

    async def initialize(self):
        self.LibraryService = asab.library.LibraryService(self, "LibraryService") #(1)!
        self.PubSub.subscribe("Library.ready!", self.on_library_ready) #(2)!

    async def on_library_ready(self, event_name, library): #(3)!

        for item in await self.LibraryService.list("/", recursive=True): #(4)!
            print("*", item)
            if item.type == 'item': #(5)!
                itemio = await self.LibraryService.read(item.name) #(6)!
                if itemio is not None:
                    with itemio: #(7)!
                        content = itemio.read()
                        print("- content: {} bytes".format(len(content)))
                else:
                    print("  - (DISABLED)")

if __name__ == '__main__':
    app = MyApplication()
    app.run()
```

1. Initializes the Library Service.
2. When the Library is initialized, `Library.ready!` PubSub message is emitted. 
3. The callback has to possess two arguments. `event_name` is the message "Library.ready!", `library` is the specific provider with
which is the Library initialized.
4. `list()` method returns list of `LibraryItem`s. For more information, see the reference section.
5. `item.type` can be either 'item' or 'dir'.
6. `read()` coroutine returns item IO object or None if the file is disabled.
7. Item IO object is used as a context manager.

The library service may exist in multiple instances, with different `paths` setups. 
For that reason, you have to provide a unique `service_name` and there is no default value for that.

!!! example "Example of the library configuration:"

    ``` ini
    [library]
    providers:
        provider+1://...
        provider+2://...
        provider+3://...
    ```

## PubSub messages

| Message | Published when... |
| --- | --- |
| `Library.not_ready!` | providers are not ready. |
| `Library.ready!` | all of the providers are ready. |
| `Library.change!` | the content of the Library has changed. |



## Notification on changes

!!! example

    ```python
    class MyApplication(asab.Application):

    async def initialize(self):
        self.PubSub.subscribe("Library.ready!", self.on_library_ready
        self.PubSub.subscribe("Library.change!", self.on_library_change)

    async def on_library_ready(self, event_name, library=None):
        await self.LibraryService.subscribe(["/asab"]) #(1)!

    def on_library_change(self, message, provider, path): #(2)!
        print("New changes in the library found by provider: '{}'".format(provider))
    ```

    1. `self.LibraryService.subscribe()` method takes either a single path as a string or multiple paths in list and watches for changes in them.
    2. This coroutine takes three arguments: `message` (`Library.change!` in this case), `provider` (name of the provider that has detected changes) and `path` (the path where changes were made).

## Providers

The list of available providers:

| Provider | Read the content | Notify on changes |
| --- | :---: | :---: |
| Filesystem | :material-check: | :material-check: |
| Apache Zookeeper | :material-check: | :material-check: |
| Microsoft Azure Storage | :material-check: | :material-close: |
| Git | :material-check:  | :material-check: |

### Filesystem

The most basic provider that reads data from the local filesystem. 
The notification on changes functionality is available only for Linux systems,
as it uses [inotify](https://en.wikipedia.org/wiki/Inotify).

!!! example "Configuration examples:"

    ```ini
    [library]
    providers: /home/user/directory
    ```

    ```ini
    [library]
    providers: ./this_directory
    ```

    ```ini
    [library]
    providers: file:///home/user/directory
    ```

### Apache Zookeeper

ZooKeeper as a consensus technology is vital for microservices in the
cluster.

There are several configuration strategies:

1)  Configuration from `[zookeeper]` section.

```ini
[zookeeper]
servers=zookeeper-1:2181,zookeeper-2:2181,zookeeper-3:2181
path=/library

[library]
providers:
    zk://
```

2)  Specify a path of a ZooKeeper node where only library lives.

```ini
[zookeeper]
servers=zookeeper-1:2181,zookeeper-2:2181,zookeeper-3:2181
path=/else

[library]
providers:
    zk:///library
```

``` ini
[zookeeper]
servers=zookeeper-1:2181,zookeeper-2:2181,zookeeper-3:2181
path=/else

[library]
providers:
    zk:///
```

3)  Configuration from the URL in the `[library]` section.

``` ini
[library]
providers:
    zk://zookeeper-1:2181,zookeeper-2:2181,zookeeper-3:2181/library
```

4)  Configuration from `[zookeeper]` section and joined
    [path]{.title-ref} from `[zookeeper]` and `[library]` sections.

    > The resulting path will be [/else/library]{.title-ref}.

``` ini
[zookeeper]
servers=zookeeper-1:2181,zookeeper-2:2181,zookeeper-3:2181
path=/else

[library]
providers:
    zk://./library
```

If a `path` from the `[zookeeper]` section is missing, an application class name will be used, e.g.
`/BSQueryApp/library`.

### Microsoft Azure Storage

You can configure the microservice to read from the Microsoft Azure Storage container.

Configuration:

``` ini
[library]
providers: azure+https://ACCOUNT-NAME.blob.core.windows.net/BLOB-CONTAINER
```

If Container Public Access Level is not set to *"Public access"*, then
*"Access Policy"* must be created with *"Read"* and *"List"* permissions
and *"Shared Access Signature" (SAS)* query string must be added to a
URL in a configuration:

``` ini
[library]
providers: azure+https://ACCOUNT-NAME.blob.core.windows.net/BLOB-CONTAINER?sv=2020-10-02&si=XXXX&sr=c&sig=XXXXXXXXXXXXXX
```

### Git repository

!!! warning

    Connection to git repositories requires
    [pygit2](https://www.pygit2.org/) library to be installed.

    ```shell
    pip install pygit2
    ```

Please follow this format in the configuration:

``` ini
[library]
providers: git+http(s)://<username>:<deploy-token>@<path>#<branch>
```

!!! example "Cloning from GitHub repository:"

    Using a public repository from GitHub, the configuration may look like
    this:

    ``` ini
    [library]
    providers: git+https://github.com/john/awesome_project.git
    ```

!!! example "Using custom branch:"

    Use hash `#<branch-name>` to clone a repository from a
    selected branch:

    ``` ini
    [library]
    providers: git+https://github.com/john/awesome_project.git#name-of-the-branch
    ```

#### Deploy tokens in GitLab

GitLab uses deploy tokens to enable authentication of deployment tasks,
independent of a user account. Authentication through deploy tokens is
the only supported option for now.

If you want to create a deploy token for your GitLab repository, follow
these steps from the
[manual](https://docs.gitlab.com/ee/user/project/deploy_tokens/#create-a-deploy-token):

1.  Go to **Settings > Repository > Deploy tokens** section in your
    repository. (Note that you have to possess a *"Maintainer"* or
    *"Owner"* role for the repository.)
2.  Expand the **"Deploy tokens"** section. The list of current Active
    Deploy Tokens will be displayed.
3.  Complete the fields and scopes. We recommend a custom *"username"*,
    as you will need it later for the URL in the configuration.
4.  Record the deploy token's values *before leaving or refreshing the
    page*! After that, you cannot access it again.

After the deploy token is created, use the URL for the repository in the
following format:

``` ini
[library]
providers: git+https://<username>:<deploy_token>@gitlab.example.com/john/awesome_project.git
```

#### Where does the repository clone?

The git provider clones the repository into a temporary directory. The
default path for the cloned repository is
`/tmp/asab.library.git/` and it can be changed manually:

``` ini
[library:git]
repodir=path/to/repository/cache
```

### Libraries repository

The `libsreg` provider downloads the content from the _distribution URL_.
The distribution URL points to HTTP(S) server where _content archives_ are published.

!!! example "Configuration examples:"

    ```ini
    [library]
    providers: libsreg+https://libsreg.example.com/my-library
    ```

!!! example "More than one distribution server can be specified:"

    ```ini
    [library]
    providers: libsreg+https://libsreg1.example.com,libsreg2.example.com/my-library
    ```

    This variant provides more resiliency against a distribution server unavailability.

A structure of the distribution server filesystem:

```
/my-library/
  + my-library-master.tar.xz
  + my-library-master.tar.xz.sha256
  + my-library-production.tar.xz
  + my-library-production.tar.xz.sha256
  + my-library-v43.41.tar.xz
  + my-library-v43.41.tar.xz.sha256
  ...
```

* `*.tar.xz`: This is the TAR/XZ archive of the actual content
* `*.tar.xz.sha256`: SHA256 checksum of the archive

The structure of the distribution is as follows:

`/{archname}/{archname}-{version}.tar.xz`

* `archname`: A name of the distribution archive, `my-library` in the example above
* `version`: A version of the distribution archive, `master`, `production` are typically GIT branches, `v43.41` is a GIT tag.


!!! tip

    This provider is designed to use Microsoft Azure Storage as a distribution point.
    Is is assumed that the content archives are uploaded to the distribution point using CI/CD.



## Reference

::: asab.library.LibraryService
