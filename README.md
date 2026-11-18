# Salmon Lines

[Open Salmon Lines](https://coolcode.ca/salmonlines/) · [CoolCode](https://coolcode.ca/)

Explore Fisheries and Oceans Canada’s Pacific salmon spawning records by waterbody, species, subdistrict, population and run. Compare two same-species populations on a common time axis, read annual estimates, adult presence and enumeration methods, export the displayed years, or share a view. Nearby comparisons prioritize the same DFO subdistrict. Yorkson Creek links to its mapped channel in Hidden Water.

## Source and coverage

The [NuSEDS catalogue](https://open.canada.ca/data/en/dataset/c48669a3-045b-400d-b730-48aafe8c5ee6) publishes a simplified all-areas CSV and an English data dictionary. The June 1, 2026 edition contains 421,001 annual records spanning 1920–2025, including BC, Yukon and transboundary waters. The full index includes 9,886 populations and 9,964 distinct population/waterbody series. See the live source panel and [snapshot metadata](snapshot/source.json) for the edition, exact resource, retrieval date, and source SHA-256. The site build date is displayed independently. Contains information licensed under the [Open Government Licence – Canada](https://open.canada.ca/en/open-government-licence-canada).

Each series retains its DFO population and geographic feature IDs. Different sites, runs and measures stay separate. Adult natural spawners, total natural spawners, total returns to river and unspecified historical returns are selectable. No field is substituted for another. Survey effort and reporting methods vary. Annual analysis years refer to the season assigned by DFO. Blank source values, missing years and reported numeric zeros are distinct in the table and export. Inspections reporting no adults do not imply a numerical estimate of zero.

## Build and refresh

Python and Node are required for development. Visitors need only a browser. Searches, charting, comparisons and CSV exports run locally using same-origin static files. A shared URL includes the selected populations, measure and time period.

```sh
node --test tests/*.test.mjs
python3 -m unittest discover -s tests -v
python3 scripts/build.py
python3 -m http.server 8000 --directory dist
```

The offline build expands the checked-in compressed snapshot. The browser downloads its index and the relevant history shards on demand. CI also runs the desktop/mobile Chromium tests in `tests/browser_smoke.py`.

`python3 scripts/refresh.py` locates the latest dated all-areas simplified CSV in the government catalogue, checks its digest and validates its schema, identities and historical coverage before replacing the snapshot. A monthly workflow checks for new or corrected source editions. Use **Actions → Browser tool · Check and publish → Run workflow**, on main with the refresh checkbox, for an extra check. Validated refreshes are recorded in Git; the checked and browser-tested build deploys to GitHub Pages. Set repository Pages source to **GitHub Actions**.
