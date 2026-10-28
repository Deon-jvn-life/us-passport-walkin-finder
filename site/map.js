/* Lazy map for facility lists. Leaflet is loaded only when the map is near the screen. */
(function () {
  var el = document.getElementById("facility-map");
  var dataEl = document.getElementById("facility-map-data");
  if (!el || !dataEl) return;
  var points = [];
  try {
    points = JSON.parse(dataEl.textContent);
  } catch (e) {
    return;
  }
  if (!points.length) return;
  var label = el.getAttribute("aria-label") || "Map of places on this page";
  var started = false;

  function esc(s) {
    return String(s == null ? "" : s).replace(/[&<>"']/g, function (c) {
      return {"&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;"}[c];
    });
  }

  function popupHtml(p) {
    var dir = String(p.directions || "");
    var ok = dir.indexOf("https://www.google.com/maps/dir/?api=1&destination=") === 0;
    var link = ok
      ? '<p><a href="' + esc(dir) + '" target="_blank" rel="noopener">Get directions<span class="visually-hidden"> to ' + esc(p.name) + ', opens in a new tab</span></a></p>'
      : "";
    return "<p><strong>" + esc(p.name) + "</strong></p><p>" + esc(p.address) + "</p>" + link;
  }

  function paintRules() {
    var style = document.createElement("style");
    style.textContent = [
      '.leaflet-container,.leaflet-container *{font-family:system-ui,-apple-system,"Segoe UI",Roboto,sans-serif}',
      ".leaflet-container{z-index:0;background:#E7EFE9;color:#1A1814;font-size:1rem}",
      ".leaflet-popup-content-wrapper,.leaflet-popup-tip{background:#fff;color:#1A1814;box-shadow:0 2px 12px rgba(0,0,0,.28)}",
      ".leaflet-popup-content,.leaflet-popup-content p,.leaflet-popup-content strong{background:#fff;color:#1A1814}",
      ".leaflet-popup-content{margin:16px 48px 16px 16px;font-size:1rem;line-height:1.5}",
      ".leaflet-popup-content p{margin:0 0 12px}",
      ".leaflet-popup-content p:last-child{margin:0}",
      ".leaflet-popup-content a{color:#0A3D66;background:#fff}",
      ".leaflet-container a.leaflet-popup-close-button{width:44px;height:44px;font-size:1.5rem;line-height:44px;color:#1A1814;padding:0}",
      ".leaflet-bar a{width:44px;height:44px;line-height:44px;font-size:1.25rem;color:#1A1814;background:#fff}",
      ".leaflet-control-attribution{background:rgba(255,255,255,.94);color:#1A1814;font-size:1rem;line-height:1.4;max-width:100%}",
      ".leaflet-control-attribution a{color:#0A3D66}"
    ].join("");
    document.head.appendChild(style);
  }

  function fail() {
    el.textContent = "The map could not be loaded. The list on this page has every place.";
    el.setAttribute("aria-busy", "false");
  }

  function init() {
    if (!window.L) {
      fail();
      return;
    }
    paintRules();
    var reduce = false;
    try {
      reduce = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    } catch (err) {
      reduce = false;
    }
    el.textContent = "";
    el.classList.add("is-ready");
    var map = window.L.map(el, {
      scrollWheelZoom: false,
      fadeAnimation: !reduce,
      zoomAnimation: !reduce,
      markerZoomAnimation: !reduce,
      keyboard: true
    });
    window.L.tileLayer("https://tile.openstreetmap.org/{z}/{x}/{y}.png", {
      maxZoom: 19,
      attribution: '&copy; <a href="https://www.openstreetmap.org/copyright" rel="noopener">OpenStreetMap</a> contributors'
    }).addTo(map);
    var bounds = [];
    points.forEach(function (p) {
      if (typeof p.lat !== "number" || typeof p.lon !== "number") return;
      if (p.lat < 25.2 || p.lat > 27.2 || p.lon < -81.05 || p.lon > -79.9) return;
      var marker = window.L.marker([p.lat, p.lon], {keyboard: false, alt: p.name || "Place"});
      marker.bindPopup(popupHtml(p), {
        maxWidth: 320,
        autoPanPaddingTopLeft: [16, 148],
        autoPanPaddingBottomRight: [16, 24]
      });
      marker.addTo(map);
      bounds.push([p.lat, p.lon]);
    });
    if (!bounds.length) {
      fail();
      return;
    }
    if (bounds.length === 1) map.setView(bounds[0], 15);
    else map.fitBounds(bounds, {padding: [32, 32]});
    el.setAttribute("role", "region");
    el.setAttribute("aria-label", label);
    el.setAttribute("aria-busy", "false");
    map.scrollWheelZoom.disable();
    el.addEventListener("click", function () {
      map.scrollWheelZoom.enable();
    });
    document.addEventListener("click", function (ev) {
      if (!el.contains(ev.target)) map.scrollWheelZoom.disable();
    });
    window.setTimeout(function () {
      map.invalidateSize();
    }, 0);
  }

  function loadScript() {
    var script = document.createElement("script");
    script.src = el.getAttribute("data-leaflet");
    script.onload = init;
    script.onerror = fail;
    document.body.appendChild(script);
  }

  function load() {
    if (started) return;
    started = true;
    var css = document.createElement("link");
    css.rel = "stylesheet";
    css.href = el.getAttribute("data-leaflet-css");
    css.onload = loadScript;
    css.onerror = fail;
    document.head.appendChild(css);
  }

  el.setAttribute("aria-busy", "true");
  if ("IntersectionObserver" in window) {
    var watcher = new IntersectionObserver(function (entries) {
      for (var i = 0; i < entries.length; i++) {
        if (entries[i].isIntersecting) {
          watcher.disconnect();
          load();
          return;
        }
      }
    }, {rootMargin: "200px 0px"});
    watcher.observe(el);
  } else if (document.readyState === "complete") {
    load();
  } else {
    window.addEventListener("load", load);
  }
})();
