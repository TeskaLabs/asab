"""This script iterates over .py files in examples directory and converts them into .md files into docs/examples."""

import pathlib
import yaml
import datetime
import re
import subprocess

EXAMPLE_DIR = pathlib.Path.cwd() / "examples"
DOCS_DIR = pathlib.Path.cwd() / "docs" / "examples"
MKDOCS_FILE = pathlib.Path.cwd() / "mkdocs.yml"


def process_examples(path_from, path_to):
	"""Find all the python files in 'path_from'.
	For each file, check if the corresponding .md file exist in 'path_to'
	or if it was modified (has a different commit hash).
	If so, create a new md file and append its reference to the 'nav' section in 'mkdocs.yml' file.
"""
	for py_file in EXAMPLE_DIR.glob("*.py"):
		# Check if the example is referenced in docs
		md_file = DOCS_DIR / py_file.with_suffix(".md").name
		if not md_file.exists() or git_metadata(py_file) != load_headers(md_file):
			create_markdown(py_file, md_file)
			add_to_navbar(md_file, MKDOCS_FILE)


def load_headers(md_file: pathlib.Path):
	_, headers, *content = md_file.read_text().split("---")
	assert content, "{} does not have 'headers' section defined.".format(md_file)
	return yaml.safe_load(headers)


def git_metadata(py_file: pathlib.Path) -> dict:
	git_format = "%aN|%ad|%H"
	last_git_commit = subprocess.check_output(["git", "log", "-n", "1", "--format={}".format(git_format), "--", py_file]).decode('utf-8').strip("\n").split("|")
	date_format = '%a %b %d %H:%M:%S %Y %z'
	metadata = {
		"author": last_git_commit[0],
		"date": datetime.datetime.strptime(last_git_commit[1], date_format),
		"commit": last_git_commit[2],
		"title": py_file.stem.replace("_", " ").replace("-", " ").capitalize()
	}
	return metadata


def create_markdown(py_file: pathlib.Path, md_file: pathlib.Path):
	text = """---
{headers}
---

!!! example

	```python title={py_file_name} linenums="1"
	{py_file_content}
	```
""".format(
		headers=yaml.safe_dump(git_metadata(py_file)),
		py_file_name=py_file.name,
		py_file_content=py_file.read_text().replace("\n", "\n\t")
	)
	md_file.write_text(text)


def add_to_navbar(md_file: pathlib.Path, mkdocs_file: pathlib.Path):

	with open(mkdocs_file, "+at", encoding="utf-8") as f:
		content = f.read()
		if md_file.name not in content:
			print(md_file.name, "not in", mkdocs_file.name)
			nav_reference = "    - examples/{}\n".format(md_file.name)
			f.write(nav_reference)


def main():
	process_examples(EXAMPLE_DIR, DOCS_DIR)


if __name__ == '__main__':
	main()
