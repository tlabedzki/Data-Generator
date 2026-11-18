"""
How numbers are written on screen. The app uses Polish notation everywhere, whatever the language of the generated
data (user decision): a no-break space between thousands and a decimal comma.

    Polish (app):     1 234,56   6,6M   33,4%
    English (README): 1,234.56   6.6M   33.4%

The README images are in English like the README text, so scripts/make_charts.py draws them inside
`with notation("en"):`. Used for headline numbers, the table preview, chart titles, labels, axes and tooltips and
input fields. The no-break space keeps a number on one line. Downloaded files keep the machine format (CSV: no
grouping, decimal dot; see func/export.py).
"""
from contextlib import contextmanager

NOTATIONS = {"pl": (" ", ","), "en": (",", ".")}  # (thousands, decimal)

THOUSANDS, DECIMAL = NOTATIONS["pl"]  # the app's input fields
_active = ["pl"]


@contextmanager
def notation(name):
    """Temporarily write numbers in another notation (used for the English README images)."""
    if name not in NOTATIONS:
        raise ValueError(f"Unknown notation: {name}. Use one of {sorted(NOTATIONS)}.")
    _active.append(name)
    try:
        yield
    finally:
        _active.pop()


def set_default_notation(name):
    """Notation of the whole process (DG_NOTATION=en is only for recording English README images of the app)."""
    if name not in NOTATIONS:
        raise ValueError(f"Unknown notation: {name}. Use one of {sorted(NOTATIONS)}.")
    _active[0] = name


def _marks():
    return NOTATIONS[_active[-1]]


def thousands_mark():
    return _marks()[0]


def decimal_mark():
    return _marks()[1]


def number(value, decimals=0):
    """1234.5 -> '1 234,50' (app) or '1,234.50' (README) with decimals=2."""
    thousands, decimal = _marks()
    text = f"{value:,.{decimals}f}"
    return text.replace(",", "\0").replace(".", decimal).replace("\0", thousands)


def percent(share, decimals=0):
    """0.334 -> '33%', with decimals=1 '33,4%' (app) or '33.4%' (README)."""
    return f"{number(share * 100, decimals)}%"


def compact(value):
    """6_600_000 -> '6,6M' (app) or '6.6M' (README); below a thousand a plain number."""
    for limit, suffix in ((1e9, "B"), (1e6, "M"), (1e3, "k")):
        if abs(value) >= limit:
            return f"{number(value / limit, 1)}{suffix}"
    return number(value, 0)


def plotly_separators():
    """Plotly layout.separators for the active notation: the decimal mark first, then the thousands mark."""
    thousands, decimal = _marks()
    return decimal + thousands


PLOTLY_SEPARATORS = DECIMAL + THOUSANDS  # the app's notation
