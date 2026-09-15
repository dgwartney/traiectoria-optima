"""Every committed figure exists, in both variants, and every reference resolves.

Two failure modes, both of which have actually happened in this repository and
neither of which stops a build.

**A figure an experiment stopped writing.** Each experiment renders every chart
twice -- a dark version into `slides/images/` for the deck and a light one into
`docs/images/` for the report -- so that a chart and a slide agree. Nothing
checked that it happened, except for `route-map`.

**A figure a chapter references but nothing produces.** Pandoc treats a missing
image as a *warning*: the build exits 0 and the PDF is simply missing its
figure. That is how the four hand-drawn diagrams in Appendix C stayed absent
from the report for weeks -- `pdfimages -list` on the old build returned the
header row and nothing else. The second half of this file is the guard against
a repeat, and it works from the markdown rather than from a list someone has to
remember to update.
"""

import re
from pathlib import Path
from typing import List, Tuple

import pytest

PNG_MAGIC = b"\x89PNG\r\n\x1a\n"

# A figure so small it is almost certainly a failed render rather than a chart.
MIN_PLAUSIBLE_BYTES = 2_048

# The paired figures, and which experiment writes each one. The deck gets the
# dark variant under its bare name; the report gets `-light`. `route-map` is
# the exception -- a map cannot follow a dark theme, because every basemap
# style that would is watermarked or 401s without an API key, so both
# directories get the same light PNG. See experiments/route-map/experiment.toml.
PAIRED_FIGURES: List[Tuple[str, str]] = [
    ("search-cost", "runtime"),
    ("search-cost", "nodes-expanded"),
    ("graph-stats", "degree-distribution"),
    ("graph-stats", "top-hubs"),
]

SAME_IN_BOTH_FIGURES: List[Tuple[str, str]] = [
    ("route-map", "route-map-hnl-bdl"),
    ("route-map", "route-map-syd-jfk"),
    # `us-route-map` is a map too, so it shares the same exception. It also
    # renders each still *once* and copies it, rather than rendering twice:
    # screenshot output is not byte-deterministic -- two renders of the same
    # map came out 25 bytes apart, because basemap tiles arrive and labels
    # settle on their own schedule -- and this list demands they be identical.
    ("us-route-map", "us-route-map-all"),
    ("us-route-map", "us-route-map-lower-48"),
    ("us-route-map", "us-route-map-structure"),
    ("us-route-map", "us-route-map-pacific"),
    ("us-route-map", "us-route-map-caribbean"),
]

# `![alt](path)` in a chapter or appendix.
IMAGE_REFERENCE = re.compile(r"!\[[^\]]*\]\(([^)\s]+)")


def assert_is_a_real_png(path: Path) -> None:
    """Fail unless the file exists and is a PNG with plausible contents.

    Args:
        path: File to check.
    """
    assert path.is_file(), f"{path} is missing"
    data = path.read_bytes()
    assert data[:8] == PNG_MAGIC, f"{path} is not a PNG"
    assert len(data) >= MIN_PLAUSIBLE_BYTES, (
        f"{path} is only {len(data)} bytes, which is a failed render rather "
        "than a chart"
    )


@pytest.mark.parametrize(
    ("slug", "stem"),
    PAIRED_FIGURES,
    ids=[f"{slug}:{stem}" for slug, stem in PAIRED_FIGURES],
)
class TestPairedFigures:
    """Charts rendered twice, once per theme."""

    def test_the_dark_variant_is_committed_for_the_deck(self, repo_root, slug, stem):
        assert_is_a_real_png(repo_root / "slides" / "images" / f"{stem}.png")

    def test_the_light_variant_is_committed_for_the_report(self, repo_root, slug, stem):
        assert_is_a_real_png(repo_root / "docs" / "images" / f"{stem}-light.png")

    def test_the_two_variants_are_not_the_same_image(self, repo_root, slug, stem):
        """A copy rather than a re-render would defeat the whole convention.

        The deck is a dark theme and the report is a white page; one file
        cannot serve both, and the way that goes wrong silently is somebody
        copying instead of re-rendering.
        """
        dark = (repo_root / "slides" / "images" / f"{stem}.png").read_bytes()
        light = (repo_root / "docs" / "images" / f"{stem}-light.png").read_bytes()

        assert dark != light, (
            f"{stem}.png and {stem}-light.png are byte-identical, so one of "
            "them was copied rather than rendered for its theme"
        )


@pytest.mark.parametrize(
    ("slug", "stem"),
    SAME_IN_BOTH_FIGURES,
    ids=[f"{slug}:{stem}" for slug, stem in SAME_IN_BOTH_FIGURES],
)
def test_route_maps_are_committed_to_both_directories(repo_root, slug, stem):
    """The one experiment whose figure is deliberately the same in both.

    Not a violation of the two-variant convention but an exception to it, and
    an exception with a reason: OpenStreetMap is the only tile style available
    without an API key and it is light, so the deck places the light map in a
    white card.
    """
    for directory in ("docs/images", "slides/images"):
        assert_is_a_real_png(repo_root / directory / f"{stem}.png")


def report_documents(repo_root: Path) -> List[Path]:
    """Return every chapter and appendix of the report.

    Args:
        repo_root: Repository root.

    Returns:
        Sorted markdown paths.
    """
    return sorted((repo_root / "docs" / "report").glob("[0-9][0-9]-*.md"))


def test_there_are_report_documents_to_check(repo_root):
    """Guard against the sweep below passing because it found nothing."""
    assert len(report_documents(repo_root)) >= 12


def test_every_figure_the_report_references_exists(repo_root):
    """The guard against a silently figure-less PDF.

    Derived from the markdown rather than from a hand-maintained list, so a
    chapter that starts referencing a new figure is covered without anyone
    remembering to add it here.
    """
    missing = []
    for document in report_documents(repo_root):
        text = document.read_text(encoding="utf-8")
        for match in IMAGE_REFERENCE.finditer(text):
            target = match.group(1)
            if target.startswith(("http://", "https://")):
                continue
            resolved = (document.parent / target).resolve()
            if not resolved.exists():
                line = text[: match.start()].count("\n") + 1
                missing.append(f"{document.name}:{line} -> {target}")

    assert not missing, (
        "these figures are referenced by the report but do not exist. Pandoc "
        "would warn and still exit 0, so the PDF would build without them:\n"
        + "\n".join(missing)
    )


def test_the_report_references_at_least_one_figure_per_visual_chapter(repo_root):
    """A chapter that lost its figures would otherwise pass the sweep above.

    §2.5 and §7 are the two chapters whose arguments are carried by charts,
    and §3 by the class diagram. If a reference is deleted rather than broken,
    nothing above notices.
    """
    expected = {
        "02-dataset.md": 2,
        "03-graph-construction.md": 1,
        "07-empirical-evaluation.md": 2,
    }
    for name, least in expected.items():
        document = repo_root / "docs" / "report" / name
        found = len(IMAGE_REFERENCE.findall(document.read_text(encoding="utf-8")))
        assert found >= least, (
            f"{name} references {found} figures, expected at least {least}"
        )
