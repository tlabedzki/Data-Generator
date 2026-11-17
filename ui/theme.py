"""
Visual tokens of the app: a minimal white page with a cinematic teal and orange pair.

Teal carries the data, copper (orange) marks the one thing to notice, neutral greys hold everything else. Both ramps
are stepped in OKLCH (teal hue 207, copper hue 50) so each shade keeps the same character from light to dark.
"""

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

SANS = "Instrument Sans"            # running text and interface
HEAD = "Bricolage Grotesque"        # page title and step titles (user choice «2c», build 2 variant C)
NUM = "Inter"                       # numbers: tables, stats, chart axes and labels, inputs (tabular figures)
SANS_STACK = f"'{SANS}', 'Segoe UI', system-ui, sans-serif"
HEAD_STACK = f"'{HEAD}', {SANS_STACK}"
NUM_STACK = f"'{NUM}', {SANS_STACK}"

MANTINE_THEME = {
    "fontFamily": SANS_STACK,
    "fontFamilyMonospace": "ui-monospace, 'Cascadia Mono', Consolas, monospace",
    "headings": {"fontFamily": HEAD_STACK, "fontWeight": "600"},
    "primaryColor": "petrol",
    "primaryShade": 7,
    "colors": {"petrol": TEAL, "copper": COPPER},
    "black": INK,
    "defaultRadius": "sm",
    "fontSizes": {"xs": "12px", "sm": "14px", "md": "15px", "lg": "17px", "xl": "20px"},
}
