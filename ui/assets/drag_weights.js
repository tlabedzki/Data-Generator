/*
 * Draggable seasonality weights. Each .dg-weights-graph holds a Plotly chart with one point per month or weekday.
 * Grab a point (mouse, pen or finger), move it up or down and the value follows live; on release the values go to
 * the Dash store "<graph id minus -graph>-drag", which fills in the number fields the generator reads.
 * Numbers are written with a decimal comma, like the rest of the app.
 */
(function () {
  "use strict";

  var HIT_RADIUS = 22;  // px around a point that starts a drag

  function format(value, decimal) {
    return value.toFixed(2).replace(".", decimal || ",");
  }

  function storeId(container) {
    return container.id.replace(/-graph$/, "-drag");
  }

  function attach(container) {
    var gd = container.querySelector(".js-plotly-plot");
    if (!gd || gd.__dgDrag || !gd._fullLayout || !gd.data) {
      return;
    }
    gd.__dgDrag = true;
    var drag = null;

    function axes() {
      var layout = gd._fullLayout;
      return {x: layout.xaxis, y: layout.yaxis, left: layout._size.l, top: layout._size.t};
    }

    function local(event) {
      var rect = gd.getBoundingClientRect();
      return {x: event.clientX - rect.left, y: event.clientY - rect.top};
    }

    function nearest(event) {
      var a = axes(), p = local(event), trace = gd.data[0], best = null;
      for (var i = 0; i < trace.x.length; i++) {
        var px = a.left + a.x.d2p(trace.x[i]), py = a.top + a.y.d2p(trace.y[i]);
        var distance = Math.hypot(px - p.x, py - p.y);
        if (distance <= HIT_RADIUS && (!best || distance < best.distance)) {
          best = {index: i, distance: distance};
        }
      }
      return best;
    }

    function valueAt(event) {
      var a = axes(), meta = gd.layout.meta || {}, max = meta.max || 1, step = meta.step || 0.01;
      // The scale stays fixed while dragging; a point stops just below the top edge so its value stays visible.
      var ceiling = Math.min(max, a.y.range[1] * 0.88);
      var value = a.y.p2d(local(event).y - a.top);
      value = Math.round(value / step) * step;
      return Math.max(0, Math.min(ceiling, value));
    }

    function redraw(values, active) {
      var decimal = (gd.layout.meta || {}).decimal;
      Plotly.restyle(gd, {y: [values.slice()], text: [values.map(function (v) { return format(v, decimal); })]}, [0]);
      // On narrow screens the labels are hidden by CSS; keep the one being dragged visible.
      var labels = gd.querySelectorAll(".textpoint");
      for (var i = 0; i < labels.length; i++) { labels[i].classList.toggle("dg-active", i === active); }
    }

    gd.addEventListener("pointerdown", function (event) {
      var hit = nearest(event);
      if (!hit) {
        return;
      }
      event.preventDefault();
      event.stopPropagation();
      drag = {index: hit.index, values: gd.data[0].y.map(Number), pointer: event.pointerId};
      try { gd.setPointerCapture(event.pointerId); } catch (error) { /* synthetic events have no capture */ }
      gd.classList.add("is-dragging");
    }, true);

    gd.addEventListener("pointermove", function (event) {
      if (!drag) {
        gd.style.cursor = nearest(event) ? "ns-resize" : "";
        return;
      }
      event.preventDefault();
      var value = valueAt(event);
      if (value !== drag.values[drag.index]) {
        drag.values[drag.index] = value;
        redraw(drag.values, drag.index);
      }
    }, true);

    function finish(event) {
      if (!drag) {
        return;
      }
      var values = drag.values.map(function (v) { return Math.round(v * 100) / 100; });
      drag = null;
      // After the drag, make room above a high point so it can be dragged further next time.
      var meta = gd.layout.meta || {}, top = gd._fullLayout.yaxis.range[1];
      var needed = Math.max.apply(null, values) * 1.45;
      if (needed > top) {
        Plotly.relayout(gd, {"yaxis.range": [0, Math.min(needed, (meta.max || 1) * 1.15)]});
      }
      gd.classList.remove("is-dragging");
      try { gd.releasePointerCapture(event.pointerId); } catch (error) { /* ignore */ }
      if (window.dash_clientside && window.dash_clientside.set_props) {
        window.dash_clientside.set_props(storeId(container), {data: values});
      }
    }

    gd.addEventListener("pointerup", finish, true);
    gd.addEventListener("pointercancel", finish, true);

    // A chart drawn inside the collapsed Advanced section has no width yet: redraw it once it becomes visible.
    if (window.ResizeObserver) {
      new ResizeObserver(function () {
        if (gd.offsetWidth > 0) { Plotly.Plots.resize(gd); }
      }).observe(container);
    }
  }

  function scan() {
    var graphs = document.querySelectorAll(".dg-weights-graph");
    for (var i = 0; i < graphs.length; i++) { attach(graphs[i]); }
  }

  new MutationObserver(scan).observe(document.documentElement, {childList: true, subtree: true});
  document.addEventListener("DOMContentLoaded", scan);
})();
