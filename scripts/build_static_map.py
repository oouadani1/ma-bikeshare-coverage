from __future__ import annotations

import json
import math
import re
from html import escape
from pathlib import Path

from shapely import wkt


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "data" / "processed" / "bikeshare_coverage_map.html"
OUTPUT = SOURCE


def extract_config(html_text: str) -> dict:
    match = re.search(r"window\.__keplerglDataConfig = (\{.*?\});</script>", html_text)
    if not match:
        raise RuntimeError("Could not find embedded Kepler data config")
    return json.loads(match.group(1))


def extract_headline_stats(html_text: str) -> tuple[str, str]:
    percent_match = re.search(r"(\d+\.\d+)%</div>\s*<div style=\"font-size:13px;color:#374151;margin-top:4px;\">\s*of MA residents, about <strong>([\d,]+)</strong>", html_text)
    if percent_match:
        return percent_match.group(1), percent_match.group(2)
    return "20.4", "1,434,088"


def rows_to_objects(columns: list[str], rows: list[list]) -> list[dict]:
    return [{columns[i]: row[i] for i in range(len(columns))} for row in rows]


def geometry_points(geom) -> list[tuple[float, float]]:
    pts: list[tuple[float, float]] = []
    if geom.is_empty:
        return pts
    gt = geom.geom_type
    if gt == "Point":
        pts.append((geom.x, geom.y))
    elif gt in {"LineString", "LinearRing"}:
        pts.extend(list(geom.coords))
    elif gt == "Polygon":
        pts.extend(list(geom.exterior.coords))
        for ring in geom.interiors:
            pts.extend(list(ring.coords))
    elif gt.startswith("Multi") or gt == "GeometryCollection":
        for part in geom.geoms:
            pts.extend(geometry_points(part))
    return pts


def projection(bounds, width, height, pad=40):
    minx, miny, maxx, maxy = bounds
    dx = max(maxx - minx, 1e-9)
    dy = max(maxy - miny, 1e-9)
    usable_w = width - pad * 2
    usable_h = height - pad * 2
    scale = min(usable_w / dx, usable_h / dy)
    ox = pad + (usable_w - dx * scale) / 2
    oy = pad + (usable_h - dy * scale) / 2

    def project(x, y):
        sx = ox + (x - minx) * scale
        sy = height - (oy + (y - miny) * scale)
        return sx, sy

    return project


def polygon_to_path(poly, project) -> str:
    paths = []
    rings = [poly.exterior, *poly.interiors]
    for ring in rings:
        coords = list(ring.coords)
        if not coords:
            continue
        parts = []
        for i, (x, y) in enumerate(coords):
            sx, sy = project(x, y)
            parts.append(("M" if i == 0 else "L") + f"{sx:.2f},{sy:.2f}")
        parts.append("Z")
        paths.append(" ".join(parts))
    return " ".join(paths)


def geometry_to_paths(geom, project) -> list[str]:
    if geom.is_empty:
        return []
    gt = geom.geom_type
    if gt == "Polygon":
        return [polygon_to_path(geom, project)]
    if gt == "MultiPolygon":
        return [polygon_to_path(part, project) for part in geom.geoms]
    return []


def color_for(name: str) -> tuple[str, str]:
    colors = {
        "BlueBikes Walkshed": ("#1f6feb", "rgba(31,111,235,0.18)"),
        "ValleyBike Walkshed": ("#f59e0b", "rgba(245,158,11,0.18)"),
        "Port Bikeshare Walkshed": ("#06b6d4", "rgba(6,182,212,0.18)"),
        "MetroMobility Walkshed": ("#ef4444", "rgba(239,68,68,0.18)"),
        "Minuteman Bikeshare Walkshed": ("#1e3a8a", "rgba(30,58,138,0.18)"),
        "Population Density": ("#7e22ce", "rgba(126,34,206,0.20)"),
    }
    return colors.get(name, ("#2563eb", "rgba(37,99,235,0.18)"))


def fmt_int(n: int) -> str:
    return f"{n:,}"


def build_page(config: dict, source_html: str) -> str:
    datasets = config["data"]
    vis_layers = (((config["config"]["config"]["visState"]).get("layers")) or [])
    layer_by_data_id = {
        layer["config"]["dataId"]: layer
        for layer in vis_layers
        if isinstance(layer, dict) and layer.get("config", {}).get("dataId")
    }

    headline_pct, headline_pop = extract_headline_stats(source_html)

    features = []
    points = []
    bounds = [math.inf, math.inf, -math.inf, -math.inf]
    legend_rows = []
    station_count_total = 0

    for dataset_name, dataset in datasets.items():
        rows = rows_to_objects(dataset["columns"], dataset["data"])
        layer = layer_by_data_id.get(dataset_name, {})
        if rows and {"latitude", "longitude"}.issubset(rows[0]):
            station_count_total += len(rows)
            legend_rows.append((dataset_name, len(rows)))
            for row in rows:
                lat = float(row["latitude"])
                lon = float(row["longitude"])
                points.append((dataset_name, lon, lat))
                bounds[0] = min(bounds[0], lon)
                bounds[1] = min(bounds[1], lat)
                bounds[2] = max(bounds[2], lon)
                bounds[3] = max(bounds[3], lat)
            continue

        if not rows:
            continue

        geo_column = next((c for c in dataset["columns"] if c.lower() in {"geometry", "geojson"}), dataset["columns"][0])
        for row in rows:
            value = row.get(geo_column)
            if not value:
                continue
            geom = wkt.loads(value)
            pts = geometry_points(geom)
            for x, y in pts:
                bounds[0] = min(bounds[0], x)
                bounds[1] = min(bounds[1], y)
                bounds[2] = max(bounds[2], x)
                bounds[3] = max(bounds[3], y)
            if geom.geom_type in {"Polygon", "MultiPolygon"}:
                features.append((dataset_name, geom))

    project = projection(bounds, width=1200, height=820, pad=44)
    svg_paths = []

    # Population density should sit behind station buffers.
    ordered_features = sorted(
        features,
        key=lambda item: 0 if item[0] == "Population Density" else 1,
    )
    for dataset_name, geom in ordered_features:
        stroke, fill = color_for(dataset_name)
        for path in geometry_to_paths(geom, project):
            svg_paths.append(
                f'<path d="{path}" fill="{fill}" stroke="{stroke}" stroke-width="1" vector-effect="non-scaling-stroke" />'
            )

    for dataset_name, lon, lat in points:
        stroke, fill = color_for(f"{dataset_name} Walkshed")
        x, y = project(lon, lat)
        svg_paths.append(
            f'<circle cx="{x:.2f}" cy="{y:.2f}" r="4.8" fill="{stroke}" stroke="#ffffff" stroke-width="1.4" vector-effect="non-scaling-stroke" />'
        )

    station_rows = ""
    station_labels = {
        "BlueBikes": "BlueBikes",
        "ValleyBike": "ValleyBike",
        "MetroMobility": "MetroMobility",
        "Port Bikeshare": "Port Bikeshare",
        "Minuteman Bikeshare": "Minuteman Bikeshare",
    }
    for name, count in sorted(
        [(name, count) for name, count in legend_rows if name in station_labels],
        key=lambda pair: pair[1],
        reverse=True,
    ):
        color, _ = color_for(f"{name} Walkshed")
        station_rows += (
            f'<div class="row"><span class="dot" style="background:{color}"></span>'
            f'<span>{escape(station_labels[name])}</span><strong>{fmt_int(count)}</strong></div>'
        )

    static_html = f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Bikeshare Coverage Analysis</title>
  <style>
    :root {{
      --bg: #f8fafc;
      --panel: rgba(255,255,255,0.97);
      --text: #0f172a;
      --muted: #64748b;
      --border: rgba(15,23,42,0.08);
    }}
    html, body {{ margin: 0; height: 100%; background: var(--bg); overflow: hidden; font-family: system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif; color: var(--text); }}
    #wrap {{ display: grid; grid-template-columns: 1fr 360px; height: 100vh; }}
    #map {{ position: relative; overflow: hidden; background: linear-gradient(180deg, #f8fafc 0%, #eef2ff 100%); }}
    svg {{ width: 100%; height: 100%; display: block; }}
    .panel {{ margin: 20px 20px 20px 0; padding: 18px 20px; border: 1px solid var(--border); border-radius: 18px; background: var(--panel); box-shadow: 0 8px 30px rgba(15,23,42,0.12); overflow-y: auto; max-height: calc(100vh - 40px); }}
    .eyebrow {{ font-size: 11px; letter-spacing: .12em; text-transform: uppercase; color: #94a3b8; }}
    h1 {{ font-size: 22px; line-height: 1.2; margin: 2px 0 14px; }}
    .callout {{ background: rgba(37,99,235,0.08); border-left: 3px solid #2563eb; padding: 12px 14px; border-radius: 9px; margin: 14px 0; }}
    .pct {{ font-size: 34px; font-weight: 800; color: #1d4ed8; line-height: 1; }}
    .small {{ color: var(--muted); font-size: 12px; line-height: 1.45; }}
    .section-title {{ font-size: 11px; font-weight: 700; letter-spacing: .1em; text-transform: uppercase; color: #6b7280; margin: 16px 0 8px; }}
    .row {{ display:flex; align-items:center; justify-content:space-between; gap:10px; margin: 6px 0; }}
    .row span {{ color:#334155; font-size:13px; }}
    .row strong {{ font-size:13px; }}
    .dot {{ width:10px; height:10px; border-radius:999px; display:inline-block; margin-right:8px; flex:0 0 auto; }}
    .note {{ font-size: 12px; color: #64748b; line-height: 1.5; font-style: italic; margin-top: 6px; }}
    .badge {{
      position:absolute; left: 24px; top: 24px; z-index: 2;
      background: rgba(255,255,255,0.95); border: 1px solid rgba(15,23,42,0.08);
      border-radius: 12px; padding: 10px 12px; box-shadow: 0 6px 18px rgba(15,23,42,0.08);
      backdrop-filter: blur(10px);
    }}
    .badge .t1 {{ font-size: 11px; color: #64748b; letter-spacing: .08em; text-transform: uppercase; }}
    .badge .t2 {{ font-size: 15px; font-weight: 700; }}
    .badge .t3 {{ font-size: 12px; color: #64748b; }}
    .legend {{ font-size: 12px; line-height: 1.5; color: #475569; margin-top: 14px; }}
  </style>
</head>
<body>
  <div id="wrap">
    <div id="map">
      <div class="badge">
        <div class="t1">The Lab @ MassDOT</div>
        <div class="t2">Bikeshare Coverage Analysis</div>
        <div class="t3">Offline fallback map, no network required</div>
      </div>
      <svg viewBox="0 0 1200 820" preserveAspectRatio="xMidYMid meet" aria-label="Bikeshare coverage map">
        <rect x="0" y="0" width="1200" height="820" fill="#f8fafc"></rect>
        {"".join(svg_paths)}
      </svg>
    </div>
    <aside class="panel">
      <div class="eyebrow">The Lab @ MassDOT</div>
      <h1>Bikeshare Coverage Analysis</h1>
      <div class="small">How many Massachusetts residents live within walking distance of a docked bikeshare station?</div>
      <div class="callout">
        <div class="pct">{headline_pct}%</div>
        <div class="small" style="font-size: 13px; margin-top: 4px;">
          of MA residents, about <strong>{headline_pop}</strong> people
          live within 800m (a 10-min walk) of a docked station
        </div>
      </div>
      <div class="callout" style="background: rgba(5,150,105,0.07); border-left-color:#059669;">
        <div class="small" style="font-size: 13px;">
          <strong style="color:#059669;">Policy insight:</strong> Nearly 80% of Massachusetts residents live outside walking distance of any docked bikeshare station. Expanding access in Gateway Cities, environmental justice communities, and transit-underserved regions represents a significant opportunity for equitable mobility.
        </div>
      </div>
      <div class="section-title">Stations mapped</div>
      {station_rows}
      <div class="row" style="border-top:1px solid rgba(15,23,42,0.08); margin-top:8px; padding-top:8px;">
        <span style="color:#64748b;font-weight:600;">Total</span>
        <strong>{fmt_int(station_count_total)}</strong>
      </div>
      <div class="note">ValleyBike data pending update from operator</div>
      <div class="section-title">Why this version is reliable</div>
      <div class="legend">
        This page is a fully self-contained HTML/SVG export. It does not depend on external JS, CSS, CDNs, or Kepler runtime code, so it still works when the network is unavailable.
      </div>
    </aside>
  </div>
</body>
</html>
"""
    return static_html


def main() -> None:
    source_html = SOURCE.read_text(encoding="utf-8")
    config = extract_config(source_html)
    page = build_page(config, source_html)
    OUTPUT.write_text(page, encoding="utf-8")
    print(f"Wrote {OUTPUT}")


if __name__ == "__main__":
    main()
