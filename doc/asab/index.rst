Asynchronous Server Application Boilerplate's documentation!
=============================================================

Asynchronous Server App Boilerplate (or ASAB for short) minimizes the amount of code that one needs to write when building a server application in Python 3.5+.

ASAB is developed `on GitHub <https://github.com/TeskaLabs/asab/>`_. Contributions are welcome!

ASAB is designed to be simple
-----------------------------

.. code:: python

    import asab

    class MyApplication(asab.Application):
    	pass

    if __name__ == "__main__":
    	app = MyApplication()
        app.run()
