# MA Bikeshare Coverage Analysis

**How many Massachusetts residents live within a 10-minute walk of a docked bikeshare station?**

This micro visualization project answers this question posed by the Lab @ MassDOT, seeking to understand how many Massachusetts residents are within a reasonable walking distance to a bikeshare station. The resulting map visualizes all seven bikeshare systems operating in Massachusetts — docked systems plus a small number of fixed-location geofenced systems — draws a 10 minute walkingshed around each station, and estimates how many residents fall within it using most recent 2023 American Community Survey Census population data. The map also includes a demographic lens showing coverage for residents aged 50 and older. This inquiry is helpful as a preliminary analysis of mobility equity in Massachusetts because it brings independent bikeshare data into a single source, uses most recent operator data (as of June 2026), and reveals state-wide bikeshare gaps.


**[View the interactive map →](https://oouadani1.github.io/ma-bikeshare-coverage/data/processed/bikeshare_coverage_map.html)**

---

## Key Finding

**About 20% of Massachusetts residents — roughly 1.4 million people — live within a 10-minute walk (~800m) of a docked bikeshare station.**

Among residents aged 50 and older, approximately 15% — roughly 337,000 people — live within walking distance of a station.

---

## Systems Mapped

| System | Operator | Geography |
|---|---|---|
| BlueBikes | Motivate / Lyft | Greater Boston area, 13 municipalities |
| ValleyBike | Pioneer Valley Planning Commission | Pioneer Valley (Springfield, Northampton, Amherst area) |
| Port Bikeshare | Tandem Mobility | Newburyport |
| MetroMobility | MetroMobility | Greater Boston (Somerville, Cambridge, Boston, Lawrence, Lowell, Worcester, and others) |
| Minuteman Bikeshare | Minuteman Advisory Group | Concord / Acton area |
| Coast Provincetown | Coast | Provincetown & North Truro |
| CargoB | CargoB | Greater Boston (Back Bay, Cambridge, Somerville, Allston/Brighton, Jamaica Plain, Roslindale, Arlington) |

> **Note on dockless systems:** Sandy Pedals (Nantucket Island) is a dockless bike and scooter service and is not included in the coverage count — see Limitations. It is marked on the map for awareness.

> **Note on geofenced systems:** Coast Provincetown and CargoB are not docked systems in the traditional sense — they use geofenced pickup areas or bike parking corrals rather than fixed docks. We treat each mapped area's coordinates as a station location for this analysis, since the pickup zone itself is fixed in place. See Limitations.

---

## How It Works

1. **Station data** — Collected from each operator. All coordinates manually verified against operator maps and Google Street View. Stored in `data/raw/Master Bikeshare Station Data.xlsx`, one tab per system.

2. **Service area** — We draw an 800-meter straight-line circle around each station (roughly a 10-minute walk at an average pace of 80 meters per minute). All circles are merged into one combined shape.

3. **Population estimate** — We overlay the coverage shape with U.S. Census block group boundaries. For each block group, we calculate what share of its area falls inside the coverage shape, then apply that same share to its population count. This technique is called **areal interpolation** — it assumes people are spread roughly evenly within each block group, which is a reasonable approximation at this scale.

4. **Population data** — 2023 American Community Survey 5-year estimates (Table B01003), pulled via the free Census Reporter API.

---

## What's on the Map

- **Colored buffers** — Each system's combined coverage area, shaded in its brand color
- **Station dots** — Individual station locations, colored by system
- **Background layer** — Census block groups shaded by population density (people per km²)
- **Info panel** — Summary stats, system legend, and a walking-distance sensitivity slider (1–10 minutes)
- **Demographic toggle** — Switch between all residents and the age 50+ population to see how bikeshare coverage varies by group; the map recolors and the coverage stat updates accordingly
- **Nantucket outline** — Marks the Sandy Pedals dockless service area on the map (not included in the coverage count; see Limitations)

---

## Limitations & Assumptions

- **Straight-line distances overestimate real walkability.** An 800m radius assumes you can walk in a straight line to a station. In practice, streets, buildings, and other barriers make the actual walking route longer. A street-network walkshed analysis (using real route distances) would produce a smaller, more accurate coverage area. This is planned as a next step.

- **ValleyBike data is pending an update.** The ValleyBike figures are based on 2025 hub data while we wait for a refreshed operator dataset. Some hubs are geofenced "drop zones" rather than traditional fixed docks; these are included in the count, which may slightly overstate docked-station coverage for the Pioneer Valley.

- **Coast Provincetown and CargoB use geofenced areas, not fixed docks.** Neither system uses traditional docking hardware. Coast relies on geofenced parking areas at partner locations; CargoB uses designated bike parking corrals. For this analysis, we treat each mapped area's coordinates as a station location, since the pickup zone itself is fixed in place — this is consistent with how the 800-meter walkshed model works and is considered sufficient for this scale of analysis.

- **Population is assumed to be evenly distributed within each block group.** This is a standard simplification used in spatial analysis. It introduces some error in areas with uneven development patterns (e.g., a dense downtown and a park in the same block group).

- **This is a snapshot in time.** Station locations and counts change seasonally and as systems expand. The analysis reflects the station data and population estimates as of mid-2026.

- **Walking speed assumption.** The 10-minute threshold assumes 80 meters per minute (~3 mph). Slower walkers, people with mobility limitations, or routes with hills would have smaller effective service areas.

- **Dockless systems are not counted.** Sandy Pedals, a dockless bike and scooter service on Nantucket Island, is excluded from the coverage analysis because it has no fixed stations and the 800-meter walkshed model does not apply. If the entire island were treated as a single service area, it would add roughly 14,000 year-round residents — less than 0.2 percentage points at the statewide level. It is listed on the map as a resource for bikeshare awareness across the state.

---

## How to Update

All tunable parameters live in `config.py`. To refresh any part of the analysis:

| Goal | Action |
|---|---|
| Add or correct station data | Edit the relevant tab in `Master Bikeshare Station Data.xlsx`, delete `data/processed/stations_combined.geojson`, re-run |
| Change walking distance threshold | Edit `BUFFER_METERS` in `config.py`, delete buffer caches, re-run |
| Change a system's color on the map | Edit `SYSTEM_COLORS` in `config.py`, re-run Section 5 |
| Update to newer Census data | Bump `ACS_YEAR` and `TIGER_URL` in `config.py`, delete block group caches, re-run |
| Force full re-run | Delete all files in `data/processed/`, re-run the notebook |

---

## Files

```
config.py                          All parameters — the only file you need to edit
analysis.ipynb                     Analysis notebook — runs from start to finish
data/raw/
  Master Bikeshare Station Data.xlsx   Station data, one tab per system
data/processed/
  bikeshare_coverage_map.html      Standalone interactive map (hosted on GitHub Pages)
  results.json                     Machine-readable summary of key figures
```
