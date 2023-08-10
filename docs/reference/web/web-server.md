# Web server

For starting, accessing and manipulating of a web server, ASAB provides `asab.web` module together with `asab.WebService` and `asab.web.WebContainer`.
This module offers an integration of [`aiohttp` web server](http://aiohttp.readthedocs.io/en/stable/web.html). It is possible to run multiple web servers from one application. The configuration for each server is stored in dedicated **web container**. **Web Service** registers these containers and runs the servers.

!!! tip

	For a quick start, we recommend reading the official `aiohttp` tutorial on [how to run a simple web server](https://docs.aiohttp.org/en/stable/web_quickstart.html#run-a-simple-web-server).

In order to use ASAB Web Service, first make sure that you have `aiohttp` module installed:
``` shell
python3 -m pip install aiohttp
```

## Handlers, routes and resources

`aiohttp` servers use the concept of Handlers, Routes and Resources. Here we provide a very quick explanation that should help you to get into the terminology.

- **Handler**, more precisely *"a web request handler"*, is a function that does the logic when you send HTTP request to the endpoint. It is a coroutine that accepts `aiohttp.web.Request` instance as its only parameter and returns a `aiohttp.web.Response` object.

	```python
	async def handler(request):
		return aiohttp.web.Response()
	```

- **Route** corresponds to handling HTTP method by calling web handler. Routes are added to the route table that is stored in the Web Application object.

	```python
	web_app.add_routes(
		[web.get('/path1', get_1),
		web.post('/path1', post_1),
		web.get('/path2', get_2),
		web.post('/path2', post_2)]
	```

- **Resource** is an entry in route table which corresponds to requested URL. Resource in turn has at least one route. When you add a route, the resource object is created under the hood.


## Running a simple web server


!!! example "Creating a web server 1: One method does it all!"

	To build a web server quickly, ASAB provides a method [`asab.web.create_web_server()`](#asab.web.create_web_server) that does all the magic.

	```python linenums="1"
	import asab.web
	import aiohttp

	class MyApplication(asab.Application):
		async def initialize(): #(1)!
			web = asab.web.create_web_server(self) #(2)!
			web.add_get('/hello', self.hello) #(3)!

		# This is the web request handler
		async def hello(self, request): #(4)!
			return aiohttp.web.Response(data="Hello from your ASAB server!\n")

	if __name__ == '__main__':
		app = MyApplication()
		app.run()
	```

	1. Web server configuration should be prepared during [the init-time](/reference/application/reference/#init-time) of the application lifecycle.
	2. `asab.web.create_web_server()` creates web server and returns instance of
		[`aiohttp.web.UrlDispatcher` object](https://docs.aiohttp.org/en/stable/web_reference.html?highlight=router#router) (which is usually referred to as a "router"). The method takes the argument `app` which is used as the reference to the base `asab.Application` object, and optional parameters that expand configuration options.
	3. You can easily create a new endpoint by [`aiohttp.web.UrlDispatcher.add_route()` method](https://docs.aiohttp.org/en/stable/web_reference.html?highlight=router#aiohttp.web.UrlDispatcher.add_route)
		that appends a request handler to the router table. This one is a shortcut for adding a **GET** handler. 
	4. A request handler must be a coroutine that accepts [`aiohttp.web.Request` instance](https://docs.aiohttp.org/en/stable/web_reference.html#aiohttp.web.Request) as its only parameter and returns [`aiohttp.web.Response` instance](https://docs.aiohttp.org/en/stable/web_reference.html#response).

	By default, ASAB server runs on `0.0.0.0:8080`. 
	You can test if your server is working by sending a request to the `/hello` endpoint, e.g., via the `curl` command:

	```shell
	curl http://localhost:8080/hello
	```

	and you should get the response:

	```
	Hello from your ASAB server!
	```

!!! example "Creating a web server 2: Under the hood."

	The code below does exactly the same as in the previous example.

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
	3. Creates the Web container, which is instance of [`asab.Config.Configurable`](http://localhost:8000/reference/config/reference/#asab.config.Configurable) object that stores the configuration such as the actual web application.
	4. `asab.web.WebContainer.WebApp` is instance of `aiohttp.web.Application` object. To create a new endpoint, use methods for [`aiohttp.web.Application.router` object](https://docs.aiohttp.org/en/stable/web_reference.html?highlight=add_get#router).
	5. A request handler must be a coroutine that accepts [`aiohttp.web.Request` instance](https://docs.aiohttp.org/en/stable/web_reference.html#aiohttp.web.Request) as its only parameter and returns [`aiohttp.web.Response` instance](https://docs.aiohttp.org/en/stable/web_reference.html#response).

!!! tip

	Resources may also have variable path, see [the documentation](https://docs.aiohttp.org/en/stable/web_quickstart.html#variable-resources).

	```python
	web.get('/users/{user}/age', user_age_handler)
	web.get(r'/{name:\d+}', name_handler)
	```

!!! note

	`aiohttp` also supports the *Flask style* for creating web request handlers via decorators. ASAB applications use the *Django style* way of creating routes, i.e. without decorators.

## Web server configuration

Configuration is passed to the `asab.web.WebContainer` object.

| Parameter | Meaning |
| --- | --- |
| `listen` | The socket address to which the web server will listen. |
| `backlog` | A number of unaccepted connections that the system will allow before refusing new connections, see [`socket.socket.listen()`](https://docs.python.org/3/library/socket.html#socket.socket.listen) for details. |
| `rootdir` | The root path for the server. In case of many web containers, each one can implement a different root. |
| `servertokens` | Controls whether `'Server'` response header field is included (`'full'`) or faked (`'prod'`). |
| `cors` | See [Cross-Origin Resource Sharing](/reference/web/cors) section. |
| `body_max_size`| Client's maximum size in a request, in bytes. If a **POST** request exceeds this value, `aiohttp.HTTPRequestEntityTooLarge` exception is raised. See [the documentation](https://docs.aiohttp.org/en/stable/web_reference.html?highlight=client_max_size#aiohttp.web.Application) for more information. |
| `cors` | Contents of the Access-Control-Allow-Origin header. See the [CORS section](./cors). |
| `cors_preflight_paths` | Pattern for endpoints that shall return responses to pre-flight requests (**OPTIONS**). Value must start with `"/"`. See the [CORS section](./cors). |

### The default configuration

```ini
[web]
listen=0.0.0.0 8080
backlog=128
rootdir=
servertokens=full
cors=
cors_preflight_paths=/openidconnect/*, /test/*
body_max_size=1024**2
```


### Socket addresses

The default configuration of the web socket address in `asab.web.WebContainer` is the following:

``` ini
[web]
listen=0.0.0.0:8080
```

Multiple listening interfaces can be specified:

``` ini
[web]
listen:
	0.0.0.0:8080
	:: 8080
```

Multiple listening interfaces, one with HTTPS (TLS/SSL) can be
specified:

``` ini
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

``` ini
[web]
listen:
	0.0.0.0 8080
	:: 8080
	0.0.0.0 8443 ssl

# The SSL parameters are inside of the WebContainer section
cert=...
key=...
```

You can also enable listening on TCP port 8080, IPv4 and IPv6 if applicable:

```ini
[web]
listen=8080
```

## Reference

::: asab.web.create_web_server

::: asab.web.service.WebService

::: asab.web.WebContainer

