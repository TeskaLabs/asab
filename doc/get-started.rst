Getting started
===============

Make sure you have both `pip <https://pip.pypa.io/en/stable/installing/>`_ and at
least version 3.5 of Python before starting. ASAB uses the new ``async``/``await``
syntax, so earlier versions of python won't work.

1. Install ASAB:

.. code:: bash

    $ pip3 install asab


2. Create a file called ``main.py`` with the following code:


.. code:: python

    #!/usr/bin/env python3
    import asab

    class MyApplication(asab.Application):
        async def main(self):
            print("Hello world")

    if __name__ == '__main__':
        app = MyApplication()
        app.run()


3. Run the server:

.. code:: bash

     $ python3 main.py
     Hello world

You are now successfully runinng an ASAB application server.


4. Stop the application by ``Control-C``.

Note: The ASAB is designed around a so-called `event loop <https://en.wikipedia.org/wiki/Event_loop>`_.
It is meant primarily for server architectures.
For that reason, it doesn't terminate and continue running and serving eventual requests.



Going into details
------------------

.. code:: python

    #!/usr/bin/env python3

ASAB application uses a Python 3.5+.
This is specified a by hashbang line at the very begginig of the file, on the line number 1.


.. code:: python

    import asab


ASAB is included from as `asab` module via an import statement.


.. code:: python

    class MyApplication(asab.Application):

Every ASAB Application needs to have an application object.
It is a singleton; it means that the application must create and operate precisely one instance of the application.
ASAB provides the base :any:`Application` class that you need to inherit from to implement your custom application class.


.. code:: python

        async def main(self):
            print("Hello world")

The :any:`Application.main()` method is one of the application lifecycle methods, that you can override to implement desired application functionality.
The `main` method is a coroutine, so that you can await any tasks etc. in fully asynchronous way.
This method is called when ASAB application is executed and initialized.
The lifecycle stage is called "runtime".

In this example, we just print a message to a screen.



.. code:: python

    if __name__ == '__main__':
        app = MyApplication()
        app.run()

This part of the code is executed when the Python program is launched.
It creates the application object and executes the :any:`Application.run()` method.
This is a standard way of how ASAB application is started.


Next steps
----------

Chech out tutorials about how to build ASAB based :doc:`web server <tutorial/web/chapter1>`.

