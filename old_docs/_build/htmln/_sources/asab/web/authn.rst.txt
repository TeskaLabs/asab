Authn module
=================

.. py:currentmodule:: asab.web.authn

Module :py:mod:`asab.web.authn` provides middlewares and classes to allow only authorized users access specified web server endpoints.
It also allows to forward requests to the authorization server via instance of OAuthForwarder.

Currently available authorization technologies include OAuth 2.0, public/private key and HTTP basic auth.

Middleware
------------

.. py:method:: authn_middleware_factory(app, implementation, *args, **kwargs):

First step is to define the authorization implementation, which can be the OAuth 2.0, public/private key or
HTTP basic auth. Depending on the implementation, there are arguments which further specify the authorization
servers that are going to be used.

When it comes to OAuth 2.0, there are :any:`methods` for every OAuth 2.0 server, that is going to be used for authorization
and obtainment of the user identity. The relevant method is selected based on access token prefix, that is received
from the client in the HTTP request (:any:`Authorization` header):

`Authorization: Bearer <OAUTH-SERVER-ID>-<ACCESS_TOKEN>`

The following example illustrates how to register a middleware inside the web server container with OAuth 2.0
implementation and GitHub method.

.. code:: python

    container.WebApp.middlewares.append(
        asab.web.authn.authn_middleware_factory(self,
            "oauth2client",  # other implementations include: "basicauth" and "pubkeyauth"
            methods=[
            # Use GitHub OAuth provider
            asab.web.authn.oauth.GitHubOAuthMethod(),
            ],
        )
    )


Decorators
------------

In order to require authorization for a specific endpoint and thus utilize the output of the registered middleware,
it is necessary to decorate its handler method with :any:`authn_required_handler` decorator.

The decorator provide the handler method with an :any:`identity` argument, which contains the user identity received
from the authorization server. Thus the user information can be further evaluated or included as part of the response.
To receive just the identity information but not force the authorization for the endpoint, the :any:`authn_optional_handler`
can be used instead.

The following example illustrates how to use the :any:`authn_required_handler` decorator in order to enforce the
authorization and receive user identity in the :any:`identity` argument:

.. code:: python

    @asab.web.authn.authn_required_handler
    async def user(self, request, *, identity):
        return asab.web.rest.json_response(request=request, data={
            'message': '"{}", you have accessed our secured "user" endpoint.'.format(identity),
        })


Example
------------

To see & try the full example which utilizes OAuth 2.0 middleware and decorators, please see the code
in the following link:

`https://github.com/TeskaLabs/asab/blob/master/examples/web-authn-oauth.py <https://github.com/TeskaLabs/asab/blob/master/examples/web-authn-oauth.py>`_

Another example serves to demonstrate the public/private key authorization via ASAB web client ssl cert authorization:

`https://github.com/TeskaLabs/asab/blob/master/examples/web-authn-pubkey.py <https://github.com/TeskaLabs/asab/blob/master/examples/web-authn-pubkey.py>`_
