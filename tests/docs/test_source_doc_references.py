"""Paths to documents, cited from inside the source, must resolve.

`tests/docs/test_links.py` checks links between markdown files. Nothing
checked the other direction: a module docstring naming a document. That gap
let `viz/geodesic.py` keep pointing at the old `distance_formulas` document
for as long as it took the #72 review to read the file -- the document had moved into the
report as Appendix C and left nothing behind at the old path.

It matters more than an ordinary broken link because these docstrings **ship
in the wheel**, where `help(Geodesic)` is the documentation, and a reader
following the reference has no repository to search.
"""

import re
from pathlib import Path
from typing import List, Tuple

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]

SOURCE_DIRS = ("src", "scripts", "tests")

#: Any path into the documentation directory, mentioned in a source file.
DOC_PATH = re.compile(r"docs/[A-Za-z0-9_./-]*\.md")


def _source_files() -> List[Path]:
    return sorted(
        path
        for directory in SOURCE_DIRS
        for path in (REPO_ROOT / directory).rglob("*.py")
        if "__pycache__" not in path.parts
    )


def _references() -> List[Tuple[Path, int, str]]:
    found = []
    for path in _source_files():
        for number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
            for match in DOC_PATH.findall(line):
                found.append((path, number, match))
    return found


REFERENCES = _references()


def test_the_scan_finds_something() -> None:
    """A regex that matched nothing would make the test below vacuous."""
    assert REFERENCES, "no docs/*.md references found -- has the pattern rotted?"


@pytest.mark.parametrize(
    "path,line,reference",
    REFERENCES,
    ids=[f"{p.relative_to(REPO_ROOT)}:{n}" for p, n, _ in REFERENCES],
)
def test_every_document_cited_from_source_exists(
    path: Path, line: int, reference: str
) -> None:
    assert (REPO_ROOT / reference).is_file(), (
        f"{path.relative_to(REPO_ROOT)}:{line} cites {reference}, which does "
        "not exist. If the document moved into the report, cite it by its "
        "appendix letter instead of a path -- these docstrings ship in the "
        "wheel, where there is no repository to search."
    )
