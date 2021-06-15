Cross-Origin Resource Sharing (CORS)
====================================

When you create a web container, you specify a config section name. In the example below it’s `myapp:web`:

.. code:: python

    asab.web.WebContainer(self.WebService, "myapp:web")

You can then configure CORS by running your app with a config file with this contents:

.. code::
	[myapp:web]
	cors=*
	cors_preflight_paths=/*



- **cors**: contents of the Access-Control-Allow-Origin header
- **cors_preflight_paths**: a pattern for endpoints that shall return responses to pre-flight requests (OPTIONS). Value must start with "/".
