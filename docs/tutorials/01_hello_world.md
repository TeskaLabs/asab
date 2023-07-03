Creating your first asab application
====================================

Make sure you have both [pip](https://pip.pypa.io/en/stable/installing/)
and at least version 3.7 of Python before starting. ASAB uses the new
`async`/`await` syntax, so earlier versions of python won't work.

1.  Install ASAB:

    ``` console
    pip3 install asab
    ```

2.  Create a file called `main.py` with the following code:

    ``` python title="main.py"
    #!/usr/bin/env python3
    import asab

    class MyApplication(asab.Application):
        async def main(self):
            print("Hello world")

    if __name__ == '__main__':
        app = MyApplication()
        app.run()
    ```

3.  Run the server:

    ``` console
    python3 main.py
    ```
    
    and you should've seen the output:
    ```
    Hello world!
    ```

    You are now successfully runinng an ASAB application server.

4.  Stop the application by `Control-C`.

    Note: The ASAB is designed around a so-called [event
    loop](https://en.wikipedia.org/wiki/Event_loop). It is meant primarily
    for server architectures. For that reason, it doesn't terminate and
    continue running and serving eventual requests.

Going into details
------------------

Let's look on the application one more time.


``` python title="main.py" linenums="1"

    #!/usr/bin/env python3 # (1)!
    import asab # (2)!

    class MyApplication(asab.Application): # (3)!
        async def main(self): # (4)!
            print("Hello world") # (5)!

    if __name__ == '__main__': # (6)!
        app = MyApplication()
        app.run()
```

1.  ASAB application uses a Python 3.7+. This is specified a by hashbang
line at the very beginning of the file.

2. ASAB is included from as `asab` module via an import
statement.

3. Every ASAB Application needs to have an application object. It is a
singleton; it means that the application must create and operate
precisely one instance of the application. ASAB provides the base
[asab.Application][#TODO] class that you need to
inherit from to implement your custom application class.

4. The `Application.main()` method is one of
the application lifecycle methods, that you can override to implement
desired application functionality. The `main` method is a
coroutine, so that you can await any tasks etc. in fully asynchronous
way. This method is called when ASAB application is executed and
initialized. The lifecycle stage is called "runtime".

5. In this example, we just print a message to a screen.

6. This part of the code is executed when the Python program is launched.
It creates the application object and executes the
`Application.run()`{.interpreted-text role="any"} method. This is a
standard way of how ASAB application is started.


Summary
-------

In this tutorial, you learned how to install `asab` and create a basic application.

Check out tutorials about how to build ASAB based [web server](./02_web_server.md).
