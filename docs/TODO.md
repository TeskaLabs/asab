# TODOs

- Create a Dockerfile
- Experiment with search boosting: https://squidfunk.github.io/mkdocs-material/setup/setting-up-site-search/#search-boosting
- Override the CSS for 'h2.doc-heading' so that we can use different heading level and improve the design

## Missing sections

- PubSub
- AlertService
- ProactorService
- SSL/TLS
- Authorization and multitenancy
- CORS
- Metrics (needs to be modified)
- Zookeeper

- Containerisation (needs to be modified)
- Systemd


## Useful hyperlinks:

https://squidfunk.github.io/mkdocs-material/reference/code-blocks/

https://realpython.com/python-project-documentation-with-mkdocs/#step-1-set-up-your-environment-for-building-documentation

https://diataxis.fr/

https://google.github.io/styleguide/pyguide.html#38-comments-and-docstrings

## Converting docstrings

- Script for converting docstrings from one format to another: https://github.com/dadadel/pyment

1. Install via pip:
```
pip install git+https://github.com/dadadel/pyment.git
```

2. This command creates a patch:
```
pyment path/to/file.py -o google
```
3. Rewrite the patches:
```
patch path/to/file.py path/to/file.py.patch
```



