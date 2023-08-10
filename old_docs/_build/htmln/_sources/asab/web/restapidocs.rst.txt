REST API Docs
==============

ASAB's API service generates a `Swagger documentation <https://swagger.io/specification>`_ which automatically shows all
of your endpoints and you can add summaries, descriptions, tags and more.

If you want Authorization in Swagger docs, you will need an OpenIDConnect endpoint.

In your microservice
--------------------

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

Also by adding a docstring to your ASAB Application, a description will be automatically added to the top of the Swagger docs:

.. code-block:: python

    class TutorialApp(asab.Application):
        """
        TutorialApp is the best microservice in the world!

        <marquee>The description supports HTML tags</marquee>
        """

Authorization in Swagger
------------------------

Authorization requires making an OpenIDConnect endpoint with an Authorization and Token endpoint (like with using `SeaCat Auth <https://github.com/TeskaLabs/seacat-auth>`_).

After your endpoint has authorization, `here's an example <https://github.com/TeskaLabs/asab/blob/master/examples/web-authz-userinfo.py>`_,
add the Authorization and Token endpoints into your `config <#configuration>`_.

For the authorization bearer token to be added to the request, a scope is needed to be put into the security parameter in a docstring.
It does not matter what it is called or if it exists, but it's needed to be there. But "`- oAuth:`" always needs to be there.

.. code-block:: python

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

After setting up Authorization, a green `Authorize` button should appear in the Swagger docs.

Configuration
-------------

For authorization you will need to add a `authorizationUrl` and `tokenUrl`:

.. code-block:: ini

    [asab:doc]
    authorizationUrl=http://localhost:8080/openidconnect/authorize
    tokenUrl=http://localhost:8080/openidconnect/token

If you have an endpoint that requires a scope, you can add it with the configuration file:

.. code-block:: ini

    [asab:doc]
    scopes=read,write
