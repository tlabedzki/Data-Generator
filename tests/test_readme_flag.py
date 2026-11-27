"""README language switch: a flag at the end of the badge paragraph links to the README in the other language."""
import re
import xml.etree.ElementTree as ET
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SVG = "{http://www.w3.org/2000/svg}"
FLAGS = {  # README file: (flag image, alt and title, link target)
    "README.md": ("docs/img/flag-pl.svg", "Polski", "READMEPL.md"),
    "READMEPL.md": ("docs/img/flag-gb.svg", "English", "README.md"),
}
OLD_LINKS = ("**English** | [Polski](READMEPL.md)", "[English](README.md) | **Polski**")


def badge_paragraph(text: str) -> list[str]:
    """Lines of the first paragraph with a shields.io badge."""
    for block in re.split(r"\n[ \t]*\n", text):
        if "img.shields.io" in block:
            return block.strip().splitlines()
    raise AssertionError("no badge paragraph")


@pytest.mark.parametrize("readme", FLAGS)
def test_flag_ends_the_badge_paragraph(readme):
    image, label, target = FLAGS[readme]
    text = (ROOT / readme).read_text(encoding="utf-8")
    assert badge_paragraph(text)[-1] == f'[![{label}]({image} "{label}")]({target})'
    assert text.count(image) == 1
    assert not any(old in text for old in OLD_LINKS)


@pytest.mark.parametrize("readme", FLAGS)
def test_flag_svg_is_a_badge_high_image_with_a_title(readme):
    image, label, _ = FLAGS[readme]
    svg = ET.parse(ROOT / image).getroot()
    assert svg.tag == f"{SVG}svg" and svg.get("height") == "20"
    assert svg.find(f"{SVG}title").text == label
