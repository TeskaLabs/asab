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

### Tabs

We use tabs as an indentation method. Do not mix them with spaces!

### Blank lines

Surround top-level function and class definitions with two blank lines.

Method definitions inside a class are surrounded by a single blank line.

Extra blank lines may be used (sparingly) to separate groups of related functions. Blank lines may be omitted between a bunch of related one-liners (e.g. a set of dummy implementations).

Use blank lines in functions, sparingly, to indicate logical sections.

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

### Docstrings formatting

In order for the automatic documentation to be generated without errors, [Google style docstring guide](https://google.github.io/styleguide/pyguide.html#38-comments-and-docstrings) must be followed. Here is an example of the properly documented function:

```python
def fetch_smalltable_rows(
    table_handle: smalltable.Table,
    keys: Sequence[bytes | str],
    require_all_keys: bool = False,
) -> Mapping[bytes, tuple[str, ...]]:
    """Fetches rows from a Smalltable.

    Retrieves rows pertaining to the given keys from the Table instance
    represented by table_handle.  String keys will be UTF-8 encoded.

    Args:
      table_handle:
        An open smalltable.Table instance.
      keys:
        A sequence of strings representing the key of each table row to
        fetch.  String keys will be UTF-8 encoded.
      require_all_keys:
        If True only rows with values set for all keys will be returned.

    Returns:
      A dict mapping keys to the corresponding table row data
      fetched. Each row is represented as a tuple of strings. For
      example:

      {b'Serak': ('Rigel VII', 'Preparer'),
       b'Zim': ('Irk', 'Invader'),
       b'Lrrr': ('Omicron Persei 8', 'Emperor')}

      Returned keys are always bytes.  If a key from the keys argument is
      missing from the dictionary, then that row was not found in the
      table (and require_all_keys must have been False).

    Raises:
      IOError: An error occurred accessing the smalltable.
    """
```


!!! tip
    If you use code annotations, it will be automatically incorporated into the documentation. In case you for some reason do not want to use them and still would like to have type hints in documentation, you can manually add them like this:

    ```python
    def sum_of_squares(a, b):
        """
        Return sum of squares a^2 + b^2.

        Args:
            a (float | int): first number
            b (float | int): second number
        
        Returns:
            float or int representing the sum of squares.
        """

    ``` 

