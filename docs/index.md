# Asynchronous Server Application Boilerplate

**Asynchronous Server App Boilerplate** (or ASAB for short) is an open-source microservice platform for Python 3.7+ and [asyncio](https://docs.python.org/3/library/asyncio.html). 
ASAB aims to minimize the amount of code that needs to be written
when building a microservice or an application server. 
ASAB is fully asynchronous using async/await syntax from Python 3, making your code modern,
non-blocking, speedy and hence scalable. 
We make every effort to build ASAB container-friendly so that you can deploy
ASAB-based microservice via Docker or Kubernetes in a breeze.

Anyone can (and is encouraged to) use ASAB in his or her projects, for free.


[Get started](getting-started/installation_first_app.md){ .md-button .md-button--primary } [Read more about TeskaLabs](https://docs.teskalabs.com/){ .md-button .md-button--primary } [Contribute](contributing.md){ .md-button .md-button--primary }

!!! success "ASAB is the right choice when:"

    - :material-server: you want to build a microservice or an application server
    - :material-language-python: you are using Python 3.7+
    - :material-clock-fast: you want to utilize asynchronous I/O
    - :material-file-document-edit: you want to write non-blocking, speedy and scalable code

!!! example "Here is a complete example of a fully working microservice:"

    ``` python title="hello_world.py"
    import asab

    class MyApplication(asab.Application):
        async def main(self):
            print("Hello world!")
            self.stop()

    if __name__ == "__main__":
        app = MyApplication()
        app.run()
    ```


!!! info "Development"

    - :teskalabs: A current maintainer of ASAB is a [TeskaLabs Ltd](https://teskalabs.com) company.

    - :simple-github: ASAB is developed [on GitHub](https://github.com/TeskaLabs/asab/).
    Contributions are most welcome! If you want to help us improve asab, check our [contribution rules](./contributing.md).

    - :simple-opensourceinitiative: ASAB is free and open-source software, available under BSD licence.
    Anyone is freely licensed to use, copy, study, and change the
    software in any way, and the source code is openly shared so that people
    could voluntarily improve the design of the software.
