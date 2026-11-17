"""
Visual tokens of the app: a minimal white page with a cinematic teal and orange pair.

Teal carries the data, copper (orange) marks the one thing to notice, neutral greys hold everything else. Both ramps
are stepped in OKLCH (teal hue 207, copper hue 50) so each shade keeps the same character from light to dark.
"""

from dataclasses import dataclass

TEAL = ["#ebf8fa", "#d3eef1", "#addbe1", "#84c4cd", "#59aab4", "#34929e", "#14808c", "#006e79", "#005861", "#00434b"]
COPPER = ["#fff2eb", "#fce2d4", "#f8c9af", "#f0ac86", "#e79363", "#d97d45", "#c7692c", "#aa5823", "#88461c", "#6b3818"]

PRIMARY = TEAL[7]          # data, buttons, links
ACCENT = COPPER[6]         # the single highlighted point of each chart, step numbers
MIST = "#c3d5d8"           # recessive data marks (bars that are not the highlight)
AREA = "rgba(0, 110, 121, 0.07)"

PAGE = "#ffffff"
INK = "#14232a"            # primary text
TEXT = "#4a585e"           # secondary text
MUTED = "#808b90"          # captions, axis labels
LINE = "#e5e9ea"           # hairlines and the chart grid
WASH = "#f5f7f7"           # table header, hover

SANS = "Instrument Sans"
SERIF = "Instrument Serif"
SANS_STACK = f"'{SANS}', 'Segoe UI', system-ui, sans-serif"
SERIF_STACK = f"'{SERIF}', Georgia, serif"


@dataclass(frozen=True)
class FontPair:
    """Typeface of the headings (page title, step titles) and of the numbers (tables, stats, axes, inputs)."""

    name: str
    head: str
    num: str
    head_weight: int = 400
    head_stretch: str = "100%"
    head_tracking: str = "-0.015em"
    head_scale: float = 1.0      # optical size correction, wide faces need a smaller size
    head_em: str = "italic"      # style of the emphasized word in the title
    num_features: str = "'tnum' 1"
    num_scale: float = 1.0       # mono faces look larger at the same size


FONT_PAIRS = {
    "instrument": FontPair("Build 1: Instrument Serif + Instrument Sans", SERIF, SANS),
    "a": FontPair("A Kino: Archivo Expanded + Barlow", "Archivo", "Barlow", head_weight=600, head_stretch="125%",
                  head_tracking="-0.025em", head_scale=0.74, head_em="normal"),
    "b": FontPair("B Redakcja: Newsreader + DM Mono", "Newsreader", "DM Mono", head_weight=400,
                  head_tracking="-0.025em", head_scale=0.9, num_scale=0.92),
    "c": FontPair("C Grotesk: Bricolage Grotesque + Inter", "Bricolage Grotesque", "Inter", head_weight=600,
                  head_tracking="-0.04em", head_scale=0.84, head_em="normal", num_features="'tnum' 1, 'cv11' 1"),
    "d": FontPair("D Plakat: Playfair Display + Space Mono", "Playfair Display", "Space Mono", head_weight=500,
                  head_tracking="-0.02em", head_scale=0.84, num_scale=0.88),
}
DEFAULT_FONTS = "instrument"


def font_pair(key):
    return FONT_PAIRS.get(key or "", FONT_PAIRS[DEFAULT_FONTS])


def font_vars(pair):
    """CSS custom properties that switch the heading and number faces of the whole page."""
    return {
        "--dg-head": f"'{pair.head}', Georgia, serif",
        "--dg-head-weight": str(pair.head_weight),
        "--dg-head-stretch": pair.head_stretch,
        "--dg-head-tracking": pair.head_tracking,
        "--dg-head-scale": str(pair.head_scale),
        "--dg-head-em": pair.head_em,
        "--dg-num": f"'{pair.num}', {SANS_STACK}",
        "--dg-num-features": pair.num_features,
        "--dg-num-scale": str(pair.num_scale),
    }


MANTINE_THEME = {
    "fontFamily": SANS_STACK,
    "fontFamilyMonospace": "ui-monospace, 'Cascadia Mono', Consolas, monospace",
    "headings": {"fontFamily": SERIF_STACK, "fontWeight": "400"},
    "primaryColor": "petrol",
    "primaryShade": 7,
    "colors": {"petrol": TEAL, "copper": COPPER},
    "black": INK,
    "defaultRadius": "sm",
    "fontSizes": {"xs": "12px", "sm": "14px", "md": "15px", "lg": "17px", "xl": "20px"},
}
