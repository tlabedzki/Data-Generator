"""
Build docs/img/app-demo.svg and app-demo-dark.svg, the animated demo at the top of the README.

Usage (from the repository root, with requirements-dev.txt installed):
    python scripts/make_demo_svg.py [--shots DIR] [--reuse] [--quality 74]

The demo is an illustration, not a recording: three screenshots of the real app (fictional data: the parameters,
the preview with the charts, the month weights) and the preset cards before the click, in a browser frame, moved by
CSS animations. The script starts the app on 127.0.0.1 with English number notation, takes the
screenshots with headless Chrome or Edge (CDP) and stops the app. Then it embeds the screenshots as WebP and draws
the moving parts as vectors: the cursor, the clicks, the progress bar and the November point of the seasonality
chart, dragged up with its line and value. The story opens on the result: the key numbers of the generated shop and
the revenue chart, then November dragged up to reshape the season, then the parameters (pick Large, generate),
which lead back to the result. The loop ends on its first frame, so the seam does not jump.

Only CSS inside the SVG, no script: GitHub shows README images through <img>. With prefers-reduced-motion the image
shows the revenue chart without motion. The two files differ only in the browser frame (light and dark GitHub theme).
--shots keeps the screenshots and their geometry in DIR; --reuse builds from them without starting the app.
"""
import argparse
import asyncio
import base64
import io
import json
import math
import os
import subprocess
import sys
import tempfile
import time
import urllib.request
from pathlib import Path

import websockets
from fontTools import subset
from fontTools.ttLib import TTFont
from fontTools.varLib import instancer
from PIL import Image

PROJECT_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_DIR))
from ui import theme as t  # noqa: E402

OUT_DIR = PROJECT_DIR / "docs" / "img"
FONT = PROJECT_DIR / "ui" / "assets" / "fonts" / "inter-latin-wght-normal.woff2"
PORT = 9336  # DevTools
APP_PORT = 8765  # the app, away from the default 8050
VW, VH = 1040, 620  # browser viewport in CSS px
SCALE = 1.5  # screenshot pixels per CSS px
W = 1000  # SVG width in user units; the viewport is scaled by W / VW
BAR = 36  # browser bar above the page
LIMIT = 500 * 1024  # bytes per SVG
EASE = "cubic-bezier(.65,0,.35,1)"  # ease-in-out for glides and scrolls
EASE_OUT = "cubic-bezier(.22,1,.36,1)"
FRAMES = {  # browser frame in GitHub's light and dark theme; the app keeps its own white page
    "light": {"bar": "#f6f8fa", "border": "#d0d7de", "dot": "#d0d7de", "pill": "#ffffff", "pill_text": "#57606a"},
    "dark": {"bar": "#161b22", "border": "#30363d", "dot": "#484f58", "pill": "#0d1117", "pill_text": "#8b949e"},
}


def r4(value):
    """Round CSS px to a multiple of 4, a whole number of screenshot pixels at SCALE 1.25 or 1.5."""
    return int(round(value / 4) * 4)


# ---- 1. screenshots ----------------------------------------------------------------------------------------------

async def capture(browser, url, shots):
    """Screenshots of the app at SCALE with the geometry the animation needs, saved to shots/."""
    profile = tempfile.mkdtemp()
    proc = subprocess.Popen([browser, "--headless=new", "--disable-gpu", f"--remote-debugging-port={PORT}",
                             f"--user-data-dir={profile}", "--hide-scrollbars", "about:blank"],
                            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    geo = {"viewport": [VW, VH], "scale": SCALE}
    try:
        for _ in range(50):
            try:
                page = next(p for p in json.load(urllib.request.urlopen(f"http://127.0.0.1:{PORT}/json"))
                            if p["type"] == "page")
                break
            except Exception:
                time.sleep(0.2)
        ws = await websockets.connect(page["webSocketDebuggerUrl"], max_size=500 * 1024 * 1024)
        counter = 0

        async def send(method, **params):
            nonlocal counter
            counter += 1
            my_id = counter
            await ws.send(json.dumps({"id": my_id, "method": method, "params": params}))
            while True:
                message = json.loads(await ws.recv())
                if message.get("id") == my_id:
                    if "error" in message:
                        raise RuntimeError(f"{method}: {message['error']}")
                    return message.get("result", {})

        async def js(expression):
            result = await send("Runtime.evaluate", expression=expression, returnByValue=True)
            return result.get("result", {}).get("value")

        async def rect(selector):
            """Page rectangle (CSS px, scroll included) of the first element matching selector."""
            return await js(f"(() => {{ const r = document.querySelector({json.dumps(selector)})"
                            ".getBoundingClientRect();"
                            " return {x: r.left, y: r.top + scrollY, w: r.width, h: r.height}; })()")

        async def shot(name, x, y, w, h):
            data = (await send("Page.captureScreenshot", format="png", captureBeyondViewport=True,
                               clip={"x": x, "y": y, "width": w, "height": h, "scale": SCALE}))["data"]
            (shots / f"{name}.png").write_bytes(base64.b64decode(data))

        await send("Emulation.setDeviceMetricsOverride", width=VW, height=VH, deviceScaleFactor=1, mobile=False)
        await send("Page.enable")
        await send("Page.navigate", url=url)
        await asyncio.sleep(5)
        await js("document.documentElement.style.scrollBehavior = 'auto'")

        # Parameters: the preset cards with Medium (the patch that fades out on the click), then the page with Large
        top = r4((await rect("#parameters"))["y"] - 24)
        cards = await rect(".dg-presets")
        patch = [r4(cards["x"] - 8), r4(cards["y"] - 8)]
        patch += [r4(cards["x"] + cards["w"] + 8) - patch[0], r4(cards["y"] + cards["h"] + 8) - patch[1]]
        await shot("presets-medium", *patch)
        await js("[...document.querySelectorAll('.dg-preset')].find(b => b.textContent.startsWith('Large')).click()")
        await asyncio.sleep(0.8)
        large = await js("(() => { const b = [...document.querySelectorAll('.dg-preset')]"
                         ".find(b => b.textContent.startsWith('Large')).getBoundingClientRect();"
                         " return {x: b.left, y: b.top + scrollY, w: b.width, h: b.height}; })()")
        generate = await rect("#generate")
        progress = await rect("#progress")
        stop = r4(generate["y"] + generate["h"] / 2 - VH * 0.6 - top)  # Generate a little below the middle
        await shot("parameters", 0, top, VW, stop + VH)
        geo["parameters"] = {"top": top, "stop": stop, "patch": patch, "large": large, "generate": generate,
                             "progress": progress}

        preview_before = (await rect("#preview"))["y"]
        # Generate, wait for the charts: the preview and the first chart in one strip
        await js("document.getElementById('generate').click()")
        started = time.monotonic()
        while time.monotonic() - started < 90:
            if await js("document.querySelectorAll('#charts .js-plotly-plot').length >= 3"):
                break
            await asyncio.sleep(0.5)
        else:
            raise RuntimeError("The charts did not appear within 90 s.")
        await asyncio.sleep(2)
        preview = (await rect("#preview"))["y"]
        if abs(preview - preview_before) > 0.5:
            raise RuntimeError(f"The preview moved from {preview_before} to {preview}: the page would not line up.")
        top = r4(preview - 24)
        stop = r4((await rect("#charts"))["y"] - 24 - top)
        await shot("results", 0, top, VW, stop + VH)
        geo["results"] = {"top": top, "stop": stop}

        # Advanced: the month weights with November taken out of the chart (the SVG draws it as a vector)
        await js("[...document.querySelectorAll('.mantine-Accordion-control')]"
                 ".find(b => b.textContent.includes('Advanced')).click()")
        await asyncio.sleep(1.5)
        months = json.loads(await js("""(() => {
            const gd = document.querySelector('#weights-month-graph .js-plotly-plot');
            const L = gd._fullLayout, r = gd.getBoundingClientRect(), d = gd.data[0];
            const x0 = r.left + L._size.l, y0 = r.top + scrollY + L._size.t;
            const label = gd.querySelectorAll('.textpoint text')[10].getBoundingClientRect();
            return JSON.stringify({
                x: d.x.map((_, i) => x0 + L.xaxis.d2p(i)), y: d.y.map(v => y0 + L.yaxis.d2p(v)),
                values: d.y.map(Number), zero: y0 + L.yaxis.d2p(0), range: L.yaxis.range,
                ceiling: Math.min(gd.layout.meta.max, L.yaxis.range[1] * 0.88), step: gd.layout.meta.step,
                label_bottom: label.bottom + scrollY, label_height: label.height}); })()"""))
        top = r4(months["y"][10] - VH * 0.56)
        await js(f"window.scrollTo(0, {top})")
        await js("""(() => { const gd = document.querySelector('#weights-month-graph .js-plotly-plot');
            const y = gd.data[0].y.slice(), text = gd.data[0].text.slice();
            y[10] = null; text[10] = '';
            Plotly.restyle(gd, {y: [y], text: [text]}); })()""")
        await asyncio.sleep(0.8)
        await shot("weights", 0, top, VW, VH)
        geo["weights"] = {"top": top, **months}
    finally:
        proc.terminate()
    (shots / "geometry.json").write_text(json.dumps(geo, indent=1), encoding="utf-8")


def start_app():
    """Run the app in English notation and wait until it answers."""
    env = {**os.environ, "DG_NOTATION": "en", "DG_PORT": str(APP_PORT)}
    app = subprocess.Popen([sys.executable, "-m", "ui.app"], cwd=PROJECT_DIR, env=env,
                           stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    for _ in range(120):
        try:
            urllib.request.urlopen(f"http://127.0.0.1:{APP_PORT}", timeout=2)
            return app
        except OSError:
            time.sleep(0.5)
    stop_app(app)
    sys.exit(f"The app did not start on port {APP_PORT}.")


def stop_app(app):
    """Stop the app with its child processes (a venv python on Windows starts the real interpreter as a child)."""
    if os.name == "nt":
        subprocess.run(["taskkill", "/F", "/T", "/PID", str(app.pid)], capture_output=True)
    else:
        app.terminate()
    app.wait(timeout=10)


# ---- 2. animation ------------------------------------------------------------------------------------------------

class Motion:
    """CSS keyframes on one timeline. Each track: (seconds, value, easing to the next stop)."""

    def __init__(self, total, start=0.0):
        self.total = total
        self.start = start  # second of the timeline shown first: a negative delay starts every track there
        self.css = []
        self.count = 0

    def track(self, prop, stops, rest):
        """A class animating prop through stops; rest is the value without motion (prefers-reduced-motion)."""
        self.count += 1
        name = f"m{self.count}"
        stops = sorted(stops, key=lambda s: s[0])
        if stops[0][0] > 0:
            stops.insert(0, (0, stops[0][1], "linear"))
        if stops[-1][0] < self.total:
            stops.append((self.total, stops[-1][1], "linear"))
        frames = "".join(f"{s / self.total * 100:.3f}%{{{prop}:{value};animation-timing-function:{ease}}}"
                         for s, value, ease in stops)
        self.css.append(f"@keyframes {name}{{{frames}}}"
                        f".{name}{{{prop}:{rest};"
                        f"animation:{name} {self.total:g}s linear -{self.start:g}s infinite both}}")
        return name


def tr(x, y):
    return f"translate({x:.1f}px,{y:.1f}px)"


def ease_io(u):
    """The cubic ease-in-out of the drag, sampled in Python (keyframes in between are linear)."""
    return 4 * u ** 3 if u < 0.5 else 1 - (-2 * u + 2) ** 3 / 2


def font_face():
    """Inter at weight 400, digits and the decimal point only: the November value drawn in the SVG."""
    font = instancer.instantiateVariableFont(TTFont(FONT), {"wght": 400})
    options = subset.Options()
    options.layout_features = ["tnum"]
    options.flavor = "woff2"
    sub = subset.Subsetter(options)
    sub.populate(text="0123456789.,")
    sub.subset(font)
    buffer = io.BytesIO()
    font.flavor = "woff2"
    font.recalcTimestamp = False  # keep the source's date: two runs give the same bytes
    font.save(buffer)
    data = base64.b64encode(buffer.getvalue()).decode()
    return f"@font-face{{font-family:DgNum;src:url(data:font/woff2;base64,{data}) format('woff2')}}"


def webp(png, quality):
    buffer = io.BytesIO()
    Image.open(png).convert("RGB").save(buffer, "WEBP", quality=quality, method=6)
    return base64.b64encode(buffer.getvalue()).decode()


CURSOR = "M0 0V17.2L4.3 13.3L7.2 20.1L10.3 18.8L7.5 12.2H13.2Z"  # arrow, tip at 0,0


def build(shots, quality):
    """The light and dark SVG, as strings, from the screenshots and geometry in shots/."""
    geo = json.loads((shots / "geometry.json").read_text(encoding="utf-8"))
    if geo["viewport"] != [VW, VH] or geo["scale"] != SCALE:
        sys.exit("The screenshots were taken with another viewport or scale: run without --reuse.")
    k = W / VW
    vh = VH * k
    H = BAR + vh
    # Timeline in seconds. Scenes change by sliding like a page scroll: the preview lies below Generate, the
    # weights above it, and the loop slides back up to the parameters.
    slide = 0.9
    t_large, t_scroll, t_generate, t_results = 1.35, 1.9, 3.3, 4.6
    t_charts, t_weights = 7.6, 10.8
    t_grab, t_drag, drag_len, t_out = 12.45, 12.55, 1.3, 14.8
    t_release = t_drag + drag_len
    T = t_out + slide  # loop length
    # The loop is shown from the moment the preview is in place: the README opens on the result (key numbers, then
    # the revenue chart), then the weights, then the parameters and Generate, which lead back to the result.
    m = Motion(T, start=t_results + 1.35)
    images = {name: webp(shots / f"{name}.png", quality) for name in ("parameters", "presets-medium", "results",
                                                                      "weights")}
    size = {name: Image.open(shots / f"{name}.png").size for name in images}

    def image(name, x=0.0, y=0.0):
        w, h = size[name]
        return (f'<image x="{x:.2f}" y="{y:.2f}" width="{w / SCALE * k:.2f}" height="{h / SCALE * k:.2f}" '
                f'href="data:image/webp;base64,{images[name]}"/>')

    par, res, wei = geo["parameters"], geo["results"], geo["weights"]
    rest_cursor = (W * 0.6, vh * 0.86)  # where the loop starts and ends

    def scene(content, stops, rest):
        """A page in its own viewport clip; stops slide it in and out (user units, down is positive)."""
        cls = m.track("transform", [(s, tr(0, y), e) for s, y, e in stops], tr(0, rest))
        return f'<g class="{cls}"><g clip-path="url(#page)">{content}</g></g>'

    # Scene 1: one page from the parameters down to the charts. Click Large, glide down, click Generate; the
    # progress bar fills, the preview fills in below and the page glides on to the preview and the charts.
    large = ((par["large"]["x"] + par["large"]["w"] * 0.45) * k,
             (par["large"]["y"] + par["large"]["h"] * 0.55 - par["top"]) * k)
    generate = ((par["generate"]["x"] + par["generate"]["w"] * 0.55) * k,
                (par["generate"]["y"] + par["generate"]["h"] * 0.6 - par["top"] - par["stop"]) * k)
    at_generate = par["stop"] * k
    at_preview = (res["top"] - par["top"]) * k
    at_charts = at_preview + res["stop"] * k
    hidden = t_weights + slide + 0.05  # the page is out of view: reset it for the next loop
    scroll = m.track("transform", [(t_scroll, tr(0, 0), EASE), (t_scroll + 1.2, tr(0, -at_generate), "linear"),
                                   (t_results + 0.3, tr(0, -at_generate), EASE),
                                   (t_results + 1.3, tr(0, -at_preview), "linear"),
                                   (t_charts, tr(0, -at_preview), EASE), (t_charts + 1.2, tr(0, -at_charts), "linear"),
                                   (hidden, tr(0, -at_charts), "linear"), (hidden + 0.01, tr(0, 0), "linear")],
                     tr(0, -at_charts))
    patch_fade = m.track("opacity", [(t_large + 0.05, 1, EASE), (t_large + 0.35, 0, "linear"),
                                     (hidden, 0, "linear"), (hidden + 0.01, 1, "linear")], 0)
    results_fade = m.track("opacity", [(t_results, 0, EASE), (t_results + 0.35, 1, "linear"),
                                       (hidden, 1, "linear"), (hidden + 0.01, 0, "linear")], 1)
    px, py, _, _ = par["patch"]
    bar = par["progress"]
    bx, by, bw = bar["x"] * k, (bar["y"] - par["top"]) * k, bar["w"] * k
    bh = max(bar["h"], 3) * k
    progress_show = m.track("opacity", [(t_generate + 0.1, 0, "linear"), (t_generate + 0.25, 1, "linear"),
                                        (hidden, 1, "linear"), (hidden + 0.01, 0, "linear")], 0)
    progress_fill = m.track("transform", [(t_generate + 0.2, "scaleX(0)", "cubic-bezier(.3,.1,.3,1)"),
                                          (t_results - 0.1, "scaleX(1)", "linear"), (hidden, "scaleX(1)", "linear"),
                                          (hidden + 0.01, "scaleX(0)", "linear")], "scaleX(1)")
    progress = (f'<g class="{progress_show}"><rect x="{bx:.1f}" y="{by:.1f}" width="{bw:.1f}" height="{bh:.1f}" '
                f'rx="{bh / 2:.1f}" fill="#e5e9ea"/><g transform="translate({bx:.1f} {by:.1f})">'
                f'<rect class="{progress_fill}" width="{bw:.1f}" height="{bh:.1f}" rx="{bh / 2:.1f}" '
                f'fill="{t.PRIMARY}"/></g></g>')
    page = (f'<g class="{scroll}">{image("parameters")}'
            f'<g class="{patch_fade}">{image("presets-medium", px * k, (py - par["top"]) * k)}</g>{progress}'
            f'<g class="{results_fade}">{image("results", 0, at_preview)}</g></g>')
    # it leaves downwards when the weights come in from above and comes back from above at the end of the loop
    scene1 = scene(page, [(t_weights, 0, EASE), (t_weights + slide, vh, "linear"), (hidden, vh, "linear"),
                          (hidden + 0.01, -vh, "linear"), (t_out, -vh, EASE), (T, 0, "linear")], 0)

    # Scene 3: month weights, sliding down from above. The cursor grabs November and drags it up to the ceiling.
    xs = [x * k for x in wei["x"]]
    ys = [(y - wei["top"]) * k for y in wei["y"]]
    zero = (wei["zero"] - wei["top"]) * k
    step = wei["step"]
    v0 = wei["values"][10]
    v1 = math.floor(wei["ceiling"] / step + 1e-9) * step
    per_value = (ys[10] - zero) / v0 if v0 else (ys[9] - zero) / wei["values"][9]  # user units per weight
    lift = (v1 - v0) * per_value  # negative: up
    samples = 16
    us = [i / samples for i in range(samples + 1)]

    def drag_track(prop, at, rest_value):
        """A track that follows the drag: value at(e) for the eased share e of the lift, before, during and after."""
        return m.track(prop, [(t_drag + u * drag_len, at(ease_io(u)), "linear") for u in us], rest_value)

    nx, ny = xs[10], ys[10]
    point = drag_track("transform", lambda e: tr(0, lift * e), tr(0, lift))
    column_h = zero - ny
    column = drag_track("transform", lambda e: f"scaleY({(column_h - lift * e) / column_h:.4f})",
                        f"scaleY({(column_h - lift) / column_h:.4f})")

    def skew(x_from, y_from):
        """skewY that takes a horizontal line from (x_from, y_from) to November's x onto November's point."""
        return lambda e: f"skewY({math.degrees(math.atan2(ny + lift * e - y_from, nx - x_from)):.3f}deg)"

    left = drag_track("transform", skew(xs[9], ys[9]), skew(xs[9], ys[9])(1))
    right = drag_track("transform", skew(xs[11], ys[11]), skew(xs[11], ys[11])(1))
    marker_r = 6.5 * k
    label_y = (wei["label_bottom"] - wei["top"] - 0.24 * 11) * k  # baseline of the value above the point
    values = [round(v0 + i * step, 6) for i in range(round((v1 - v0) / step) + 1)]
    labels = []
    for i, value in enumerate(values):
        # visible while the dragged value rounds to it (the share e crosses half a step at each boundary)
        def at_share(share):
            lo, hi = 0.0, 1.0
            for _ in range(40):
                mid = (lo + hi) / 2
                lo, hi = (mid, hi) if ease_io(mid) < share else (lo, mid)
            return t_drag + (lo + hi) / 2 * drag_len
        n = len(values) - 1
        on = t_weights if i == 0 else at_share((i - 0.5) / n)
        off = T if i == n else at_share((i + 0.5) / n)
        stops = [(0, 0, "linear"), (on, 0, "linear"), (on + 0.001, 1, "linear"), (off, 1, "linear"),
                 (off + 0.001, 0, "linear")][:3 if i == n else 5]
        if i == 0:
            stops = [(0, 1, "linear"), (off, 1, "linear"), (off + 0.001, 0, "linear")]
        cls = m.track("opacity", stops, 1 if i == n else 0)
        labels.append(f'<text class="{cls}" x="{nx:.1f}" y="{label_y:.1f}">{value:.2f}</text>')
    line = f'stroke="{t.MIST}" stroke-width="1.5" vector-effect="non-scaling-stroke"'
    dot = f'r="{marker_r:.2f}" fill="{t.PRIMARY}" stroke="#ffffff" stroke-width="{2 * k:.2f}"'
    page3 = (f'{image("weights")}'
              f'<g transform="translate({nx:.1f} {zero:.1f})"><rect class="{column}" x="{-17 * k:.1f}" '
              f'y="{-column_h:.1f}" width="{34 * k:.1f}" height="{column_h:.1f}" rx="{4 * k:.1f}" '
              f'fill="{t.PRIMARY}" fill-opacity="0.09"/></g>'
              f'<g transform="translate({xs[9]:.1f} {ys[9]:.1f})">'
              f'<line class="{left}" x2="{nx - xs[9]:.1f}" {line}/></g>'
              f'<g transform="translate({xs[11]:.1f} {ys[11]:.1f})">'
              f'<line class="{right}" x2="{nx - xs[11]:.1f}" {line}/></g>'
              f'<circle cx="{xs[9]:.1f}" cy="{ys[9]:.1f}" {dot}/><circle cx="{xs[11]:.1f}" cy="{ys[11]:.1f}" {dot}/>'
              f'<g class="{point}"><circle cx="{nx:.1f}" cy="{ny:.1f}" {dot}/>'
              f'<g font-family="DgNum, Inter, \'Segoe UI\', sans-serif" font-size="{11 * k:.2f}" text-anchor="middle" '
              f'fill="{t.TEXT}">{"".join(labels)}</g></g>')
    scene3 = scene(page3, [(0, -vh, "linear"), (t_weights, -vh, EASE), (t_weights + slide, 0, "linear"),
                           (t_out, 0, EASE), (T, vh, "linear")], -vh)

    # The cursor: one track for its position, one for its visibility and one for the press
    grab = (nx, ny)
    path = [(0, rest_cursor, "linear"), (0.4, rest_cursor, EASE), (1.3, large, "linear"),
            (t_scroll, large, EASE), (t_generate - 0.1, generate, "linear"), (t_results + 0.4, generate, "linear"),
            (t_results + 0.41, (grab[0] + 70, grab[1] + 110), "linear"),
            (t_weights + slide, (grab[0] + 70, grab[1] + 110), EASE), (t_grab - 0.1, grab, "linear")]
    path += [(t_drag + u * drag_len, (nx, ny + lift * ease_io(u)), "linear") for u in us]
    path += [(t_out, (nx, ny + lift), EASE), (T, rest_cursor, "linear")]
    cursor_move = m.track("transform", [(s, tr(*xy), e) for s, xy, e in path], tr(nx, ny + lift))
    cursor_show = m.track("opacity", [(t_results, 1, "linear"), (t_results + 0.3, 0, "linear"),
                                      (t_weights + slide - 0.1, 0, "linear"), (t_weights + slide + 0.2, 1, "linear")],
                          0)
    presses = [t_large, t_generate, t_grab]
    press_stops = [(0, "scale(1)", "linear")]
    for s in presses[:2]:
        press_stops += [(s - 0.08, "scale(1)", EASE_OUT), (s, "scale(.84)", EASE_OUT), (s + 0.18, "scale(1)", "linear")]
    press_stops += [(t_grab - 0.08, "scale(1)", EASE_OUT), (t_grab, "scale(.88)", "linear"),
                    (t_release, "scale(.88)", EASE_OUT), (t_release + 0.18, "scale(1)", "linear")]
    cursor_press = m.track("transform", press_stops, "scale(1)")
    ripples = []
    for s, (x, y) in zip(presses, [large, generate, grab], strict=True):
        ring = m.track("transform", [(s, "scale(.2)", EASE_OUT), (s + 0.5, "scale(1)", "linear"),
                                     (s + 0.51, "scale(.2)", "linear")], "scale(1)")
        fade = m.track("opacity", [(s - 0.01, 0, "linear"), (s, 0.45, EASE_OUT), (s + 0.5, 0, "linear")], 0)
        ripples.append(f'<g transform="translate({x:.1f} {y:.1f})"><g class="{fade}"><circle class="{ring}" r="22" '
                       f'fill="{t.PRIMARY}" fill-opacity="0.35"/></g></g>')
    cursor = (f'<g class="{cursor_show}"><g class="{cursor_move}"><g class="{cursor_press}">'
              f'<path d="{CURSOR}" transform="scale(1.15)" fill="#14232a" stroke="#ffffff" stroke-width="1.3" '
              f'stroke-linejoin="round" filter="url(#shadow)"/></g></g></g>')

    alt = ("Data Generator app, illustrated: the generated shop's key numbers and monthly revenue chart, then November "
           "dragged up on the month weights to reshape the season, then the Large preset and Generate data.")
    css = (font_face() + "".join(m.css)
           + "@media (prefers-reduced-motion:reduce){*{animation:none!important}}")
    host = "127.0.0.1:8050"
    out = {}
    for theme, c in FRAMES.items():
        dots = "".join(f'<circle cx="{18 + i * 16}" cy="{BAR / 2}" r="5" fill="{c["dot"]}"/>' for i in range(3))
        pill_w = 150
        svg = (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H:.0f}" width="{W}" height="{H:.0f}" '
               f'role="img" aria-label="{alt}"><title>{alt}</title>'
               f'<defs><style>{css}</style>'
               f'<clipPath id="frame"><rect x="0.5" y="0.5" width="{W - 1}" height="{H - 1:.1f}" rx="10"/></clipPath>'
               f'<clipPath id="page"><rect width="{W}" height="{vh:.1f}"/></clipPath>'
               f'<clipPath id="view"><rect x="0" y="{BAR}" width="{W}" height="{vh:.1f}"/></clipPath>'
               f'<filter id="shadow" x="-50%" y="-50%" width="200%" height="200%"><feDropShadow dx="0" dy="1.2" '
               f'stdDeviation="1.4" flood-color="#000" flood-opacity="0.35"/></filter></defs>'
               f'<g clip-path="url(#frame)"><rect width="{W}" height="{H:.1f}" fill="#ffffff"/>'
               f'<g clip-path="url(#view)"><g transform="translate(0 {BAR})">'
               f'{scene1}{scene3}{"".join(ripples)}{cursor}</g></g>'
               f'<rect width="{W}" height="{BAR}" fill="{c["bar"]}"/>'
               f'<line x1="0" y1="{BAR - 0.5}" x2="{W}" y2="{BAR - 0.5}" stroke="{c["border"]}"/>{dots}'
               f'<rect x="{W / 2 - pill_w / 2}" y="{BAR / 2 - 11}" width="{pill_w}" height="22" rx="11" '
               f'fill="{c["pill"]}" stroke="{c["border"]}"/>'
               f'<text x="{W / 2}" y="{BAR / 2 + 4.3}" text-anchor="middle" font-size="12.5" fill="{c["pill_text"]}" '
               f'font-family="ui-monospace, SFMono-Regular, Consolas, monospace">{host}</text></g>'
               f'<rect x="0.5" y="0.5" width="{W - 1}" height="{H - 1:.1f}" rx="10" fill="none" '
               f'stroke="{c["border"]}"/></svg>')
        out[theme] = svg
    return out, T


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--shots", type=Path, help="keep the screenshots and geometry in this folder")
    ap.add_argument("--reuse", action="store_true", help="build from --shots without starting the app")
    ap.add_argument("--quality", type=int, default=74, help="WebP quality of the screenshots")
    a = ap.parse_args()
    shots = a.shots or Path(tempfile.mkdtemp())
    shots.mkdir(parents=True, exist_ok=True)
    if not (a.reuse and (shots / "geometry.json").exists()):
        sys.path.insert(0, str(PROJECT_DIR / "scripts"))
        from make_charts import find_browser

        browser = find_browser()
        app = start_app()
        try:
            asyncio.run(capture(browser, f"http://127.0.0.1:{APP_PORT}", shots))
        finally:
            stop_app(app)
    svgs, total = build(shots, a.quality)
    for theme, svg in svgs.items():
        path = OUT_DIR / ("app-demo.svg" if theme == "light" else "app-demo-dark.svg")
        path.write_text(svg, encoding="utf-8", newline="\n")
        kb = path.stat().st_size / 1024
        print(f"{path.name}: {kb:.0f} KB, loop {total:g} s")
        if path.stat().st_size > LIMIT:
            sys.exit(f"{path.name} is over {LIMIT // 1024} KB: lower --quality.")


if __name__ == "__main__":
    main()
