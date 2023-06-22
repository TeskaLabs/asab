Web Server Tutorial
===================

Create a simple web server with ASAB.

The code
--------

``` {.python}
```

| To start the application, store above code in a file `app.py`.
| Execute `$ python3 ./app.py` to run it.

The ASAB web server is now available at <http://localhost:8080/>.

Deeper look
-----------

**ASAB Application**

``` {.python}
#!/usr/bin/env python3
import asab.web.rest

class MyWebApplication(asab.Application):

    def __init__(self):
        super().__init__()

if __name__ == '__main__':
    app = MyWebApplication()
    app.run()
```

This is a ASAB code that declares the application class and runs it.

**Create a Web server**

The `asab.web` module provides a `create_web_server()` function that
simplifies creation of the Web server in the ASAB application.

``` {.python}
web = asab.web.create_web_server(self)
```

**Install the handler**

``` {.python}
web.add_get('/hello', self.hello)

...

async def hello(self, request):
    return asab.web.rest.json_response(
        request,
        data="Hello, world!\n"
    )
```

The handler method `hello()` is installed at the web server at `/hello`
endpoint. HTTP method is `GET`.

It means that if you access the web server with a path `/hello`, it will
be handled by a `hello(...)` method. A handler method must be a
coroutine.
