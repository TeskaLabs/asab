Creating REST HTTP webservice using  ASAB
===

## Overview

On lines below, we will discuss a creation of a basic ASAB microservice application capable of 
providing a REST HTTP API. We will be using MongoDB as an example database we perform the Create 
Read Update and Delete operations on.

### Prerequisites

1. Python version 3.6 or later
2. Asynchronous Server App Boilerplate (ASAB) version 20.3 or later
3. MongoDB instance
4. Postman


## Components

Our sample microservice will consist of several modules, each one serving a logical purpose within the
whole. The components are as follows (and they also hint a filestructure), and will be discussed in greater 
detail in their respective sections below, we will go from top to bottom:   
`myrestapi.py`, `./myrestapi/__init__.py`, `./myrestapi/app.py`, `./myrestapi/tutorial/handler.py`, and `./myrestapi/tutorial/service.py`  
While we start working on the microservice, we should have a testing MongoDB instance running, we will touch briefly 
on how to quickly do that.   
We will be using Postman to test the API and to generate json collection of available endpoints.

### MongoDB

As already mentioned above, we will be using MongoDB as this webservice's database instance. To make things simple, 
lets use a docker image (docker installation is not covered in this tutorial, but there are scores of good ones online 
should you run into any trouble). 
Pull this image:  
`https://hub.docker.com/_/mongo`   
And follow the detailed instructions on how to run it, if you choose to run the instance without password, dont forget 
to adjust the related asab.Config in the `./myrestapi/app.py`
 
### Postman

To test our webservice and provide some form of documentation to the future users of our microservice, we will 
be using Postman. You can download it here:   
`https://www.postman.com/downloads/`   
The postman is fairly straightforward to use and we are able to export documented endpoints via json or create a 
documentation.

#### myrestapi.py

This is the part, from where we run our app. We begin with the shebang line, that will tell the 
executing operating system, that we want python to execute this program.  
`#!/usr/bin/env python3`

We follow this up with imports, and all we will need here is our application:   
`from myrestapi.app import TutorialApp`   
Next, we instantiate an object of our TutorialApp class in the __main__ of the application, and we run the app:  
    
    if __name__ == '__main__':
        app = TutorialApp()   
        app.run()
        
#### ./myrestapi/app.py

Here, define our TutorialApp object, we will first need some imports:   
 
    import asab
    import asab.web
    import asab.web.rest
  
Now we need to add some default configs:    
 
    asab.Config.add_defaults(
	{
		'asab:storage': {
			'type': 'mongodb',
			'mongodb_uri': 'mongodb://mongouser:mongopassword@mongoipaddress:27017',
			'mongodb_database': 'mongodatabase'
		},
	})
    
Next, we describe the class, it inherits from the basic ASAB Application class, but we need to expand 
it a little (see comments in the code for more details):
    
    
    class TutorialApp(asab.Application):

	    def __init__(self):
            super().__init__()
            # Alternative for command-line flag -w
            import asab.storage
            self.add_module(asab.web.Module)
            self.add_module(asab.storage.Module)
    
            # Locate the web service
            self.WebService = self.get_service("asab.WebService")
            self.WebContainer = asab.web.WebContainer(self.WebService, "web")
            self.WebContainer.WebApp.middlewares.append(asab.web.rest.JsonExceptionMiddleware)
    
            # Initialize services, we can initialize one, or several API handlers/services here
            from .tutorial.handler import CRUDWebHandler
            from .tutorial.service import CRUDService
            self.CRUDService = CRUDService(self)
            # We need to pass the CRUDService as an argument, when instantiating the class
            self.CRUDWebHandler = CRUDWebHandler(self, self.CRUDService)

This could also be a BSPUMP.Application, enabling us to include a bspump pipeline in our microservice. 
To do this, inherit instead from bspump.BSPumpApplication and add service, connections and pipelines as 
usual.

#### ./myrestapi/\_\_init__.py

Init file is needed so myrestapi will work as a module.
Here we just import TutorialApp.
  
    from .app import TutorialApp


#### ./myrestapi/tutorial/handler.py

The handler is where HTTP Rest calls are handled and transformed into the actual (internal) service calls. From another 
perspective, the handler should contain only translation between REST calls and service interface. No actual 
'business logic' should be here.   
It is strongly suggested, 
that we do these CRUD methods one by one and test them straight away (the way we do this, we create a Handler method for 
creating first, then we create its Service method right after, and finally we test using Postman), if you did not set 
up your database test instance yet, now will be time to do it. If you struggle, check section below, where we use docker 
to setup a simple MongoDB containered instance. Now without further ado, lets jump into creating the handler.  
As usual, we start by importing modules:   

    import asab
    import asab.web.rest
    
    
Next is the CRUDWebhandler class:

    class CRUDWebHandler(object):
        def __init__(self, app, mongo_svc):
            self.CRUDService = mongo_svc
    
            web_app = app.WebContainer.WebApp
    
            web_app.router.add_put('/crud-myrestapi/{collection}', self.create)  # Create endpoint url
            web_app.router.add_get('/crud-myrestapi/{collection}/{id}', self.read_one)  # Read endpoint url
            web_app.router.add_put('/crud-myrestapi/{collection}/{id}', self.update)  # Update endpoint url
            web_app.router.add_delete('/crud-myrestapi/{collection}/{id}', self.delete)  # Delete endpoint url
    
        # Usually we will need to validate the body of incomming request and verify if it contains all the
        # desired fields and also their types.
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
    
            result = await self.CRUDService.create(collection, json_data)
            if result:
                return asab.web.rest.json_response(request, {"result": "OK"})
            else:
                asab.web.rest.json_response(request, {"result": "FAIL"})
    
    
        async def read_one(self, request):
            collection = request.match_info['collection']
            key = request.match_info['id']
            response = await self.CRUDService.read_one(collection, key)
            return asab.web.rest.json_response(request, response)
    
    
        @asab.web.rest.json_schema_handler({
            'type': 'object',
            'properties': {
                'field1': {'type': 'string'},
                'field2': {'type': 'number'},
                'field3': {'type': 'number'}
            }})
        async def update(self, request, *, json_data):
            collection = request.match_info['collection']
            key = request.match_info["id"]
    
            result = await self.CRUDService.update(collection, key, json_data)
            if result:
                return asab.web.rest.json_response(request, {"result": "OK"})
            else:
                asab.web.rest.json_response(request, {"result": "FAIL"})
    
        async def delete(self, request):
            collection = request.match_info['collection']
            key = request.match_info["id"]
            result = await self.CRUDService.delete(collection, key)
    
            if result:
                return asab.web.rest.json_response(request, {"result": "OK"})
            else:
                asab.web.rest.json_response(request, {"result": "FAIL"})

As we have noticed, the handler only handles the incomming requests and returns appropriate response.
All of the "logic", be it the specifics of the database connection, additional validations and other 
operations take place in the CRUDService.

#### ./myrestapi/tutorial/service.py

As mentioned above, this is where the inner workings of our microservice request processing actually is.   
Let's start as usual, by importing the desired modules:

    import asab
    import asab.storage.exceptions
    
    
    # We want to start logging here
    import logging

Initialize the logging:

    #

    L = logging.getLogger(__name__)

    #
Now we define the CRUDService class which inherits from the asab.Service class:

    class CRUDService(asab.Service):

	# Using inheritance from the asab.Service allows us to register the service as 'crud.CRUDService',
	# which would in turn enable us to call it by this name from elsewhere within the application.
	# We do not use this functionality for this service, but look around the code and we will find,
	# that it was silently used several times already for different ASAB services.
        def __init__(self, app, service_name='crud.CRUDService'):
            super().__init__(app, service_name)
            # And here we do it again, we use the "app.get_service()" to locate a service registered within
            # our app by its service name.
            self.MongoDBStorageService = app.get_service("asab.StorageService")
    
        # Below, we define class methods, that our handler will use to provide the desired functionality,
        # requested by our microservice users. These may not be limited to the methods tied to the handler's
        # CRUD functionality directly (e.g. the create, read, update and delete methods), but also any other
        # logical extensions of these, that are desirable. Bear in mind however, that we should always
        # strive for the "simplest code possible that works".
    
    
        async def create(self, collection, json_data):
            obj_id = json_data.pop("_id")
    
            cre = self.MongoDBStorageService.upsertor(collection, obj_id)
            for key, value in zip(json_data.keys(), json_data.values()):
                cre.set(key, value)
    
            try:
                await cre.execute()
                return "OK"
            except asab.storage.exceptions.DuplicateError as e:
                L.warning("Document you are trying to create already exists.")
                return None
    
    
        async def read_one(self, collection, key):
            response = await self.MongoDBStorageService.get_by(collection, "_id", key)
            return response
    
    
        async def update(self, collection, obj_id, document):
            original = await self.read_one(collection, obj_id)
            cre = self.MongoDBStorageService.upsertor(collection, original["_id"], original["_v"])
            for key, value in zip(document.keys(), document.values()):
                cre.set(key, value)
    
            try:
                await cre.execute()
                return "OK"
    
            except KeyError:
                return None
    
    
        async def delete(self, collection, key):
            try:
                await self.MongoDBStorageService.delete(collection, key)
                return True
            except KeyError:
                return False

There, all done! Now we need to see if all this comes together nicely and test it.

The application is implicitly running on 8080 port (see ASAB documentation).

We could try put method from mothod we choose PUT
Into url we set

    127.0.0.1:8080/crud-myrestapi/movie
   
Into the request body we put 

    {
    "field1": "something new",
    "field2": 5555,
    "field3": 44424
    }

Get update and delete method we could test just as put before.
Into the url we just put after collection name id of requested object.
For example:
    
    127.0.0.1:8080/crud-myrestapi/movie/some_id 

