Creating a Web Server
=====================

Now, when you know how to create and run a basic asab application, let's create the very first web server!

Set up a new project and create a new file `app.py` with the following code:

``` python title="app.py"

#!/usr/bin/env python3
import asab.web.rest

class MyWebApplication(asab.Application):

    def __init__(self):
        super().__init__()

        # Create the Web server
        web = asab.web.create_web_server(self)

        # Add a route to the handler method
        web.add_get('/hello', self.hello)

    # This is the web request handler
    async def hello(self, request):
        return asab.web.rest.json_response(
            request,
            data="Hello, world!"
        )

if __name__ == '__main__':
    app = MyWebApplication()
    app.run()

```

Run it with the command:

``` console
python3 app.py
```


The ASAB web server is now available at [http://localhost:8080/](http://localhost:8080/).

!!! note

    In case you don't know, **localhost** refers to the loopback network interface address of a device, usually represented as the IP address 127.0.0.1. It is used to refer to the device itself, allowing software to communicate with services running on the same device. In simpler terms, it's like talking to yourself within a computer to access and test applications or websites without going online.

    The part `:8080` refers to a port. A **port** is a communication endpoint in a computer network. It is represented by a numerical value, such as 8080, and it allows applications and services to establish connections and exchange data. Ports enable the proper routing and delivery of network traffic, ensuring that information reaches the intended destination within a device or across different devices on a network.

## TODO: send a request to /hello endpoint 

Deeper look
-----------

``` python title="app.py" linenums="1"

#!/usr/bin/env python3
import asab.web.rest  # (1)

class MyWebApplication(asab.Application):

    def __init__(self):
        super().__init__()  # (2)

        # Create the Web server
        web = asab.web.create_web_server(self)  # (3)

        # Add a route to the handler method
        web.add_get('/hello', self.hello)  # (4)

    # This is the web request handler
    async def hello(self, request):  # (5)
        return asab.web.rest.json_response(  # (6)
            request,
            data="Hello, world!"
        )

if __name__ == '__main__':
    app = MyWebApplication()
    app.run()

```

1. Let's start by importing the `asab.web.rest` module.

2. As you will see later, `asab.Application` has a lifecycle with three phases. This time, we modify the initialization of the application. In order not to completely override the whole application initialization, call the `super.__init__()` method.

3. The `asab.web` module provides a `create_web_server()` method that
simplifies creation of the Web server in the ASAB application. It returns an object, which is used as a router in which you can add new routes.

4. With the `add_get()` method, you can define a new route that requests can be send to. If you now access the web server with a path `/hello`, it will
be handled by a `hello()` method. In other words, the `hello()` method is installed at the web server at `/hello` endpoint with the `GET` HTTP method. Similar methods for `PUT`, `POST` and `DELETE` methods exist, as we will see in the next tutorial. 

5. This is a handler method, which is called by the router when `GET` request is send to a `/hello` endpoint. Every handler method must be a coroutine! That means, it has to be defined with `async def` keyword. Also, there has to be the `request` argument, even if you (for some peculiar reason) don't want to use it in the function body. Otherwise it won't work together with the `add_get()` method.

6. The `asab.web.rest` module provides a `json_response()` method that simply sends back any data you want to the client in JSON format.

