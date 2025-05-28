Asynchronous Server App Boilerplate
===================================
    
.. image:: https://img.shields.io/github/license/TeskaLabs/asab
    :target: https://github.com/TeskaLabs/asab/blob/master/LICENSE

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


Installation
------------


.. code:: shell

    $ pip install asab


Documentation
-------------

* `Documentation on Readthedocs <http://asab.readthedocs.io/>`_
* `Examples <https://github.com/TeskaLabs/asab/tree/master/examples>`_


Example
-------

.. code:: python

    #!/usr/bin/env python3
    import asab.web.rest
    
    class MyApplication(asab.Application):

        def __init__(self):
            super().__init__()

            # Create the Web server
            web = asab.web.create_web_server(self)

            # Add a route to the handler method
            web.add_get('/hello', self.hello)

        # This is the web request handler
        async def hello(self, request):
            return asab.web.rest.json_response(request, data="Hello, world!\n")
    
    if __name__ == '__main__':
        # Create and start the application
        app = MyApplication()
        app.run()


The application is available at http://localhost:8080/.
You can test it by:


.. code:: shell

    $ curl http://localhost:8080/hello


Microservices
-------------

Here is a growing list of Open Source microservices built using ASAB:

* `ASAB Iris <https://github.com/TeskaLabs/asab-iris>`_:  document rendering, sends output using email, SMS and instant messaging
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

**Commercial License:**

If you use this software without complying with the terms of the BSD 3-Clause License (e.g., failing to provide attribution or include the license text), you must purchase a commercial license.

For commercial licensing, please contact: sales@teskalabs.com

ASAB is maintained by `TeskaLabs Ltd <https://www.teskalabs.com>`_.


