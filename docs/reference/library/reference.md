Library {#library-ref}
=======

The ASAB Library ([asab.library]{.title-ref}) is a concept of the shared
data content across microservices in the cluster. In the cluster/cloud
microservice architectures, all microservices must have access to
unified resources. The [asab.library]{.title-ref} provides a read-only
interface for listing and reading this content.

[asab.library]{.title-ref} is designed to be read-only. It also allows
to \"stack\" various libraries into one view (overlayed) that merges the
content of each library into one united space.

The library can also notify the ASAB microservice about changes, e.g.
for automated update/reload.

There is a companion microservice [asab-library]{.title-ref} that can be
used for the management and editing of the library content. The
[asab.library]{.title-ref} can however operate without
[asab-library]{.title-ref} microservice.

Library structure
-----------------

The library content is organized in a simplified filesystem manner, with
directories and files.

Example of the library structure:

``` {.}
+ /folder1/
  - /folder1/item1.yaml
  - /folder1/item2.json
+ /folder2/
  - /folder2/item3.yaml
  + /folder2/folder2.3/
    - /folder2/folder2.3/item4.json
```

Library path rules
------------------

-   Any path must start with [/]{.title-ref}, including the root path
    ([/]{.title-ref}).
-   The folder path must end with [/]{.title-ref}.
-   The item path must end with an extension (e.g. [.json]{.title-ref}).

Layers
------

The library content can be organized into an unlimited number of layers.
Each layer is represented by a [provider]{.title-ref} with a specific
configuration.

The layers of the library are like slices of Swiss cheese layered on top
of each other. Only if there is a hole in the top layer can you see the
layer that shows through underneath. It means that files of the upper
layer overwrite files with the same path in the lower layers.

The first provider is responsible for providing
[/.disabled.yaml]{.title-ref} that controls the visibility of items. If
[/.disabled.yaml]{.title-ref} is not present, then is considered empty.

Library service
---------------

Example of the use:

``` {.python}
import asab
import asab.library


# this substitutes configuration file
asab.Config.read_string(
            """
[library]
providers=git+https://github.com/TeskaLabs/asab-maestro-library.git
"""
        )


class MyApplication(asab.Application):

    def __init__(self):
        super().__init__()
        # Initialize the library service 
        self.LibraryService = asab.library.LibraryService(self, "LibraryService")
        self.PubSub.subscribe("Library.ready!", self.on_library_ready)

    async def on_library_ready(self, event_name, library):
        print("# Library\n")

        for item in await self.LibraryService.list("/", recursive=True):
            print(" *", item)
            if item.type == 'item':
                itemio = await self.LibraryService.read(item.name)
                if itemio is not None:
                    with itemio:
                        content = itemio.read()
                        print("  - content: {} bytes".format(len(content)))
                else:
                    print("  - (DISABLED)")

if __name__ == '__main__':
    app = MyApplication()
    app.run()
```

The library service may exist in multiple instances, with different
[paths]{.title-ref} setups. For that reason, you have to provide a
unique [service\_name]{.title-ref} and there is no default value for
that.

For more examples of Library usage, please see [ASAB
examples](https://github.com/TeskaLabs/asab/tree/master/examples)

Library configuration
---------------------

Example:

``` {.ini}
[library]
providers:
    provider+1://...
    provider+2://...
    provider+3://...
```

PubSub messages
---------------

Read more about `PubSub<pubsub_page>`{.interpreted-text role="ref"} in
ASAB.

::: {.option}
Library.ready!
:::

A library is created in a "not ready" state. Only after all providers
are ready, the library itself becomes ready. The library indicates that
by the PubSub event [Library.ready!]{.title-ref}.

::: {.option}
Library.not\_ready!
:::

The readiness of the library (connection to external technologies) can
be lost. You can also subscribe to [Library.not\_ready!]{.title-ref}
event.

::: {.option}
Library.change!
:::

You can get [Notification on Changes](#notification-on-changes) in the
library. Specify a path or paths that you would like to \"listen to\".
Then subscribe to [Library.change!]{.title-ref} PubSub event. Available
for Git and FileSystem providers for now.

Notification on changes
-----------------------

::: {.automethod}
LibraryService.subscribe
:::

Providers
---------

The library can be configured to work with the following \"backends\"
(aka providers):

### Filesystem

The most basic provider that reads data from the local filesystem. The
notification on changes functionality is available only for Linux
systems, as it implements
[inotify](https://en.wikipedia.org/wiki/Inotify)

Configuration examples:

``` {.ini}
[library]
providers: /home/user/directory
```

``` {.ini}
[library]
providers: ./this_directory
```

``` {.ini}
[library]
providers: file:///home/user/directory
```

### Apache Zookeeper

ZooKeeper as a consensus technology is vital for microservices in the
cluster.

There are several configuration strategies:

1)  Configuration from \[zookeeper\] section.

``` {.ini}
[zookeeper]
servers=zookeeper-1:2181,zookeeper-2:2181,zookeeper-3:2181
path=/library

[library]
providers:
    zk://
```

2)  Specify a path of a ZooKeeper node where only library lives.

    > The library path will be [/library]{.title-ref}.

``` {.ini}
[zookeeper]
servers=zookeeper-1:2181,zookeeper-2:2181,zookeeper-3:2181
path=/else

[library]
providers:
    zk:///library


The library path will be `/`.
```

``` {.ini}
[zookeeper]
servers=zookeeper-1:2181,zookeeper-2:2181,zookeeper-3:2181
path=/else

[library]
providers:
    zk:///
```

3)  Configuration from the URL in the \[library\] section.

``` {.ini}
[library]
providers:
    zk://zookeeper-1:2181,zookeeper-2:2181,zookeeper-3:2181/library
```

4)  Configuration from \[zookeeper\] section and joined
    [path]{.title-ref} from \[zookeeper\] and \[library\] sections.

    > The resulting path will be [/else/library]{.title-ref}.

``` {.ini}
[zookeeper]
servers=zookeeper-1:2181,zookeeper-2:2181,zookeeper-3:2181
path=/else

[library]
providers:
    zk://./library
```

If a [path]{.title-ref} from the \[zookeeper\] section is missing, an
application class name will be used E.g.
[/BSQueryApp/library]{.title-ref}

### Microsoft Azure Storage

Reads from the Microsoft Azure Storage container.

Configuration:

``` {.ini}
[library]
providers: azure+https://ACCOUNT-NAME.blob.core.windows.net/BLOB-CONTAINER
```

If Container Public Access Level is not set to \"Public access\", then
\"Access Policy\" must be created with \"Read\" and \"List\" permissions
and \"Shared Access Signature\" (SAS) query string must be added to a
URL in a configuration:

``` {.ini}
[library]
providers: azure+https://ACCOUNT-NAME.blob.core.windows.net/BLOB-CONTAINER?sv=2020-10-02&si=XXXX&sr=c&sig=XXXXXXXXXXXXXX
```

### Git repository

Connection to git repositories requires
[pygit2](https://www.pygit2.org/) library to be installed.

Configuration:

Please follow this format in the configuration:

``` {.ini}
[library]
providers: git+http(s)://<username>:<deploy-token>@<path>#<branch
```

Using a public repository from github, the configuration may look like
this:

``` {.ini}
[library]
providers: git+https://github.com/john/awesome_project.git
```

Use hash [\#\<branch-name\>]{.title-ref} to clone a repository from a
selected branch:

``` {.ini}
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

1.  Go to **Settings \> Repository \> Deploy tokens** section in your
    repository. (Note that you have to possess a \"Maintainer\" or
    \"Owner\" role for the repository.)
2.  Expand the \"Deploy tokens\" section. The list of current Active
    Deploy Tokens will be displayed.
3.  Complete the fields and scopes. We recommend a custom \"username\",
    as you will need it later for the URL in the configuration.
4.  Record the deploy token\'s values *before leaving or refreshing the
    page*! After that, you cannot access it again.

After the deploy token is created, use the URL for the repository in the
following format:

``` {.ini}
[library]
providers: git+https://<username>:<deploy_token>@gitlab.example.com/john/awesome_project.git
```

#### Where does the repository clone?

The git provider clones the repository into a temporary directory. The
default path for the cloned repository is
[/tmp/asab.library.git/]{.title-ref} and it can be changed manually:

``` {.ini}
[library:git]
repodir=path/to/repository/cache
```

### Reference

::: {.autoclass}
LibraryService

::: {.automethod}
read
:::

::: {.automethod}
list
:::

::: {.automethod}
export
:::
:::
