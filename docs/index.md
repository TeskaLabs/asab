---
title: My Document
summary: A brief description of my document.
authors:
    - Waylan Limberg
    - Tom Christie
date: 2018-07-10
some_url: https://example.com
---

Asynchronous Server Application Boilerplate
===========================================

Asynchronous Server App Boilerplate (or ASAB for short) is a
microservice platform for Python 3.7+ and [asyncio](https://docs.python.org/3/library/asyncio.html). ASAB
aims to minimize the amount of code that needs to be written when
building a microservice or an application server. ASAB is fully
asynchronous using async/await syntax from Python 3, making your code
modern, non-blocking, speedy and hence scalable. We make every effort to
build ASAB container-friendly so that you can deploy ASAB-based
microservice via Docker or Kubernetes in a breeze.

ASAB is free and open-source software, available under BSD licence. It
means that anyone is freely licenced to use, copy, study, and change the
software in any way, and the source code is openly shared so that people
could voluntarily improve the design of the software. Anyone can (and is
encouraged to) use ASAB in his or her projects, for free. A current
maintainer is a [TeskaLabs Ltd](https://teskalabs.com) company.

ASAB is developed [on GitHub](https://github.com/TeskaLabs/asab/).
Contributions are welcome!

ASAB is designed to be powerful yet simple
------------------------------------------

Here is a complete example of a fully working microservice:

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

ASAB is the right choice when
-----------------------------

> -   using Python 3.7+.
> -   building the microservice or the application server.
> -   utilizing asynchronous I/O (aka
>     [asyncio](https://docs.python.org/3/library/asyncio.html)).

``` yaml
theme:
  features:
    - content.code.annotate # (1)
```

1.  :man_raising_hand: I'm a code annotation! I can contain `code`, __formatted
    text__, images, ... basically anything that can be written in Markdown.