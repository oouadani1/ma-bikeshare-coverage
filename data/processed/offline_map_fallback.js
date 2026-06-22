(function () {
  function ready(fn) {
    if (document.readyState === 'loading') {
      document.addEventListener('DOMContentLoaded', fn, { once: true });
    } else {
      fn();
    }
  }

  function rowsToObjects(columns, rows) {
    return rows.map(function (row) {
      var obj = {};
      for (var i = 0; i < columns.length; i += 1) obj[columns[i]] = row[i];
      return obj;
    });
  }

  function parsePairs(text) {
    return text
      .trim()
      .split(',')
      .map(function (pair) {
        var parts = pair.trim().split(/\s+/);
        return [parseFloat(parts[0]), parseFloat(parts[1])];
      })
      .filter(function (pair) {
        return Number.isFinite(pair[0]) && Number.isFinite(pair[1]);
      });
  }

  function parseWktPolygons(wkt) {
    if (!wkt || typeof wkt !== 'string') return [];
    var text = wkt.trim();
    if (/^POLYGON\s+EMPTY$/i.test(text) || /^MULTIPOLYGON\s+EMPTY$/i.test(text)) return [];
    var match;

    match = text.match(/^POLYGON\s*\(\((.*)\)\)$/i);
    if (match) return [ [ parsePairs(match[1]) ] ];

    match = text.match(/^MULTIPOLYGON\s*\(\(\((.*)\)\)\)$/i);
    if (!match) return [];
    return match[1]
      .split(/\)\)\s*,\s*\(\(/)
      .map(function (polygonText) {
        return polygonText
          .split(/\)\s*,\s*\(/)
          .map(function (ringText) {
            return parsePairs(ringText.replace(/^\(+|\)+$/g, ''));
          })
          .filter(function (ring) {
            return ring.length > 0;
          });
      })
      .filter(function (polygon) {
        return polygon.length > 0;
      });
  }

  function collectCoords(geometry, coords) {
    if (!geometry) return;
    if (Array.isArray(geometry)) {
      if (geometry.length >= 2 && typeof geometry[0] === 'number' && typeof geometry[1] === 'number') {
        coords.push(geometry);
        return;
      }
      geometry.forEach(function (part) {
        collectCoords(part, coords);
      });
      return;
    }
    if (geometry.type === 'Point') coords.push(geometry.coordinates);
    else if (geometry.type === 'LineString' || geometry.type === 'MultiPoint') geometry.coordinates.forEach(function (pt) { coords.push(pt); });
    else if (geometry.type === 'Polygon' || geometry.type === 'MultiLineString') geometry.coordinates.forEach(function (ring) { ring.forEach(function (pt) { coords.push(pt); }); });
    else if (geometry.type === 'MultiPolygon') geometry.coordinates.forEach(function (polygon) {
      polygon.forEach(function (ring) {
        ring.forEach(function (pt) { coords.push(pt); });
      });
    });
  }

  function projectFactory(bounds, width, height) {
    var minX = bounds.minX, minY = bounds.minY, maxX = bounds.maxX, maxY = bounds.maxY;
    var dx = Math.max(1e-9, maxX - minX);
    var dy = Math.max(1e-9, maxY - minY);
    var pad = 36;
    var usableW = Math.max(10, width - pad * 2);
    var usableH = Math.max(10, height - pad * 2);
    var scale = Math.min(usableW / dx, usableH / dy);
    var offsetX = pad + (usableW - dx * scale) / 2;
    var offsetY = pad + (usableH - dy * scale) / 2;
    return function (lon, lat) {
      return [
        offsetX + (lon - minX) * scale,
        height - offsetY - (lat - minY) * scale
      ];
    };
  }

  function pathFromPolygon(polygon, project) {
    return polygon.map(function (ring) {
      return ring.map(function (pt, idx) {
        var xy = project(pt[0], pt[1]);
        return (idx === 0 ? 'M' : 'L') + xy[0].toFixed(2) + ',' + xy[1].toFixed(2);
      }).join(' ') + ' Z';
    }).join(' ');
  }

  function layerByDataId(config) {
    var visState = (((config || {}).config || {}).config || {}).visState;
    var layers = (visState && visState.layers) || [];
    var map = {};
    layers.forEach(function (layer) {
      var dataId = layer && layer.config && layer.config.dataId;
      if (dataId) map[dataId] = layer;
    });
    return map;
  }

  function getColor(layer, fallback) {
    if (layer && layer.config && Array.isArray(layer.config.color)) return 'rgb(' + layer.config.color.join(',') + ')';
    return fallback;
  }

  function render() {
    var app = document.getElementById('app');
    var config = window.__keplerglDataConfig;
    if (!app || !config) return;
    if (window.KeplerGl || app.querySelector('.kepler-gl')) return;

    var datasets = config.data || {};
    var layers = layerByDataId(config);
    var features = [];
    var points = [];

    Object.keys(datasets).forEach(function (name) {
      var dataset = datasets[name];
      if (!dataset || !dataset.columns || !dataset.data) return;
      var rows = rowsToObjects(dataset.columns, dataset.data);
      var layer = layers[name];
      if (rows.length && Object.prototype.hasOwnProperty.call(rows[0], 'latitude') && Object.prototype.hasOwnProperty.call(rows[0], 'longitude')) {
        rows.forEach(function (row) {
          var lat = parseFloat(row.latitude);
          var lon = parseFloat(row.longitude);
          if (Number.isFinite(lat) && Number.isFinite(lon)) {
            points.push({ name: name, layer: layer, lon: lon, lat: lat, row: row });
          }
        });
        return;
      }
      var geoCol = dataset.columns.find(function (column) {
        return /geojson|geometry/i.test(column);
      }) || dataset.columns[0];
      rows.forEach(function (row) {
        var polygons = parseWktPolygons(row[geoCol]);
        polygons.forEach(function (polygon) {
          var coords = [];
          polygon.forEach(function (ring) { ring.forEach(function (pt) { coords.push(pt); }); });
          if (coords.length) features.push({ name: name, layer: layer, polygon: polygon, coords: coords });
        });
      });
    });

    var bounds = { minX: Infinity, minY: Infinity, maxX: -Infinity, maxY: -Infinity };
    features.forEach(function (feature) {
      feature.coords.forEach(function (pt) {
        if (pt[0] < bounds.minX) bounds.minX = pt[0];
        if (pt[1] < bounds.minY) bounds.minY = pt[1];
        if (pt[0] > bounds.maxX) bounds.maxX = pt[0];
        if (pt[1] > bounds.maxY) bounds.maxY = pt[1];
      });
    });
    points.forEach(function (point) {
      if (point.lon < bounds.minX) bounds.minX = point.lon;
      if (point.lat < bounds.minY) bounds.minY = point.lat;
      if (point.lon > bounds.maxX) bounds.maxX = point.lon;
      if (point.lat > bounds.maxY) bounds.maxY = point.lat;
    });
    if (!Number.isFinite(bounds.minX)) return;

    var width = Math.max(window.innerWidth, 1200);
    var height = Math.max(window.innerHeight, 800);
    var project = projectFactory(bounds, width, height);

    app.innerHTML = '';
    app.style.position = 'fixed';
    app.style.inset = '0';
    app.style.background = 'linear-gradient(180deg, #f8fafc 0%, #eef2ff 100%)';
    app.style.overflow = 'hidden';

    var svgNS = 'http://www.w3.org/2000/svg';
    var svg = document.createElementNS(svgNS, 'svg');
    svg.setAttribute('viewBox', '0 0 ' + width + ' ' + height);
    svg.setAttribute('width', '100%');
    svg.setAttribute('height', '100%');
    svg.setAttribute('preserveAspectRatio', 'xMidYMid slice');
    svg.style.position = 'absolute';
    svg.style.inset = '0';
    svg.style.pointerEvents = 'none';
    app.appendChild(svg);

    var defs = document.createElementNS(svgNS, 'defs');
    defs.innerHTML = '<filter id="shadow" x="-20%" y="-20%" width="140%" height="140%"><feDropShadow dx="0" dy="2" stdDeviation="3" flood-opacity="0.12"/></filter>';
    svg.appendChild(defs);

    var bg = document.createElementNS(svgNS, 'rect');
    bg.setAttribute('x', '0');
    bg.setAttribute('y', '0');
    bg.setAttribute('width', width);
    bg.setAttribute('height', height);
    bg.setAttribute('fill', '#f8fafc');
    svg.appendChild(bg);

    features.forEach(function (feature) {
      var path = document.createElementNS(svgNS, 'path');
      path.setAttribute('d', pathFromPolygon(feature.polygon, project));
      path.setAttribute('fill', feature.name === 'Population Density' ? 'rgba(192, 132, 252, 0.22)' : getColor(feature.layer, 'rgba(99, 102, 241, 0.18)'));
      path.setAttribute('stroke', feature.name === 'Population Density' ? 'rgba(126, 34, 206, 0.22)' : getColor(feature.layer, 'rgba(37, 99, 235, 0.8)'));
      path.setAttribute('stroke-width', feature.name === 'Population Density' ? '0.8' : '1.2');
      path.setAttribute('vector-effect', 'non-scaling-stroke');
      path.setAttribute('opacity', feature.name === 'Population Density' ? '0.9' : '0.95');
      svg.appendChild(path);
    });

    points.forEach(function (point) {
      var circle = document.createElementNS(svgNS, 'circle');
      var xy = project(point.lon, point.lat);
      circle.setAttribute('cx', xy[0].toFixed(2));
      circle.setAttribute('cy', xy[1].toFixed(2));
      circle.setAttribute('r', '5.5');
      circle.setAttribute('fill', getColor(point.layer, '#2563eb'));
      circle.setAttribute('stroke', '#ffffff');
      circle.setAttribute('stroke-width', '1.5');
      circle.setAttribute('vector-effect', 'non-scaling-stroke');
      svg.appendChild(circle);
    });

    var label = document.createElementNS(svgNS, 'g');
    label.setAttribute('filter', 'url(#shadow)');
    label.innerHTML = [
      '<rect x="22" y="22" rx="12" ry="12" width="350" height="64" fill="rgba(255,255,255,0.96)" stroke="rgba(15,23,42,0.08)"/>',
      '<text x="42" y="48" fill="#64748b" font-size="14" font-family="system-ui,-apple-system,sans-serif" letter-spacing=".08em">OFFLINE FALLBACK MAP</text>',
      '<text x="42" y="72" fill="#0f172a" font-size="20" font-weight="700" font-family="system-ui,-apple-system,sans-serif">Kepler dependencies unavailable locally</text>'
    ].join('');
    svg.appendChild(label);

    var notice = document.createElement('div');
    notice.style.cssText = 'position:fixed;left:22px;bottom:18px;z-index:9998;background:rgba(255,255,255,0.95);' +
      'color:#475569;padding:10px 14px;border-radius:10px;border:1px solid rgba(148,163,184,0.25);' +
      'font:13px/1.4 system-ui,-apple-system,sans-serif;max-width:320px;box-shadow:0 6px 24px rgba(15,23,42,0.08)';
    notice.textContent = 'Showing a local offline fallback because CDN-hosted Kepler assets are not reachable in this environment.';
    app.appendChild(notice);
  }

  ready(function () {
    setTimeout(render, 400);
  });
})();
