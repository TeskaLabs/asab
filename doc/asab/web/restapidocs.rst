REST API Docs
==============

ASAB's API service generates a `Swagger documentation <https://swagger.io/specification>`_ which automatically shows all
of your endpoints. However you will need to follow some steps to add summaries, tags and more

Before you start, make sure that you have a `REST API webserver <https://asab.readthedocs.io/en/latest/tutorial/web/chapter1.html>`_.

If you want Authorization in Swagger, you will need a OpenIDConnect endpoint.

In your microservice
-----------

First you need to initialize the API Service:

.. code-block:: python

    # Initialize API service
    self.ApiService = asab.api.ApiService(self)

    # Introduce Web to API Service
    self.ApiService.initialize_web()

If you want Authorization to work you will need to initialize the Authz service as well:

.. code-block:: python

    self.AuthzService = asab.web.authz.AuthzService(self)
    self.AuthzService.OAuth2Url = "http://localhost:8081/openidconnect"
    self.WebContainer.WebApp.middlewares.append(asab.web.authz.authz_middleware_factory(self, self.AuthzService))

After initializing the API Service a **/doc** endpoint will become available. You will notice
that some or none of your endpoints have summaries, tags or descriptions.

That's because you need to add a docstring to the endpoint function:

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

Authorization in Swagger
-----------
TODO..

Authorization requires having a OpenIDConnect endpoint (like SeaCat).

Configuration
-----------
TODO..

You need to put this in config etc. supports adding scopes etc.

.. code-block:: ini

    [asab:doc]
    authorizationUrl=http://localhost/seacat/api/openidconnect/authorize
    tokenUrl=http://localhost/seacat/api/openidconnect/token
    scopes=read,write