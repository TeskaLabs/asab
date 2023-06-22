The web server
==============

ASAB provides a web server in a :py`asab.web`{.interpreted-text
role="mod"} module. This module offers an integration of a
:py`aiohttp`{.interpreted-text role="mod"} [web
server](http://aiohttp.readthedocs.io/en/stable/web.html).

1.  Before you start, make sure that you have
    :py`aiohttp`{.interpreted-text role="mod"} module installed.

``` {.bash}
$ pip3 install aiohttp
```

2.  The following code creates a simple web server application

``` {.python}
#!/usr/bin/env python3
import asab
import asab.web
import aiohttp

class MyApplication(asab.Application):

    def __init__(self):
        super().__init__()

        # Load the ASAB Web module
        self.add_module(asab.web.Module)

        # Locate the ASAB Web service
        websvc = self.get_service("asab.WebService")

        # Create the Web container
        container = asab.web.WebContainer(websvc, 'my:web', config={"listen": "0.0.0.0:8080"})

        # Add a route to the handler
        container.WebApp.router.add_get('/hello', self.hello)

    # This is the web request handler
    async def hello(self, request):
        return aiohttp.web.Response(text='Hello!\n')

if __name__ == '__main__':
    app = MyApplication()
    app.run()
```

3.  Test it with [curl]{.title-ref}

``` {.bash}
$ curl http://localhost:8080/hello
Hello!
```

Web Service
-----------

Service location example:

``` {.python}
from asab.web import Module
self.add_module(Module)
svc = self.get_service("asab.WebService")
```

Configuration
-------------

The default configuration of the [web]{.title-ref} container in ASAB is
following:

``` {.ini}
[web]
listen=0.0.0.0:8080
```

Multiple listening interfaces can be specified:

``` {.ini}
[web]
listen:
    0.0.0.0:8080
    :: 8080
```

Multiple listening interfaces, one with HTTPS (TLS/SSL) can be
specified:

``` {.ini}
[web]
listen:
    0.0.0.0 8080
    :: 8080
    0.0.0.0 8443 ssl:web

[ssl:web]
cert=...
key=...
...
```

Multiple interfaces, one with HTTPS (inline):

``` {.ini}
[web]
listen:
    0.0.0.0 8080
    :: 8080
    0.0.0.0 8443 ssl

# The SSL parameters are inside of the WebContainer section
cert=...
key=...
...
```

Other available options are:

> -   [backlog]{.title-ref}
> -   [rootdir]{.title-ref}
> -   [servertokens]{.title-ref} (default value [full]{.title-ref})
> -   [cors]{.title-ref}
> -   [cors\_preflight\_paths]{.title-ref}

TLS/SSL paramereters:

> -   [cert]{.title-ref}
> -   [key]{.title-ref}
> -   [password]{.title-ref}
> -   [cafile]{.title-ref}
> -   [capath]{.title-ref}
> -   [ciphers]{.title-ref}
> -   [dh\_params]{.title-ref}
> -   \`verify\_mode\`: one of [CERT\_NONE]{.title-ref},
>     [CERT\_OPTIONAL]{.title-ref} or [CERT\_REQUIRED]{.title-ref}
> -   [check\_hostname]{.title-ref}
> -   [options]{.title-ref}

Sessions
--------

ASAB Web Service provides an implementation of the web sessions.

TODO: \...

TODO: \...
