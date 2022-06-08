Create microservice with REST API
=================================

With this tutorial, you can create a basic ASAB microservice application providing a REST HTTP API. 
Your CRUD microservice will implement Create, Read, Update and Delete functionality.
MongoDB will be used as an example database.


Prerequisites
-------------

1. Python version 3.6 or later
2. Asynchronous Server App Boilerplate (ASAB) version 20.3 or later
3. MongoDB instance
4. Postman

.. note::
	We will use Docker to run MongoDB. Docker installation is not covered in this tutorial, but there are scores of good ones online should you run into any trouble. If you're not familiar with Docker yet, it is great opportunity to start. https://www.docker.com/get-started/

Components
----------

The sample microservice will consist of several logical modules. 
These components are as follows (and also indicate the file structure) and will be discussed in more detail in the respective sections below, going from top to bottom: 

.. code::

	.
	└── myrestapi.py
	─── myrestapi
		└── __init__.py
		─── app.py
		─── tutorial
			└── handler.py
			└── service.py


`myrestapi.py`, `./myrestapi/__init__.py`, `./myrestapi/app.py`, `./myrestapi/tutorial/handler.py`, and `./myrestapi/tutorial/service.py`  


MongoDB
-------

To make things simple, let's use a Docker image.

Pull this image:  
https://hub.docker.com/_/mongo

You can simply use the command below to run it. If you choose to run the instance without password, don't forget 
to adjust the related **asab.Config** in `./myrestapi/app.py`.

.. code:: bash

	docker run -d -p 27017:27017 \
		-e MONGO_INITDB_ROOT_USERNAME=user \
		-e MONGO_INITDB_ROOT_PASSWORD=secret \
		mongo


Postman
-------

Use Postman to test the webservice REST API. 

You can download it here:   
https://www.postman.com/downloads/

The postman is fairly straightforward to use. You can create your collection of requests, save them, or automatically generate documentation. 


myrestapi.py
------------

This is where everything starts. Begin with the shebang line, which tells the 
executing operating system **python** should execute this program.  

.. code:: python

	#!/usr/bin/env python3

Imports follow. All you need here is the application. It is called **TutorialApp**:

.. code:: python 

	from myrestapi.app import TutorialApp 

Next, instantiate an object of your TutorialApp class in the __main__ of the application, and run the app:  

.. code:: python 

	if __name__ == '__main__':
		app = TutorialApp()   
		app.run()



app.py
------

`./myrestapi/app.py`

Define the TutorialApp object. 

Imports first:   

.. code:: python 

	import asab
	import asab.web
	import asab.web.rest
	import asab.storage


Add some configuration:

.. code:: python 
 
	asab.Config.add_defaults(
	{
		'asab:storage': {
			'type': 'mongodb',
			'mongodb_uri': 'mongodb://mongouser:mongopassword@mongoipaddress:27017',
			'mongodb_database': 'mongodatabase'
		},
	})

.. note::
	To make things more simple, Mongo credentials are stored here as default configuration. 
	Usually, you provide your app with configuration file. Learn more in section :ref:`configuration-ref`.

Next, describe the class, it inherits from the basic ASAB Application class, but you need to expand 
it a little:
	
.. code:: python 

	class TutorialApp(asab.Application):

		def __init__(self):
			super().__init__()
			# Register modules
			self.add_module(asab.web.Module)
			self.add_module(asab.storage.Module)
	
			# Locate the web service
			self.WebService = self.get_service("asab.WebService")
			self.WebContainer = asab.web.WebContainer(
				self.WebService, "web"
			)
			self.WebContainer.WebApp.middlewares.append(
				asab.web.rest.JsonExceptionMiddleware
			)
	
			# Initialize services
			from .tutorial.handler import CRUDWebHandler
			from .tutorial.service import CRUDService
			self.CRUDService = CRUDService(self)
			self.CRUDWebHandler = CRUDWebHandler(
				self, self.CRUDService
			)


\_\_init\_\_.py
----------------

`./myrestapi/__init__.py`

Init file is needed so myrestapi will work as a module.
Just import the TutorialApp.

.. code:: python 
  
	from .app import TutorialApp


handler.py
----------

`./myrestapi/tutorial/handler.py`

The handler is where HTTP Rest calls are handled and transformed into the actual (internal) service calls. From another 
perspective, the handler should contain only translation between REST calls and service interface. No actual 
'business logic' should be here.   
It is strongly suggested to build these CRUD methods one by one and test them straight away. If you haven't set 
up your database test instance yet, now is the time to do it.

As usual, we start by importing modules:   

.. code:: python 

	import asab
	import asab.web.rest
	
	
Let's start with two methods - `create` and `read` which allow us to write into database and check the record.

.. code:: python 

	class CRUDWebHandler(object):
		def __init__(self, app, mongo_svc):
			self.CRUDService = mongo_svc
			web_app = app.WebContainer.WebApp
			web_app.router.add_put(
				'/crud-myrestapi/{collection}',
				self.create
			)
			web_app.router.add_get(
				'/crud-myrestapi/{collection}/{id}',
				self.read_one
			)
	
		@asab.web.rest.json_schema_handler({
			'type': 'object',
			'properties': {
				'_id': {'type': 'string'},
				'field1': {'type': 'string'},
				'field2': {'type': 'number'},
				'field3': {'type': 'number'}
			}})
		async def create(self, request, *, json_data):
			collection = request.match_info['collection']
	
			result = await self.CRUDService.create(
				collection, json_data
			)
			if result:
				return asab.web.rest.json_response(
					request, {"result": "OK"}
				)
			else:
				asab.web.rest.json_response(
					request, {"result": "FAIL"}
				)
	
	
		async def read_one(self, request):
			collection = request.match_info['collection']
			key = request.match_info['id']
			response = await self.CRUDService.read_one(
				collection, key
			)
			return asab.web.rest.json_response(
				request, response
			)
	
The handler only accepts the incomming requests and returns appropriate response.
All of the "logic", be it the specifics of the database connection, additional validations and other 
operations take place in the CRUDService.

POST and PUT requests typically come with data in body. Providing your `WebContainer` with `JsonExceptionMiddleware` enables you to validate a JSON input
using `@asab.web.rest.json_schema_handler` decorator and JSON schema (https://json-schema.org/).

ASAB WebServer is built on top of the aiohttp library. For further details please visit https://docs.aiohttp.org/en/stable/index.html.


service.py
----------

`./myrestapi/tutorial/service.py`

As mentioned above, this is where the inner workings of the microservice request processing actually is.   
Let's start as usual, by importing the desired modules:

.. code:: python 

	import asab
	import asab.storage.exceptions


We want to start logging here:

.. code:: python 

	import logging
	#

	L = logging.getLogger(__name__)

	#


Now define the CRUDService class which inherits from the `asab.Service` class.


.. note::
	`asab.Service` is a lightweight yet powerful abstract class providing your object with 3 functionalities:

	- Name of the `asab.Service` is registered in the app and can be called from the `app` object anywhere in your code.
	- `asab.Service` class implements `initialize()` and `finalize()` coroutines which help you to handle asynchronous operations in init and exit time of your application.
	- `asab.Service` registers application object as `self.App` for you.


.. code:: python 

	class CRUDService(asab.Service):

		def __init__(self, app, service_name='crud.CRUDService'):
			super().__init__(app, service_name)
			self.MongoDBStorageService = app.get_service(
				"asab.StorageService"
			)

		async def create(self, collection, json_data):
			obj_id = json_data.pop("_id")
	
			cre = self.MongoDBStorageService.upsertor(
				collection, obj_id
			)

			for key, value in zip(
				json_data.keys(), json_data.values()
			):
				cre.set(key, value)
	
			try:
				await cre.execute()
				return "OK"
			except asab.storage.exceptions.DuplicateError as e:
				L.warning(
					"Document you are trying to create already exists."
				)
				return None
	
	
		async def read_one(self, collection, key):
			response = await self.MongoDBStorageService.get_by(
				collection, "_id", key
			)
			return response

	
`asab.StorageService` initialized in `app.py` as part of the `asab.storage.Module` enables connection to MongoDB.
Further on, there are two methods providing the handler with the desired functionalities.

**Now test it.**

The application is implicitly running on **8080** port.
Open the Postman and set new request.

Try PUT method:

.. code::

	127.0.0.1:8080/crud-myrestapi/movie
   
Insert into the request body: 

.. code::

	{
	"_id": "1",
	"field1": "something new",
	"field2": 5555,
	"field3": 44424
	}

When there's a record in your database, try to read it!
For example:

.. code::
	
	127.0.0.1:8080/crud-myrestapi/movie/1

Is your response with 200 status code? Does it return desired data?
Congratulation to your first ASAB microservice!

Oh, wait...

**C**, **R**... What about **Update** and **Delete** you ask? 

You already know everything to add next functionality!



Troubleshooting
---------------

**ERROR**

.. code::
	
	ModuleNotFoundError: No module named 'pymongo.mongo_replica_set_client'

Try:

.. code::
	
	pip install motor


--------------------

**ERROR**

.. code::

	OSError: [Errno 98] error while attempting to bind on address ('0.0.0.0', 8080): address already in use

Try to kill process listening on 8080 or add [web] section into configuration:

.. code::

	asab.Config.add_defaults(
	{
		'asab:storage': {
			'type': 'mongodb',
			'mongodb_uri': 'mongodb://mongouser:mongopassword@mongoipaddress:27017',
			'mongodb_database': 'mongodatabase'
		},
		'web': {
			'listen': '0.0.0.0 8081'
		}
	})

-------------------

**ERROR**

No error at all, no response either.

Try to check the Mongo database credentials. Does your credentials in configuration in `app.py` fit the ones you entered when running Mongo Docker image?
