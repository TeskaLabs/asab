# The web server

ASAB provides a web server in a `asab.web` module. 
This module offers an integration of [`aiohttp` web server](http://aiohttp.readthedocs.io/en/stable/web.html).

!!! tip

    For a quick start, we recommend reading the official `aiohttp` tutorial on [how to run a simple web server](https://docs.aiohttp.org/en/stable/web_quickstart.html#run-a-simple-web-server).

## Creating a web server

First make sure that you have `aiohttp` module installed:
``` shell
python3 -m pip install aiohttp
```

The following code creates a simple web server application:

``` python linenums="1"
import asab.web
import aiohttp

class MyApplication(asab.Application):

    async def initialize(self):
        self.add_module(asab.web.Module)  #(1)!
        self.WebService = self.get_service("asab.WebService") #(2)!

        self.WebContainer = asab.web.WebContainer( #(3)!
            websvc=self.WebService,
            config_section_name='my:web',
            config={"listen": "0.0.0.0:8080"}
        )

        self.WebContainer.WebApp.router.add_get('/hello', self.hello) #(4)!

    # This is the web request handler
    async def hello(self, request): #(5)!
        return aiohttp.web.Response(text='Hello from your ASAB server!\n')


if __name__ == '__main__':
    app = MyApplication()
    app.run()
```

1. In order to use `asab.WebService`, first import the corresponding `asab.web.Module`...
2. ...and then locate the Service.
3. Creates the Web container, which is a [`asab.Config.Configurable`](http://localhost:8000/reference/config/reference/#asab.config.Configurable)
4. `asab.web.WebContainer.WebApp` is instance of `aiohttp.web.Application` object. To create a new endpoint, use methods for [`aiohttp.web.Application.router`](https://docs.aiohttp.org/en/stable/web_reference.html?highlight=add_get#router).
5. A request handler must be a coroutine that accepts [`aiohttp.web.Request` instance](https://docs.aiohttp.org/en/stable/web_reference.html#aiohttp.web.Request) as its only parameter and returns [`aiohttp.web.Response` instance](https://docs.aiohttp.org/en/stable/web_reference.html#response).

You can test if your server is working by sending a request to the `/hello` endpoint, e.e., via the `curl` command:

```shell
curl http://localhost:8080/hello
```

and you should get the response:

```
Hello from your ASAB server!
```

## Web Service

Service location example:

``` {.python}
from asab.web import Module
self.add_module(Module)
svc = self.get_service("asab.WebService")
```

## Configuration

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

## Sessions

ASAB Web Service provides an implementation of the web sessions.

TODO: \...

TODO: \...
