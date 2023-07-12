"""Utility script for transferring sphinx docs into yaml files."""

import pathlib
import os

old_files = pathlib.Path.cwd() / "old_docs" / "web"

for old_file_rst in old_files.iterdir():
    print(old_file_rst.stem)
    new_file_md = pathlib.Path.cwd() / "docs" / "tutorial" / f"{old_file_rst.stem}.md"
    print(new_file_md)

    command = f"pandoc -f rst -t markdown {old_file_rst} -o {new_file_md}"

    os.system(command)
