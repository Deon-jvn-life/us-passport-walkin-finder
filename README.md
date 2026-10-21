# South Florida Passport Places (static site)

Plain-HTML guide to U.S. passport acceptance facilities in Miami-Dade, Broward and Palm Beach counties, with walk-in vs appointment hours, plus official fees, forms, documents, photo rules and processing times.

- `tools/sofla_facilities.json`: raw records for the 3 counties, filtered from the official locator data file https://passportfacilitylocator.travel.state.gov/data/Facilities.json (county assigned by ZIP using the Census 2020 ZCTA to county relationship file).
- `tools/official_pages.json`: facts from clerk and library pages used to cross-check the locator.
- `tools/build.py`: generator. Run `python3 tools/build.py` from the repo root; output goes to `site/`. Also writes `tools/facilities_parsed.json`.
- Hours string decoding follows the locator's own front-end code: days 0=Monday to 6=Sunday; flag 0 = walk-in, 1/3 = "By Appointment", 2 = not counted as walk-in.
- `vercel.json`: static, no build. Set `BASE` in build.py to the real domain before deploying (used in canonical, robots and sitemap).

Last checked: 21 October 2026. No expediter promotions. Not affiliated with the U.S. Department of State.
