# MA Bikeshare Coverage Analysis

Estimates the percentage of Massachusetts residents living within a 10-minute walk (~800m) of a docked bikeshare station, for inclusion in a Massachusetts DOT report.

---

## Data Sources

- **BTS National Transit Database — Bikeshare Stations**: CSV of station-level data from the Bureau of Transportation Statistics. Covers most MA systems through 2022–2023, with gaps noted below.
- **US Census TIGER/Line Shapefiles**: Block group geometries retrieved via the Census TIGER API.
- **ACS 5-Year Estimates (Table B01003)**: Block group population counts from the American Community Survey.
- **ValleyBike (manual)**: Current station list compiled manually; BTS data for ValleyBike is end-dated 2022 (system shutdown) and the reopened system under a new vendor is not yet in BTS.
- **Port Bikeshare (manual)**: Not present in BTS dataset; stations compiled from operator sources.
- **MetroMobility (manual)**: Not present in BTS dataset; stations compiled from operator sources.

---

## Limitations

- Euclidean (straight-line) 800m buffers are used as a proxy for a 10-minute walkshed. True pedestrian access areas require street-network routing (e.g., OSMnx isochrones) and would likely produce smaller, more accurate coverage polygons.
- Station data for Port Bikeshare and MetroMobility is manually compiled and may be incomplete or out of date.
- Areal interpolation assumes uniform population distribution within each Census block group, which introduces error in areas with uneven development patterns.
- BlueBikes station data is taken as accurate; no independent verification of station status (active/inactive) was performed.
- Analysis reflects a point-in-time snapshot and does not account for seasonal station removals or expansions.
