"""Assemble the reveal.js deck from the report chapters.

The deck is not a separate document. Every content slide is a
`<div class="deck-slide">` block living in the report chapter it belongs to,
so a slide and the prose it summarises cannot drift apart -- which is what
went wrong with the Google Slides deck this replaces.

Three stages:

1. `docs/deck-slides.lua` runs over the chapters and writes one markdown file
   per slide into `build/deck/`, named by the div's `id`.
2. `docs/deck/manifest.txt` puts them in presentation order and interleaves the
   deck-only slides -- title, agenda, questions -- which have no chapter home
   and are hand-written under `docs/deck/`.
3. pandoc's revealjs writer turns the concatenation into one HTML file,
   pointed at a version-pinned reveal.js on jsDelivr.

Stage 2 is why this is a script rather than a make recipe: resolving each
manifest entry against two directories, and failing loudly when a slide exists
but is unlisted, is awkward in make and obvious here. Like the other scripts
here, it knows the repository's layout and is not shipped in the wheel.
"""

from __future__ import annotations

import argparse
import os
import os.path
import subprocess
import sys
from pathlib import Path
from typing import List, Sequence

REPO_ROOT = Path(__file__).resolve().parents[1]

DEFAULT_MANIFEST = REPO_ROOT / "docs" / "deck" / "manifest.txt"
DEFAULT_SLIDES_DIR = REPO_ROOT / "build" / "deck"
DEFAULT_OUT = REPO_ROOT / "build" / "html" / "deck.html"
#: reveal.js is loaded from a CDN rather than vendored. Pinned by version, so
#: the deck cannot shift underneath a rehearsal. Pass a directory to
#: `--reveal` to use a local copy instead -- `make vendor-reveal` fetches one.
REVEAL_VERSION = "5.1.0"
DEFAULT_REVEAL = f"https://cdn.jsdelivr.net/npm/reveal.js@{REVEAL_VERSION}"

EXTRACT_FILTER = REPO_ROOT / "docs" / "deck-slides.lua"
DECK_CSS = REPO_ROOT / "docs" / "templates" / "deck.css"


def read_manifest(path: Path) -> List[str]:
    """Return the slide names in presentation order.

    Blank lines and `#` comments are ignored, so the manifest can carry notes
    about why a slide sits where it does.

    Args:
        path: The manifest file.

    Returns:
        Slide names, in order.

    Raises:
        SystemExit: If the manifest lists a name twice.
    """
    names: List[str] = []
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.split("#", 1)[0].strip()
        if not line:
            continue
        if line in names:
            sys.exit(f"{path}: '{line}' is listed twice")
        names.append(line)
    return names


def extract_slides(chapters: Sequence[Path], slides_dir: Path) -> None:
    """Write one markdown file per chapter slide into `slides_dir`.

    Args:
        chapters: The report chapters, in document order.
        slides_dir: Directory the filter writes into. Cleared first, so a
            renamed slide does not leave its old file behind to be picked up
            by a stale manifest entry.
    """
    slides_dir.mkdir(parents=True, exist_ok=True)
    for stale in slides_dir.glob("*.md"):
        stale.unlink()
    subprocess.run(
        [
            "pandoc",
            *[str(chapter) for chapter in chapters],
            "-t",
            "markdown",
            f"--lua-filter={EXTRACT_FILTER}",
            "-o",
            "/dev/null",
        ],
        check=True,
        env={**os.environ, "DECK_SLIDES_DIR": str(slides_dir)},
    )


def resolve(name: str, slides_dir: Path, deck_dir: Path) -> Path:
    """Find the markdown for one manifest entry.

    A hand-written deck-only slide under `docs/deck/` wins over an extracted
    one, so a chapter slide can be overridden by name without editing the
    build.

    Args:
        name: The slide name from the manifest.
        slides_dir: Where extracted chapter slides were written.
        deck_dir: Where hand-written deck-only slides live.

    Returns:
        Path to the slide's markdown.

    Raises:
        SystemExit: If neither directory has it.
    """
    for candidate in (deck_dir / f"{name}.md", slides_dir / f"{name}.md"):
        if candidate.exists():
            return candidate
    sys.exit(
        f"manifest lists '{name}' but neither {deck_dir}/{name}.md nor "
        f"{slides_dir}/{name}.md exists"
    )


def check_nothing_orphaned(names: Sequence[str], slides_dir: Path) -> None:
    """Fail if a chapter carries a slide the manifest does not list.

    Authoring a slide and forgetting the manifest would drop it from the deck
    silently, which is the same failure mode as a missing blank line around the
    wrapper div. Both are worth an error rather than a quiet omission.

    Args:
        names: The manifest's slide names.
        slides_dir: Where extracted chapter slides were written.

    Raises:
        SystemExit: If an extracted slide is unlisted.
    """
    extracted = {path.stem for path in slides_dir.glob("*.md")}
    orphaned = sorted(extracted - set(names))
    if orphaned:
        sys.exit(
            "these chapter slides are not in the manifest, so they would be "
            "left out of the deck: " + ", ".join(orphaned)
        )


def assemble(paths: Sequence[Path], out: Path) -> Path:
    """Concatenate the slides into one markdown file.

    Args:
        paths: Slide markdown files, in presentation order.
        out: Where to write the combined markdown.

    Returns:
        The path written.
    """
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(
        "\n\n".join(path.read_text(encoding="utf-8").strip() for path in paths) + "\n",
        encoding="utf-8",
    )
    return out


def resolve_reveal(reveal: str, out: Path) -> str:
    """Return the value pandoc should use for `revealjs-url`.

    A URL is passed through. A local directory is written *relative* to the
    output file rather than absolute, so a `deck.html` built here still works
    after the tree is copied onto a presentation machine.

    Args:
        reveal: A CDN base URL, or a path to a reveal.js checkout.
        out: Where the HTML will be written.

    Returns:
        The URL or relative path to hand pandoc.

    Raises:
        SystemExit: If a local path was given and does not hold reveal.js.
    """
    if reveal.startswith(("http://", "https://")):
        return reveal.rstrip("/")
    directory = Path(reveal)
    if not (directory / "dist" / "reveal.js").exists():
        sys.exit(
            f"no reveal.js at {directory} -- run `make vendor-reveal`, or drop "
            "the --reveal argument to load it from the CDN"
        )
    return os.path.relpath(directory, out.parent)


def render(deck_md: Path, out: Path, reveal: str) -> None:
    """Run pandoc's revealjs writer over the assembled markdown.

    Args:
        deck_md: The assembled slide markdown.
        out: Where to write the HTML.
        reveal: A CDN base URL, or a path to a reveal.js checkout.
    """
    out.parent.mkdir(parents=True, exist_ok=True)
    reveal_url = resolve_reveal(reveal, out)
    subprocess.run(
        [
            "pandoc",
            str(deck_md),
            "-o",
            str(out),
            "-t",
            "revealjs",
            "--standalone",
            "--slide-level=2",
            f"--resource-path={REPO_ROOT}:{REPO_ROOT / 'docs'}",
            "-V",
            f"revealjs-url={reveal_url}",
            "-V",
            "theme=black",
            # Slides are top-aligned: reveal centres vertically by default,
            # which floats each title to a different height depending on how
            # much body text follows it.
            "-V",
            "center=false",
            "-V",
            "width=1280",
            "-V",
            "height=720",
            "-V",
            "margin=0.06",
            "-V",
            "controls=true",
            "-V",
            "progress=true",
            "-V",
            "hash=true",
            f"--css={os.path.relpath(DECK_CSS, out.parent)}",
        ],
        check=True,
    )


def main(argv: Sequence[str] | None = None) -> int:
    """Build the deck.

    Args:
        argv: Command-line arguments, or `None` to read `sys.argv`.

    Returns:
        Process exit status.
    """
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("chapters", nargs="+", type=Path, help="report chapters, in order")
    parser.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    parser.add_argument("--slides-dir", type=Path, default=DEFAULT_SLIDES_DIR)
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT)
    parser.add_argument("--reveal", default=DEFAULT_REVEAL)
    args = parser.parse_args(argv)

    names = read_manifest(args.manifest)
    extract_slides(args.chapters, args.slides_dir)
    check_nothing_orphaned(names, args.slides_dir)
    paths = [resolve(name, args.slides_dir, args.manifest.parent) for name in names]
    deck_md = assemble(paths, args.slides_dir / "deck.md")
    render(deck_md, args.out, args.reveal)
    print(f"{args.out} ({len(paths)} slides)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
