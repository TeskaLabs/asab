# Contributing to ASAB

This document outlines some of the conventions for contributing to ASAB code.

Thank you for considering a contribution to ASAB!
Contributions are welcome — and to keep the project healthy and legally sound for everyone, all contributions are accepted under the terms below.


## Contribution terms

By submitting a contribution to this project — including but not limited to pull requests, patches, code, documentation, tests, examples, or issue content (each a "Contribution") — you accept and agree to the following terms for your present and future Contributions:

### 1. License of Contributions ("inbound = outbound")

All Contributions to this project are licensed under the same license as the project itself: the **BSD 3-Clause License** (see the [`LICENSE`](./LICENSE) file), **without any additional terms or conditions**.

There is no separate contributor license, no dual licensing of Contributions, and no side agreements.
What goes in is licensed exactly as what goes out.

### 2. Copyright license — perpetual and irrevocable

You grant to TeskaLabs Ltd and to all recipients of software distributed by this project a **perpetual, worldwide, non-exclusive, royalty-free, irrevocable copyright license** to use, reproduce, modify, prepare derivative works of, publicly display, publicly perform, sublicense, and distribute your Contribution and derivative works thereof, under the BSD 3-Clause License.

**This grant cannot be revoked.** Once a Contribution is submitted and merged into the project, you may not withdraw the license to it, demand its removal on licensing grounds, or impose new conditions on its use.
This protects every user and contributor who builds on the project.

### 3. Patent license

To the extent your Contribution is covered by any patents you own or control, you grant to TeskaLabs Ltd and to all recipients of software distributed by this project a **perpetual, worldwide, non-exclusive, royalty-free, irrevocable patent license** to make, have made, use, offer to sell, sell, import, and otherwise transfer your Contribution, alone or in combination with the project.

If you (or any entity on your behalf) institute patent litigation alleging that the project or a Contribution within it constitutes patent infringement, any patent licenses granted to you under this section terminate as of the date such litigation is filed.

### 4. Your representations

By submitting a Contribution, you represent that:

1. You are legally entitled to grant the above licenses. The Contribution is your original work, **or** you have sufficient rights to submit it under the project license.
2. If your employer has rights to intellectual property you create (which is common in employment contracts), you have received permission from your employer to submit the Contribution, or your employer has waived such rights.
3. If your Contribution includes third-party material, you have clearly identified it, including its source and license, and that license is compatible with the BSD 3-Clause License.
4. Your Contribution does not knowingly violate any third-party copyright, patent, trademark, or trade secret.

### 5. No obligation and no compensation

You understand that:

1. The maintainers are under no obligation to accept, merge, use, or retain any Contribution, and may modify or remove merged Contributions at their discretion.
2. Contributions are provided voluntarily. You are not entitled to any compensation, attribution beyond what the BSD 3-Clause License requires, or other consideration for your Contribution.
3. Except for the representations in section 4, Contributions are provided **"AS IS"**, without warranties of any kind.

*If you do not agree with these terms, please do not submit a Contribution.*


## Coding conventions

ASAB is a Python project.

### PEP8

We in TeskaLabs are following PEP8 Style Guide for Python Code.
[PEP8](https://www.python.org/dev/peps/pep-0008/) is a document that provides guidelines and
best practices on how to write Python code. The primary focus of PEP 8 is to improve the readability
and consistency of Python code.

### flake8

You can check if changes in your code are compliant with PEP8 by running following command

```bash
flake8 .
```

It is highly recommended to create a pre-commit hook (`.git/hooks/pre-commit`)

```
#!/bin/sh
echo "Running flake8 ..."
flake8 .
```

Hook must be executable (`chmod u+x .git/hooks/pre-commit`)

This hook is part of [TravisCI](https://travis-ci.com/TeskaLabs/asab/)

### Imports

Imports shall be writen one-per-line style as per the example below

```
import os
import sys
import logging
...
```

Following additional rules apply for imports:

1. Use relative imports when you import locally from a package
2. Use absolute imports when you import from external package
3. Never use `from ... import ...` because it unnecessarily increases complexity for readers
(unless you have very good reason for that). The only exception is `__init__.py` where it is
used for importing symbols that you want to expose as a given module public API

### Documenting functions, methods and classes

Functions, methods and classes should be documented using quotation marks, see the example below

```
def publish(self, event_name, *args, **kwargs):
	""" Notify subscribers of an event with arguments. """
	callback_set = self.subscribers.get(event_name)
	...
```

## Publishing to pypi.org

1. Create a version tag (`git tag -a v19.10`)
1. Push a tag to GitHub (`git push origin v19.10`)
1. Make local build (`python3 setup.py sdist bdist_wheel`)
1. Publish a package to pypi.org (`twine upload dist/*`)
