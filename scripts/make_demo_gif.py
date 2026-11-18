"""
Record docs/img/app-demo.gif, the README demo of the app, with real input events in headless Chrome or Edge (CDP).

Usage (from the repository root, with requirements-dev.txt installed):
    python scripts/make_demo_gif.py [out.gif]

The script starts the app itself on 127.0.0.1 with English number notation (DG_NOTATION=en), records the scenes and
stops the app: pick Large, generate, glide through the preview and the charts, open Advanced and drag November up.
Motion is smooth: eased scrolls at FRAME_MS per frame, a time-lapse of the progress bar, short cross-fades instead
of cuts (also at the loop seam) and an eased drag. Set CHROME to the browser executable if it is not found.
"""
import asyncio
import base64
import io
import json
import os
import subprocess
import sys
import tempfile
import time
import urllib.request
from pathlib import Path

import websockets
from PIL import Image, ImageChops

PROJECT_DIR = Path(__file__).resolve().parents[1]
OUT = PROJECT_DIR / "docs" / "img" / "app-demo.gif"
PORT = 9336  # DevTools
APP_PORT = 8765  # the app, away from the default 8050
WIDTH, HEIGHT, OUT_WIDTH = 1280, 760, 960
FRAME_MS = 70  # ~14 fps for every moving part
COLORS = 96


def ease(t):
    """Cubic ease-in-out: slow start, fast middle, gentle stop."""
    return 4 * t ** 3 if t < 0.5 else 1 - (-2 * t + 2) ** 3 / 2


async def record(browser, url, out_path):
    profile = tempfile.mkdtemp()
    proc = subprocess.Popen([browser, "--headless=new", "--disable-gpu", f"--remote-debugging-port={PORT}",
                             f"--user-data-dir={profile}", "--hide-scrollbars", "about:blank"],
                            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    frames = []  # [image, duration ms]
    try:
        for _ in range(50):
            try:
                page = next(t for t in json.load(urllib.request.urlopen(f"http://127.0.0.1:{PORT}/json"))
                            if t["type"] == "page")
                break
            except Exception:
                time.sleep(0.2)
        ws = await websockets.connect(page["webSocketDebuggerUrl"], max_size=200 * 1024 * 1024)
        counter = 0

        async def send(method, **params):
            nonlocal counter
            counter += 1
            my_id = counter
            await ws.send(json.dumps({"id": my_id, "method": method, "params": params}))
            while True:
                message = json.loads(await ws.recv())
                if message.get("id") == my_id:
                    return message.get("result", {})

        async def js(expression):
            return (await send("Runtime.evaluate", expression=expression, returnByValue=True)).get("result", {}).get("value")

        async def grab():
            data = (await send("Page.captureScreenshot", format="png"))["data"]
            image = Image.open(io.BytesIO(base64.b64decode(data))).convert("RGB")
            image = image.resize((OUT_WIDTH, round(image.height * OUT_WIDTH / image.width)), Image.LANCZOS)
            return image.point(lambda v: 255 if v >= 248 else v)  # near-white resize noise -> the white page

        async def frame(duration=FRAME_MS):
            frames.append([await grab(), duration])

        def hold(duration):
            frames[-1][1] = duration

        async def fade_to(duration, steps=3):
            """Cross-fade from the last frame to the current page instead of a cut."""
            before, after = frames[-1][0], await grab()
            for step in range(1, steps + 1):
                frames.append([Image.blend(before, after, step / (steps + 1)), FRAME_MS])
            frames.append([after, duration])

        async def scroll_to(selector, offset, per_frame=110, low=8, high=18):
            target = await js(f"Math.min(document.querySelector('{selector}').getBoundingClientRect().top + scrollY - {offset},"
                              " document.documentElement.scrollHeight - innerHeight)")
            start = await js("scrollY")
            if abs(target - start) < 40:  # already there (the app scrolls to the results itself)
                return
            steps = max(low, min(high, round(abs(target - start) / per_frame)))
            for step in range(1, steps + 1):
                await js(f"window.scrollTo(0, {round(start + (target - start) * ease(step / steps))})")
                await asyncio.sleep(0.04)
                await frame()

        await send("Emulation.setDeviceMetricsOverride", width=WIDTH, height=HEIGHT, deviceScaleFactor=1, mobile=False)
        await send("Page.enable")
        await send("Page.navigate", url=url)
        await asyncio.sleep(5)
        await js("document.documentElement.style.scrollBehavior = 'auto'")
        await js("window.scrollTo(0, document.querySelector('#parameters').getBoundingClientRect().top + scrollY - 20)")
        await asyncio.sleep(0.5)
        await frame(1100)
        # Pick Large
        await js("[...document.querySelectorAll('.dg-preset')].find(b => b.textContent.startsWith('Large')).click()")
        await asyncio.sleep(0.8)
        await fade_to(1100)
        # Generate, glide down to the progress bar, then a time-lapse of the run (the wait itself is cut)
        await js("document.getElementById('generate').click()")
        await asyncio.sleep(0.3)
        await scroll_to("#generate", 520)
        started = time.monotonic()
        while time.monotonic() - started < 60:
            if await js("document.querySelectorAll('#charts .js-plotly-plot').length >= 3"):
                break
            await frame()
            await asyncio.sleep(1.5)
        await asyncio.sleep(2)
        await fade_to(1300)  # the app has scrolled to the Preview by itself
        await scroll_to("#preview", 20)
        await scroll_to("#charts", 20)
        hold(1500)
        # Advanced: open it, glide up to the month weights and drag November up
        await js("[...document.querySelectorAll('.mantine-Accordion-control')].find(b => b.textContent.includes('Advanced')).click()")
        await asyncio.sleep(1.5)
        await scroll_to("#weights-month-graph", 230)
        hold(700)
        point = json.loads(await js("""(() => { const gd = document.querySelector('#weights-month-graph .js-plotly-plot');
            const L = gd._fullLayout, r = gd.getBoundingClientRect(), t = gd.data[0];
            const top = r.top + L._size.t;
            return JSON.stringify({x: r.left + L._size.l + L.xaxis.d2p(t.x[10]), y: top + L.yaxis.d2p(t.y[10]),
                                   ceiling: top + L.yaxis.d2p(L.yaxis.range[1] * 0.88)}); })()"""))
        x, y = point["x"], point["y"]
        lift, steps = y - point["ceiling"] - 1, 14  # drag November right up to the drag ceiling, no frozen frames
        await send("Input.dispatchMouseEvent", type="mouseMoved", x=x, y=y)
        await send("Input.dispatchMouseEvent", type="mousePressed", x=x, y=y, button="left", clickCount=1)
        for step in range(1, steps + 1):
            await send("Input.dispatchMouseEvent", type="mouseMoved", x=x, y=y - lift * ease(step / steps),
                       button="left", buttons=1)
            await asyncio.sleep(0.15)
            await frame()
        await send("Input.dispatchMouseEvent", type="mouseReleased", x=x, y=y - lift, button="left", clickCount=1)
        await asyncio.sleep(1)
        await fade_to(1800)  # the axis grows after the release
        # Loop seam: fade back to the first frame
        first, last = frames[0][0], frames[-1][0]
        for step in range(1, 5):
            frames.append([Image.blend(last, first, step / 5), FRAME_MS])
    finally:
        proc.terminate()

    # Drop exact repeats (merge their time), one shared palette for all frames, pure white background.
    merged = [frames[0]]
    for image, duration in frames[1:]:
        if ImageChops.difference(image, merged[-1][0]).getbbox() is None:
            merged[-1][1] += duration
        else:
            merged.append([image, duration])
    sample = merged[::2]
    strip = Image.new("RGB", (OUT_WIDTH, sum(image.height for image, _ in sample)))
    top = 0
    for image, _ in sample:
        strip.paste(image, (0, top))
        top += image.height
    palette = strip.quantize(colors=COLORS, method=Image.Quantize.MEDIANCUT, dither=Image.Dither.NONE)
    colors = palette.getpalette()[:COLORS * 3]
    lightest = max(range(COLORS), key=lambda i: sum(colors[i * 3:i * 3 + 3]))
    colors[lightest * 3:lightest * 3 + 3] = [255, 255, 255]
    palette = Image.new("P", (1, 1))
    palette.putpalette(colors + [0, 0, 0] * (256 - COLORS))
    images = [image.quantize(palette=palette, dither=Image.Dither.NONE) for image, _ in merged]
    images[0].save(out_path, save_all=True, append_images=images[1:], duration=[d for _, d in merged], loop=0,
                   optimize=False, disposal=1)
    moving = sum(1 for _, d in merged if d <= FRAME_MS)
    total = sum(d for _, d in merged)
    print(len(merged), "frames,", moving, "moving at", FRAME_MS, "ms,", total / 1000, "s")


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


def main():
    sys.path.insert(0, str(PROJECT_DIR / "scripts"))
    from make_charts import find_browser

    out_path = Path(sys.argv[1]) if len(sys.argv) > 1 else OUT
    browser = find_browser()
    app = start_app()
    try:
        asyncio.run(record(browser, f"http://127.0.0.1:{APP_PORT}", out_path))
    finally:
        stop_app(app)
    print(f"GIF saved to {out_path}")


if __name__ == "__main__":
    main()
