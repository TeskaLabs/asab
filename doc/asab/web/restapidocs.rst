REST API Docs
==============

ASAB's API service generates a `Swagger documentation <https://swagger.io/specification>`_ which automatically shows all
of your endpoints. However you will need to follow some steps to add summaries, tags and more.

Before you start, make sure that you have a `REST API microservice <https://asab.readthedocs.io/en/latest/tutorial/web/chapter2.html>`_.

If you want Authorization in Swagger, you will need a OpenIDConnect endpoint.

In your microservice
-----------

First you need to initialize the API Service:

.. code-block:: python

    # Initialize API service
    self.ApiService = asab.api.ApiService(self)

    # Introduce Web to API Service
    self.ApiService.initialize_web()

After initializing the API Service a **/doc** endpoint will become available. You will notice
that some or none of your endpoints have summaries, tags or descriptions.

That's because you need to add a docstring to your endpoint method:

.. code-block:: python

    async def endpoint(self, request):
        """
        Summary looks like this and takes the first line from docstring.

        Description of what this endpoint does.

        ---
        tags: [asab.mymicroservice]
        """

The first line of the docstring gets shown as a summary next to the endpoint in Swagger.
There are also extra parameters you can set like tags, which work like categories.

The description of the microservice also needs a docstring for it to show up:

.. code-block:: python

    class TutorialApp(asab.Application):
        """
        TutorialApp is the best microservice in the world!

        <marquee>The description supports HTML tags</marquee>
        """

Authorization in Swagger
-----------
Authorization requires having an OpenIDConnect endpoint with an Authorization and Token endpoint (like SeaCat).

First initialize the Authz service in your microservice:

.. code-block:: python

    self.AuthzService = asab.web.authz.AuthzService(self)
    self.AuthzService.OAuth2Url = "http://localhost:8081/openidconnect"
    self.WebContainer.WebApp.middlewares.append(asab.web.authz.authz_middleware_factory(self, self.AuthzService))

Setting the OAuth2Url is important, otherwise authorization will not work.

You need to add an Authz header above at the endpoint method:

.. code-block:: python

    @asab.web.authz.required("resource:topsecret")
    async def top_secret_endpoint(self, request):

Then add the Authorization and Token endpoints into your `config <#configuration>`_.

After setting up Authorization, a green `Authorize` button will appear. Authorizing will add a bearer token to every
request you do inside Swagger. You will get unauthorized if you refresh the page.

If it does not add a bearer token, or it does not authorize you at all, retrace your steps and try again.

Configuration
-----------
Some parts of Swagger can be changed with this configuration.

For authorization you will need to add a `authorizationUrl` and `tokenUrl`:

.. code-block:: ini

    [asab:doc]
    authorizationUrl=http://localhost:8080/openidconnect/authorize
    tokenUrl=http://localhost:8080/openidconnect/token

If you have an endpoint that requires a scope, you can add it with the configuration file:

.. code-block:: ini

    [asab:doc]
    scopes=read,write

You can change the version tag that shows next to the name of your microservice:

.. code-block:: ini

    [asab:doc]
    version=1.0.0