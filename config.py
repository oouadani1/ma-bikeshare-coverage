"""
Centralized configuration for the MA Bikeshare Coverage analysis.

Change any value here and re-run analysis.ipynb — results and map update automatically.
No need to touch the notebook code.

Sensitive values (API keys, tokens) live in .env — never commit that file.
"""
import os
from dotenv import load_dotenv
load_dotenv()   # loads .env into os.environ if present

# ── Distance / methodology ─────────────────────────────────────────────────────
BUFFER_METERS   = 800     # 800m ≈ 10-minute walk at 80 m/min; change to test sensitivity
WALK_SPEED_KPH  = 4.8     # used for OSMnx network analysis (not yet active)
WALK_MINUTES    = 10      # used for OSMnx network analysis

# ── Coordinate reference systems ───────────────────────────────────────────────
MA_CRS  = 'EPSG:26986'   # MA State Plane (meters) — all distance/area math
WGS84   = 'EPSG:4326'    # Geographic lat/lon — source data + KeplerGL output

# ── Census vintage ─────────────────────────────────────────────────────────────
# Bump ACS_YEAR when a newer 5-year estimate is available.
# Also update TIGER_URL to the matching shapefile year.
ACS_YEAR        = 2023
TIGER_URL       = 'https://www2.census.gov/geo/tiger/GENZ2023/shp/cb_2023_25_bg_500k.zip'

# Population data source:
#   'census_reporter' — free, no key, uses Census Reporter API (default)
#   'census_api'      — official Census API; requires a free key from api.census.gov/data/key_signup.html
POPULATION_SOURCE = 'census_reporter'
CENSUS_API_KEY    = os.environ.get('CENSUS_API_KEY', '')   # set in .env

ACS_API_URL     = (
    'https://api.census.gov/data/{year}/acs/acs5'
    '?get=B01003_001E'
    '&for=block+group:*'
    '&in=state:25+county:*+tract:*'
    '&key={key}'
)
CENSUS_REPORTER_URL = 'https://api.censusreporter.org/1.0/data/show/latest?table_ids=B01003&geo_ids=150|04000US25'

# ── BlueBikes: seasonal filter ─────────────────────────────────────────────────
# Set to None  → include all stations (active + winter storage)
# Set to 'Year Round' → exclude winter-storage stations for a conservative estimate
BLUEBIKES_SEASONAL_FILTER = None   # options: None | 'Year Round'

# ── Data source ────────────────────────────────────────────────────────────────
# All station data now lives in one master Excel file, one tab per system.
MASTER_EXCEL = 'data/raw/Master Bikeshare Station Data.xlsx'

# ── System colors (brand hex codes) — edit here to update the map instantly ───
# Each key maps to a bikeshare system; value is the hex color for its dots and buffer.
SYSTEM_COLORS = {
    'bluebikes':      '#1B6FE4',  # BlueBikes blue
    'valleybike':     '#F7941D',  # ValleyBike orange
    'port_bikeshare': '#00BCD4',  # Port Bikeshare teal
    'metromobility':  '#9C27B0',  # MetroMobility purple
    'minuteman':      '#E53935',  # Minuteman Bikeshare red
}

# ── System display labels ──────────────────────────────────────────────────────
SYSTEM_LABELS = {
    'bluebikes':      'BlueBikes',
    'valleybike':     'ValleyBike',
    'port_bikeshare': 'Port Bikeshare',
    'metromobility':  'MetroMobility',
    'minuteman':      'Minuteman Bikeshare',
}

# ── Processed data cache paths ─────────────────────────────────────────────────
# These files are written on first run and re-used on subsequent runs.
# Delete them to force a refresh from source (e.g. after updating raw data).
CACHE_BLOCK_GROUPS      = 'data/processed/ma_block_groups.geojson'
CACHE_STATIONS          = 'data/processed/stations_combined.geojson'
CACHE_BUFFER            = 'data/processed/coverage_buffer.geojson'
CACHE_BG_COVERAGE       = 'data/processed/block_groups_with_coverage.geojson'
CACHE_MULTI_BUFFER      = 'data/processed/multi_buffer_coverage.json'

# ── Output paths ───────────────────────────────────────────────────────────────
OUT_MAP_HTML    = 'data/processed/bikeshare_coverage_map.html'

# ── KeplerGL map display settings ─────────────────────────────────────────────
KEPLER_HEIGHT   = 900
