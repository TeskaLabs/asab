Getting started
===============

Make sure you have both [pip](https://pip.pypa.io/en/stable/installing/)
and at least version 3.7 of Python before starting. ASAB uses the new
`async`/`await` syntax, so earlier versions of python won\'t work.

1.  Install ASAB:

``` {.bash}
$ pip3 install asab
```

2.  Create a file called `main.py` with the following code:

``` {.python}
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

``` {.bash}
$ python3 main.py
Hello world
```

You are now successfully runinng an ASAB application server.

4.  Stop the application by `Control-C`.

Note: The ASAB is designed around a so-called [event
loop](https://en.wikipedia.org/wiki/Event_loop). It is meant primarily
for server architectures. For that reason, it doesn\'t terminate and
continue running and serving eventual requests.

Going into details
------------------

``` {.python}
#!/usr/bin/env python3
```

ASAB application uses a Python 3.7+. This is specified a by hashbang
line at the very begginig of the file, on the line number 1.

``` {.python}
import asab
```

ASAB is included from as [asab]{.title-ref} module via an import
statement.

``` {.python}
class MyApplication(asab.Application):
```

Every ASAB Application needs to have an application object. It is a
singleton; it means that the application must create and operate
precisely one instance of the application. ASAB provides the base
`Application`{.interpreted-text role="any"} class that you need to
inherit from to implement your custom application class.

``` {.python}
async def main(self):
    print("Hello world")
```

The `Application.main()`{.interpreted-text role="any"} method is one of
the application lifecycle methods, that you can override to implement
desired application functionality. The [main]{.title-ref} method is a
coroutine, so that you can await any tasks etc. in fully asynchronous
way. This method is called when ASAB application is executed and
initialized. The lifecycle stage is called \"runtime\".

In this example, we just print a message to a screen.

``` {.python}
if __name__ == '__main__':
    app = MyApplication()
    app.run()
```

This part of the code is executed when the Python program is launched.
It creates the application object and executes the
`Application.run()`{.interpreted-text role="any"} method. This is a
standard way of how ASAB application is started.

Next steps
----------

Check out tutorials about how to build ASAB based
`web server <tutorial/web/chapter1>`{.interpreted-text role="doc"}.
