# Installation and first application

## Installation

ASAB is distributed via [pypi](https://pypi.org/project/asab/). For installing ASAB, there are three options you can choose from:

=== "Using pip"

    This is the simplest and recommended installation method.

    ``` bash
    pip install asab
    ```

=== "Cloning from git repository"

    You can clone it from master branch using pip:

    ``` bash
    pip install git+https://github.com/TeskaLabs/asab.git
    ```

    Or you can clone the repository manually:

    ``` bash
    git clone https://github.com/TeskaLabs/asab.git
    pip install -e .
    ```


=== "Using EasyInstall"

    You can install asab using [EasyInstall](http://peak.telecommunity.com/DevCenter/EasyInstall) package manager.

    ``` bash
    easy_install asab
    ```

## Creating your first application

1.  Create a file called `main.py` with the following code:

        
    ``` python title="main.py" linenums="1"

        #!/usr/bin/env python3 
        # (1)!
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

    1. ASAB is included from as `asab` module via an import
    statement.

    1. Every ASAB Application needs to have an application object. It is a
    **singleton**: the application must create and operate
    precisely one instance of the application. ASAB provides the base
    [asab.Application][#TODO] class that you need to
    inherit from to implement your custom application class.

    1. The `#!python Application.main()` method is one of
    the application lifecycle methods, that you can override to implement
    desired application functionality. The `main` method is a
    coroutine, so that you can await any tasks etc. in fully asynchronous
    way. This method is called when ASAB application is executed and
    initialized. The lifecycle stage is called "runtime".

    1. In this example, we just print a message to a screen.

    2. This part of the code is executed when the Python program is launched.
    It creates the application object and executes the `#!python run()` method which creates and runs an event loop. 
    This is a standard way of how ASAB application is started.


2.  Run the server:

    ``` shell
    python3 main.py
    ```

    If you see the following output, you have successfully created and run an ASAB application server.

    ```
    Hello world!
    ```


3.  Stop the application by `Ctrl+C`.

    !!! info
        The ASAB is designed around a so-called [event
        loop](https://en.wikipedia.org/wiki/Event_loop). It is meant primarily
        for server architectures. For that reason, it doesn't terminate and
        continue running and serving eventual requests.

You can continue with a step-by-step tutorial on how to build ASAB based [web server](./web_server.md).
