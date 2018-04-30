Asynchronous Server Application Boilerplate
===========================================

Asynchronous Server App Boilerplate (or *ASAB* for short) minimizes the amount of code that needs to be written when building a server application in Python.
ASAB is fully asynchronous, this means you can use the new shiny async/await syntax from Python 3.5, making your code non-blocking, speedy and hence scalable.

We hope you will find *ASAB* fun and easy to use, especially when you are about to build a Python-based application server such as web application server, MQTT server, microservice container, ETL or `stream processor <https://github.com/TeskaLabs/bspump>`_.

ASAB is developed on `GitHub <https://github.com/TeskaLabs/asab>`_.

Contributions are welcome.

Have fun!


.. image:: https://badges.gitter.im/TeskaLabs/asab.svg
   :alt: Join the chat at https://gitter.im/TeskaLabs/asab
   :target: https://gitter.im/TeskaLabs/asab?utm_source=badge&utm_medium=badge&utm_campaign=pr-badge&utm_content=badge


Installation
------------

``pip install asab``


Documentation
-------------

`Documentation on Readthedocs <http://asab.readthedocs.io/>`_


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

