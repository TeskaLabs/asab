# Cross-Origin Resource Sharing (CORS)

!!! tip

	[This article](https://developer.mozilla.org/en-US/docs/Web/HTTP/CORS) explains the key concept of CORS very well.

The Cross-Origin Resource Sharing standard works by adding new HTTP headers that let servers describe which origins are permitted to read that information from a web browser. Additionally, for HTTP request methods that can cause side-effects on server data (in particular, HTTP methods other than **GET**, or **POST** with certain MIME types), the specification mandates that browsers **"preflight"** the request, soliciting supported methods from the server with the HTTP **OPTIONS** request method, and then, upon "approval" from the server, sending the actual request. Servers can also inform clients whether "credentials" (such as Cookies and HTTP Authentication) should be sent with requests.


## Preflight paths

Preflight requests are sent by the browser, for some cross domain request (custom header etc.).
Browser sends preflight request first.
It is a request on the same endpoint as an app demanded request, but of the **OPTIONS** method.
Only when a satisfactory response is returned, the browser proceeds with sending original request.
Use `cors_preflight_paths` option to specify all paths and path prefixes (separated by comma) for which you
want to allow OPTIONS method for preflight requests.

You can then configure CORS by running your app with a config file with this contents:

``` ini
[web]
cors=*
cors_preflight_paths=/*
```

| Option | Meaning |
| --- | --- |
| `cors` | Contents of the Access-Control-Allow-Origin header |
| `cors_preflight_paths` | Pattern for endpoints that shall return responses to pre-flight requests (**OPTIONS**). Value must start with `"/"`. |

## Reference

::: asab.web.WebContainer.add_preflight_handlers

