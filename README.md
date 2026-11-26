# Salmon Lines

[Open Salmon Lines](https://coolcode.ca/salmonlines/) · [CoolCode](https://coolcode.ca/)

Explore Fisheries and Oceans Canada’s Pacific salmon spawning records by waterbody, species, subdistrict, population and run. Compare two same-species populations on a common time axis, read annual estimates, adult presence and enumeration methods, export the displayed years, or share a view. Nearby comparisons prioritize the same DFO subdistrict. Yorkson Creek links to its mapped channel in Hidden Water.

<!-- coolcode:guide -->
Read the latest and preceding estimates for one river, population and measure. For Chilliwack River coho, compare the survey years with the Bench Road repair timeline.
<!-- /coolcode:guide -->

[Browse population profiles by species](https://coolcode.ca/salmonlines/series/) for population and waterbody pairs with numerical estimates in at least ten distinct analysis years on one DFO measure. Each profile shows the latest two qualifying estimates, dated survey rows, presence, recorded enumeration methods and links to the individual measures in the explorer. The headline uses the qualifying measure with the most recent estimate. Ties favour the narrower measure in explorer order. The build generates the profiles, directory and child sitemap from the checked-in edition.

The river reading updates with the selected populations, measure and years. For example, the June 2026 source edition puts the Adams River sockeye natural adult estimate at 354 in 2024 and 4,851 in 2023. Its total natural spawner estimate for 2024 is 1,373, which also includes jacks. A difference between seasons describes estimated abundance under one measure; assessing causes or population health requires more evidence.

## Chilliwack River and the Bench Road crossing

The Chilliwack River coho preset opens series 46982-62 with DFO’s unspecified historical returns measure. The latest year in the series is shown alongside the provincial crossing’s 2016 completion date. The published years in the current series end before the repair. A basin-wide population estimate and a crossing assessment answer different questions. The project report names cutthroat trout and lists coho among possible beneficiaries. Open [Hidden Water’s project timeline](https://coolcode.ca/hiddenwater/#crossing-1474) to inspect the four crossing records and the original report.

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

For a saved source supplied with `--csv`, use `--retrieved-on YYYY-MM-DD` when the original acquisition date is known. An unchanged local copy preserves the recorded date. A changed local copy with unknown provenance displays “Retrieval date unrecorded.”

<!-- schedule-reliability -->
## Schedule reliability

Public GitHub repositories can have scheduled workflows disabled after 60 days of inactivity. A separate weekly [schedule guard](.github/workflows/schedule-guard.yml) calls GitHub's enable-workflow API for an explicit list of refresh workflows and itself. It can restore workflows disabled for inactivity, preserves manually disabled workflows, and runs independently of collection failures.

This is an interim mitigation, not a scheduling guarantee: GitHub does not document active-workflow renewal as a permanent exemption, and scheduled runs can be delayed or dropped. A scheduler on our own Linux server is the planned independent trigger. The guard does not collect data, create dummy commits, or change source/check timestamps; successful collection and published data freshness still need monitoring.
<!-- /schedule-reliability -->

## Search metadata

The build emits a descriptive page title, canonical URL, social preview metadata and
static `WebApplication` JSON-LD for the free browser tool. The visible application
name stays unchanged. Edit the search title in `web/index.html`; application details
come from `tool.json`. No ratings or reviews are invented.

Dataset JSON-LD and the visible snapshot section use `snapshot/source.json`. `dateModified` is the DFO source edition, while the visible retrieval date remains separate. Rebuilding the page never relabels the old source edition as newly modified.
