# SFUSD admission odds

A single-page lookup of how applicants fared in the SFUSD 2026–27 main round and waitlist, for every school,
program and grade, plus a map of SFUSD and charter schools with GreatSchools ratings.

Live page (once GitHub Pages is on): https://joyceyan.github.io/sfusd/

## Files

- `index.html` — the built page. GitHub Pages serves this from the repo root. Do not edit it by hand.
- `artifact.html` — the same page as a fragment, for publishing as a Claude artifact.
- `template.html` — the page's markup, styles and script, with `__DATA__`-style placeholders.
- `build.py` — joins the data and fills the template. No dependencies beyond Python 3.
- `fetch.sh` — re-downloads the source data.
- `data/main-round.csv`, `data/waitlist.csv` — exports of the two SFUSD Google Sheets.
- `geo/greatschools-*.json` — school locations and ratings from GreatSchools' San Francisco listings.
- `geo/charter-info.json` — charter admissions details, researched by hand in November 2026.
- `geo/neighborhoods.geojson` — DataSF analysis neighborhoods, used as the basemap.

## Updating

```sh
./fetch.sh        # optional: refresh the sheets, ratings and outlines
python3 build.py  # rebuild index.html and artifact.html
```

`build.py` prints any school it cannot match to GreatSchools. Name overrides and the few hand-placed
locations are at the top of the matching section.

## How the numbers are computed

- Combined odds = main-round success + (1 − main-round success) × waitlist odds.
- Main-round rates exclude sibling applicants: (all − sibling) successes ÷ (all − sibling) requests. Siblings are placed almost every time.
- Waitlist odds = offers made so far ÷ current waitlist length, capped at 100%. No waitlist row means nobody is waiting.
- A program counts as neighborhood-based when the sheet shows attendance-area applicants for it; everything else is city-wide.
- Special education (SDC) programs and Access SFUSD sites are excluded.
