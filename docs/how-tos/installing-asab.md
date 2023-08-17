# Installation and first application

## Installation

ASAB is distributed via [pypi](https://pypi.org/project/asab/). There are three installation options:

=== "Using pip"

    We recommend using pip because it's the simplest installation method.

    ``` bash
    pip install asab
    ```

=== "Cloning from the Git repository"

    You can clone the repository from the master branch using pip:

    ``` bash
    pip install git+https://github.com/TeskaLabs/asab.git
    ```

    Or clone the repository manually:

    ``` bash
    git clone https://github.com/TeskaLabs/asab.git
    pip install -e .
    ```


=== "Using EasyInstall"

    You can install asab using the [EasyInstall](http://peak.telecommunity.com/DevCenter/EasyInstall) package manager.

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

    1. All ASAB applications use Python 3.7+. This is specified by a hashbang
    line at the very beginning of the file.

    2. ASAB is included from as `asab` module via an import
    statement.

    3. Every ASAB Application needs to have an application object. It is a
    **singleton**: the application must create and operate
    precisely one instance of the application. ASAB provides the base
    [asab.Application][#TODO] class that you need to
    inherit from to implement your custom application class.

    4. The `#!python Application.main()` method is one of
    the application lifecycle methods, that you can override to implement
    desired application functionality. The `main` method is a
    coroutine, so that you can await any tasks etc. in a fully asynchronous
    way. This method is called when the ASAB application is executed and
    initialized. The lifecycle stage is called "runtime".

    5. In this example, the app is printing a message to the screen.

    6. This part of the code is executed when you launch the Python program.
    It creates the application object and executes the `#!python run()` method which creates and runs an event loop. 
    This is the standard way of starting any ASAB application.


2.  Run the server:

    ``` shell
    python3 main.py
    ```

    If you see the following output, you have successfully created and run an ASAB application server.

    ```
    Hello world!
    ```


3.  Stop the application by pressing `Ctrl+C`.

    !!! info
        ASAB is designed around an [event loop](https://en.wikipedia.org/wiki/Event_loop). It is meant primarily
        for server architectures. For that reason, an ASAB application keeps running and serving requests unless or until you terminate the application. See [run time](../reference/application/reference.md#run-time).

You can continue with a step-by-step tutorial on how to build an ASAB-based [web server](./web_server.md).
