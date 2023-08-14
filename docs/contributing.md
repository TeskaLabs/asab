# Contributing

We appreciate your effort to help us improve ASAB. In case you are interested in contributing, please follow the rules and conventions that we describe below.


## Coding conventions

At TeskaLabs, we follow the [PEP8 Style Guide](https://www.python.org/dev/peps/pep-0008/), which provides guidelines and
best practices on writing Python code for improved readability and consistency.

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

These are the parts of the PEP8 Style Guide we care about the most:

### Tabs

We use tabs as an indentation method. Do not mix them with spaces!

### Blank lines

Surround top-level function and class definitions with two blank lines.

Surround method definitions inside a class with a single blank line.

You may use extra blank lines (sparingly) to separate groups of related functions. You can omit blank lines between a bunch of related one-liners (e.g. a set of dummy implementations).

Use blank lines in functions, sparingly, to indicate logical sections.

### Imports

Write imports one-per-line style as per the example:

```python
import os
import sys
import logging
```

Also:

1. Use **relative imports** when you import locally from a package.
2. Use **absolute imports** when you import from external package.
3. Never use `from ... import ...` because it unnecessarily increases complexity for readers
(unless you have very good reason for that). The only exception is `__init__.py` where it is
used for importing symbols that you want to expose as a given module public API.

## Documentation conventions

We use [Material for MkDocs](https://squidfunk.github.io/mkdocs-material/) as our documentation engine. To learn about features, visit the [reference page](https://squidfunk.github.io/mkdocs-material/reference/).

MkDocs uses Markdown for writing documentation.

### Docstrings formatting

In order for the automatic documentation to be generated without errors, [Google style docstring guide](https://google.github.io/styleguide/pyguide.html#38-comments-and-docstrings) must be followed. Here is an example of a properly documented function:

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
    Code annotations will be automatically incorporated into the documentation. If you don't want to use code annotations and would still like to have type hints in documentation, you can manually add them like this:

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

