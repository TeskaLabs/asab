# Contributing

We appreciate your effort to help us improve ASAB. In case you are interested in contributing, please follow the rules and conventions that we describe below.


## Coding conventions

In TeskaLabs, we are following [PEP8 Style Guide](https://www.python.org/dev/peps/pep-0008/) that provides guidelines and
best practices on how to write Python code to improve its readability and consistency.

To check if changes in your code are compliant with PEP8, you can use [flake8](https://flake8.pycqa.org/en/latest/):

```bash
flake8 .
```

!!! tip "Pre-commit hooks"

    It is highly recommended to create a pre-commit hook:

    ```shell title=".git/hooks/pre-commit"
    #!/bin/sh
    echo "Running flake8 ..."
    flake8 .
    ```

    Do not forget to make the hook executable:

    ``` bash
    chmod u+x .git/hooks/pre-commit
    ```

We shall provide some parts of the PEP8 Style Guide that we are focused on.

### Imports

Imports shall be written one-per-line style as per the example below

```python
import os
import sys
import logging
```

Following additional rules apply for imports:

1. Use **relative imports** when you import locally from a package.
2. Use **absolute imports** when you import from external package.
3. Never use `from ... import ...` because it unnecessarily increases complexity for readers
(unless you have very good reason for that). The only exception is `__init__.py` where it is
used for importing symbols that you want to expose as a given module public API.

## Documentation conventions

As a documentation engine, we use [mkdocs-material](https://squidfunk.github.io/mkdocs-material/). If you want to learn about various features provided by the engine, you can [read more](https://squidfunk.github.io/mkdocs-material/reference/).

MkDocs uses markdown for writing documentation.

