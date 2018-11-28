Asynchronous Server Application Boilerplate's documentation
===========================================================

Asynchronous Server App Boilerplate (or ASAB for short) is a microservice platform for Python 3.5+ and `asyncio`.
The aim of ASAB is to minimizes the amount of code that needs to be written when building a microservice or an aplication server.

ASAB is the free and open-source software, available under BSD licence.
It means that anyone is freely licenced to use, copy, study, and change the software in any way, and the source code is openly shared so that people could voluntarily improve the design of the software.
Anyone can (and is encouraged to) use ASAB in his or her projects, for free.

ASAB is developed `on GitHub <https://github.com/TeskaLabs/asab/>`_.
Contributions are welcome!
A current maintainer is a `TeskaLabs Ltd <https://teskalabs.com>`_ company.


ASAB is designed to be powerful yet simple
------------------------------------------

Here is a complete example of the fully working microservice:

.. code:: python

    import asab

    class MyApplication(asab.Application):
        async def main(self):
            print("Hello world!")
            self.stop()

    if __name__ == "__main__":
        app = MyApplication()
        app.run()


ASAB is a right choice when
---------------------------

 - using Python 3.5+.
 - utilizing asynchronous I/O (aka `asyncio <https://docs.python.org/3/library/asyncio.html>`_).
 - building a microservice or an application server.
