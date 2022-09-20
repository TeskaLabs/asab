Asynchronous Server App Boilerplate
===================================

Asynchronous Server App Boilerplate (or ASAB for short) is a microservice *framework* for Python 3 and `asyncio`.
The aim of ASAB is to minimize the amount of code that needs to be written when building a microservice or an aplication server.
ASAB is fully asynchronous using async/await syntax from Python 3, making your code modern, non-blocking, speedy and hence scalable.
We make every effort to build ASAB container-friendly so that you can deploy ASAB-based microservice via Docker or Kubernetes in a breeze.

ASAB is the free and open-source software, available under BSD licence.
It means that anyone is freely licenced to use, copy, study, and change the software in any way, and the source code is openly shared so that people could voluntarily improve the design of the software.
Anyone can (and is encouraged to) use ASAB in his or her projects, for free.

ASAB is currently used for `microservices <https://en.wikipedia.org/wiki/Microservices>`_, web application servers, ETL or `stream processors <https://github.com/TeskaLabs/bspump>`_.

ASAB is developed on `GitHub <https://github.com/TeskaLabs/asab>`_.
Contributions are welcome!

.. image:: https://travis-ci.com/TeskaLabs/asab.svg?branch=master
    :target: https://travis-ci.com/TeskaLabs/asab

.. image:: https://badges.gitter.im/TeskaLabs/asab.svg
   :alt: Join the chat at https://gitter.im/TeskaLabs/asab
   :target: https://gitter.im/TeskaLabs/asab?utm_source=badge&utm_medium=badge&utm_campaign=pr-badge&utm_content=badge


Installation
------------

``pip install asab``


Documentation
-------------

* `Documentation on Readthedocs <http://asab.readthedocs.io/>`_
* `Examples <https://github.com/TeskaLabs/asab/tree/master/examples>`_


Example
-------

.. code:: python

    #!/usr/bin/env python3
    import asab
    import asab.web
    import aiohttp
    
    class MyApplication(asab.Application):

        def __init__(self):
            # Load the ASAB Web module
            super().__init__(modules=[asab.web.Module])

            # Locate the Web service
            websvc = self.get_service("asab.WebService")
            
            # Create the Web container
            container = asab.web.WebContainer(websvc, 'my:web', config={"listen": "0.0.0.0:8080"})
            
            # Add a route to the handler
            container.WebApp.router.add_get('/', self.hello)

        # This is the web request handler
        async def hello(self, request):
            return aiohttp.web.Response(text="Hello, world!\n")
    
    if __name__ == '__main__':
        # Create and start the application
        # The application will be available at http://localhost:8080/
        app = MyApplication()
        app.run()



Microservices
-------------

Here is a growing list of Open Source microservices built using ASAB:

* `SeaCat Auth <https://github.com/TeskaLabs/seacat-auth>`_: authentication, authorization, identity management, session management and other access control features



Highlights
----------

* Unified approach to **Configuration**
* **Logging** using reasonably configured Python ``logging`` module
* Build-in and custom **Metrics** with feeds into InfluxDB and Prometheus
* **Alerting** with integration to PagerDuty and OpsGenie.
* **HTTP Server** powered by `aiohttp <https://docs.aiohttp.org/en/stable/>`_ library
* **Apache Zookeeper Client** provides shared consensus across microservices’ cluster
* Persistent **storage** abstraction based on upsertor for MongoDB and ElasticSearch
* **Pub/Sub**
* **Dependency injection** using Modules and Services
* **Proactor pattern service** for long-running synchronous work
* **Task service**
* Unified microservice **API**


Automatic API documentation
---------------------------

The REST API is automatically documented using OpenAPI3 standard and the Swagger.

.. image:: https://github.com/TeskaLabs/asab/raw/master/doc/openapi3-swagger.jpg


Principles
----------

* Write once, use many times
* Keep it simple
* Well `documented <http://asab.readthedocs.io/>`_
* Asynchronous via Python 3 ``async``/``await`` and ``asyncio``
* `Event-driven Architecture <https://en.wikipedia.org/wiki/Event-driven_architecture>`_ / `Reactor pattern <https://en.wikipedia.org/wiki/Reactor_pattern>`_
* Single-threaded core but compatible with threads
* First-class support for `containerization <https://en.wikipedia.org/wiki/Operating-system-level_virtualization>`_
* Compatible with `pypy <http://pypy.org>`_, Just-In-Time Python compiler
* Kappa architecture
* Support for introspection
* Modularized


Video tutorial
^^^^^^^^^^^^^^

.. image:: http://img.youtube.com/vi/77StpWxOIBc/0.jpg
   :target: https://www.youtube.com/watch?v=77StpWxOIBc&list=PLhdpLpq_tPSDb2YMDwyz431pM1BPDWHNK


Licence
-------

ASAB is an open-source software, available under BSD 3-Clause License.  
ASAB is maintained by `TeskaLabs Ltd <https://www.teskalabs.com>`_.

