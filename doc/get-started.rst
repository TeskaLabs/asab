Getting started
===============

Make sure you have both `pip <https://pip.pypa.io/en/stable/installing/>`_ and at
least version 3.5 of Python before starting. ASAB uses the new ``async``/``await``
syntax, so earlier versions of python won't work.

1. Install ASAB:  ``python3 -m pip install asab``
2. Create a file called ``main.py`` with the following code:


.. code:: python

    import asab

    class MyApplication(asab.Application):
        pass

    if __name__ == '__main__':
        app = MyApplication()
        app.run()


3. Run the server: ``python3 main.py``

You now have a working ASAB application server, ready for your mission!
