# OpenAPI Documentation

ASAB's API service generates [Swagger documentation](https://swagger.io/specification) which automatically
shows all of your endpoints, and you can add summaries, descriptions, tags, and more.

If you want authorization in Swagger docs, you will need an OpenIDConnect endpoint.

## Creating OpenAPI endpoint

First, you need to initialize the API Service:

``` python
self.ApiService = asab.api.ApiService(self) #(1)!
self.ApiService.initialize_web() #(2)!
```

1. Initializes OpenAPI Service.
2. Introduces Web to OpenAPI Service.

After initializing the API Service, */doc* endpoint will become available. After you open it, you should see the following content:

![Preview of Swagger documentation](/images/rest-api-docs/1-preview.png)

You will notice that some or none of your endpoints have summaries, tags, or descriptions.

That's because you need to add a docstring to your endpoint method:

``` python
async def endpoint(self, request):
	"""
	Summary looks like this and takes the first line from docstring.

	Description of what this endpoint does.

	---
	tags: [asab.mymicroservice]
	"""
```


Also by adding a docstring to your ASAB Application, a description will
be automatically added to the top of the Swagger docs:

``` python
class TutorialApp(asab.Application):
	"""
	TutorialApp is the best microservice in the world!

	<marquee>The description supports HTML tags</marquee>
	"""
```
![Preview of Swagger documentation with docstrings](/images/rest-api-docs/2-preview-with-docs.png)

## Authorization in Swagger

Authorization requires making an OpenIDConnect endpoint with an Authorization and Token endpoint
(like with using TeskaLabs [SeaCat Auth](https://github.com/TeskaLabs/seacat-auth)).

For authorization, you will need to add `authorizationUrl`
and `tokenUrl` to the configuration:

``` ini
[asab:doc]
authorizationUrl=http://localhost:8080/openidconnect/authorize
tokenUrl=http://localhost:8080/openidconnect/token
```

If you have an endpoint that requires a scope, you can add it with the
configuration file:

``` ini
[asab:doc]
scopes=read,write
```

To set up endpoint authorization, you can use [this example](/examples/web-authz-userinfo).

For the authorization bearer token to be added to the request, a scope is needed to be put into the security parameter in a docstring.
It does not matter what it is called or if it exists, but it needs to be included.
`- oAuth` must always be included.

``` python
@asab.web.authz.required("resource:topsecret")
async def top_secret_endpoint(self, request):
	"""
	Top secret!

	---
	tags: [asab.coolestmicroservice]
	security:
		- oAuth:
			- read
	"""
```

After setting up Authorization, a green `Authorize` button should appear in the Swagger docs. After you click on it, you should see the following content:

![Authorization of Swagger documentation](/images/rest-api-docs/3-authorization.png)


## Tags

You can label your handler methods with custom tags.
These tags are used for grouping and sorting your endpoints on the documentation page.

``` python
async def my_method(self, request):
"""
<function description>

---
tags: ['custom tag 1', 'custom tag 2', 'custom tag 3']
"""
	...
```

!!! info
	Remember to use exactly three dashes on the separate line and put tags in array with `[]`, even if you want to have a single tag.


If there is no custom tag defined - the tag name is automatically set to
be `module_name`. If you do not want to use custom tags but
still would like to sort the routes, you can configure the options in
the config file:

``` ini
[asab:doc]
default_route_tag=class_name
```

There are two options for `default_route_tag`:

=== "`module_name`"
	All tags without a custom name are displayed with the name of the **module** where the handler is defined.
	![Authorization of Swagger documentation](/images/rest-api-docs/4-module.png)

=== "`class_name`"
	All tags without a custom name are displayed with the name of the **class** where the handler is defined.
	![Authorization of Swagger documentation](/images/rest-api-docs/5-class.png)
