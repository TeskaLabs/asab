Asynchronous Server App Boilerplate
===================================

Asynchronous Server App Boilerplate (or ASAB for short) is a microservice platform for Python 3.5+ and asyncio.
The aim of ASAB is to minimize the amount of code that needs to be written when building a microservice or an aplication server.
ASAB is fully asynchronous using async/await syntax from Python 3.5, making your code modern, non-blocking, speedy and hence scalable.
We make every effort to build ASAB container-friendly so that you can deploy ASAB-based microservice via Docker or Kubernetes in a breeze.

ASAB is the free and open-source software, available under BSD licence.
It means that anyone is freely licenced to use, copy, study, and change the software in any way, and the source code is openly shared so that people could voluntarily improve the design of the software.
Anyone can (and is encouraged to) use ASAB in his or her projects, for free.

ASAB is currently used for `microservices <https://en.wikipedia.org/wiki/Microservices>`_, web application servers, ETL or `stream processors <https://github.com/TeskaLabs/bspump>`_.

ASAB is developed on `GitHub <https://github.com/TeskaLabs/asab>`_.
Contributions are welcome!

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
    
    class MyApplication(asab.Application):
        async def main(self):
            print("Hello world!")
            self.stop()
    
    if __name__ == '__main__':
        app = MyApplication()
        app.run()


Principles
----------

* Write once, use many times
* Keep it simple
* Well `documented <http://asab.readthedocs.io/>`_
* Asynchronous via Python 3.5+ ``async``/``await`` and ``asyncio``
* `Event-driven Architecture <https://en.wikipedia.org/wiki/Event-driven_architecture>`_ / `Reactor pattern <https://en.wikipedia.org/wiki/Reactor_pattern>`_
* Single-threaded core but compatible with threads
* Good support for `containerization <https://en.wikipedia.org/wiki/Operating-system-level_virtualization>`_
* Compatible with `pypy <http://pypy.org>`_, Just-In-Time compiler capable of boosting Python code performace more then 5x times
* Support for introspection
* Modularized


High-level architecture
-----------------------

.. image:: https://github.com/TeskaLabs/asab/raw/master/doc/_static/asab-architecture.png
    :alt: Schema of ASAB high-level achitecture


Licence
-------

ASAB is an open-source software, available under BSD 3-Clause License.  
ASAB is maintained by `TeskaLabs Ltd <https://www.teskalabs.com>`_.

