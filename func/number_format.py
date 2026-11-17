"""
One way of writing numbers on screen, whatever the language of the generated data (user decision: Polish notation
everywhere): a no-break space between thousands and a decimal comma.

    1 234,56   6,6M   33,4%

Used for headline numbers, the table preview, chart titles, labels, axes and tooltips and input fields. The no-break
space keeps a number on one line. The k and M suffixes stay short. Downloaded files keep the machine format
(CSV: no grouping, decimal dot; see func/export.py).
"""

THOUSANDS = " "  # no-break space
DECIMAL = ","


def number(value, decimals=0):
    """1234.5 -> '1 234,50' with decimals=2."""
    text = f"{value:,.{decimals}f}"
    return text.replace(",", "\0").replace(".", DECIMAL).replace("\0", THOUSANDS)


def percent(share, decimals=0):
    """0.334 -> '33%', with decimals=1 '33,4%'."""
    return f"{number(share * 100, decimals)}%"


def compact(value):
    """6_600_000 -> '6,6M', 672_100 -> '672,1k'; below a thousand a plain number."""
    for limit, suffix in ((1e9, "B"), (1e6, "M"), (1e3, "k")):
        if abs(value) >= limit:
            return f"{number(value / limit, 1)}{suffix}"
    return number(value, 0)


# Plotly layout.separators: the decimal mark first, then the thousands mark.
PLOTLY_SEPARATORS = DECIMAL + THOUSANDS
