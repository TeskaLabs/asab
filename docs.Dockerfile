FROM squidfunk/mkdocs-material
RUN pip3 install mkdocs-print-site-plugin \
mkdocs-awesome-pages-plugin \
mkdocs-glightbox \
mkdocs-autorefs \
mkdocs-diagrams \
mkdocs-git-revision-date-localized-plugin \
mkdocstrings \
mkdocstrings-python