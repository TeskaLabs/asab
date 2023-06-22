REST API Docs
=============

ASAB\'s API service generates a [Swagger
documentation](https://swagger.io/specification) which automatically
shows all of your endpoints and you can add summaries, descriptions,
tags and more.

If you want Authorization in Swagger docs, you will need an
OpenIDConnect endpoint.

In your microservice
--------------------

First you need to initialize the API Service:

``` {.python}
# Initialize API service
self.ApiService = asab.api.ApiService(self)

# Introduce Web to API Service
self.ApiService.initialize_web()
```

After initializing the API Service a **/doc** endpoint will become
available. You will notice that some or none of your endpoints have
summaries, tags or descriptions.

That\'s because you need to add a docstring to your endpoint method:

``` {.python}
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

``` {.python}
class TutorialApp(asab.Application):
    """
    TutorialApp is the best microservice in the world!

    <marquee>The description supports HTML tags</marquee>
    """
```

Authorization in Swagger
------------------------

Authorization requires making an OpenIDConnect endpoint with an
Authorization and Token endpoint (like with using [SeaCat
Auth](https://github.com/TeskaLabs/seacat-auth)).

After your endpoint has authorization, [here\'s an
example](https://github.com/TeskaLabs/asab/blob/master/examples/web-authz-userinfo.py),
add the Authorization and Token endpoints into your
[config](#configuration).

For the authorization bearer token to be added to the request, a scope
is needed to be put into the security parameter in a docstring. It does
not matter what it is called or if it exists, but it\'s needed to be
there. But \"[- oAuth:]{.title-ref}\" always needs to be there.

``` {.python}
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

After setting up Authorization, a green [Authorize]{.title-ref} button
should appear in the Swagger docs.

Configuration
-------------

For authorization you will need to add a [authorizationUrl]{.title-ref}
and \`tokenUrl\`:

``` {.ini}
[asab:doc]
authorizationUrl=http://localhost:8080/openidconnect/authorize
tokenUrl=http://localhost:8080/openidconnect/token
```

If you have an endpoint that requires a scope, you can add it with the
configuration file:

``` {.ini}
[asab:doc]
scopes=read,write
```

Tags
----

You can label your handler methods with custom tags. These tags are used
for grouping and sorting your endpoints on the documentation page.

``` {.python}
async def my_method(self, request):
"""<function description>
---
tags: ['custom tag 1', 'custom tag 2', 'custom tag 3']
"""
```

(Remember to use exactly three dashes on the separate line and put tags
in array with [\[\]]{.title-ref} even if you want to have a single tag).

If there is no custom tag defined, the tag name is automatically set to
be [module\_name]{.title-ref}. If you do not want to use custom tags but
still would like to sort the routes, you can configure the options in
the config file:

``` {.ini}
[asab:doc]
default_route_tag=class_name
```

There are two options for \`default\_route\_tag\`:

-   \`module\_name\`: All tags without custom name are displayed with
    the name of the **module** where the handler is defined.
-   \`class\_name\`: All tags without custom name are displayed with the
    name of the **class** where the handler is defined.
