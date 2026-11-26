"""Publish one dated profile per evidence-rich DFO population and geographic feature."""
from collections import defaultdict
from html import escape
import json
from pathlib import Path
import re
from urllib.parse import urlencode
from xml.etree import ElementTree as ET

MIN_YEARS = 10
MEASURES = (
    ("adult", "Natural adult spawners", "The estimate covers adults spawning naturally. DFO records early-maturing jacks separately."),
    ("natural", "Total natural spawners", "This measure includes naturally spawning adults and jacks."),
    ("river", "Total return to river", "This broader freshwater estimate can include natural spawners, hatchery broodstock, other removals and unspecified returns."),
    ("legacy", "Unspecified returns", "DFO’s historical returns measure has an uncertain age group or accounting basis."),
)
CATALOGUE = "https://open.canada.ca/data/en/dataset/c48669a3-045b-400d-b730-48aafe8c5ee6"
LICENCE = "https://open.canada.ca/en/open-government-licence-canada"


def link(href, text):
    return f'<a href="{escape(href, quote=True)}">{escape(text)}</a>'


def number(value):
    if value is None:
        return "No estimate"
    return f"{value:,.3f}".rstrip("0").rstrip(".")


def metrics_for(rows):
    if len({r[0] for r in rows}) != len(rows):
        raise ValueError("Multiple observations for one population, waterbody and analysis year")
    return {position: [r for r in rows if r[position] is not None]
            for position in range(1, len(MEASURES) + 1)}


def main_measure(series):
    eligible = [pos for pos, rows in series.items() if len(rows) >= MIN_YEARS]
    # A shared latest year favours the more specific measure, in the published display order.
    return max(eligible, key=lambda pos: (series[pos][-1][0], -pos), default=None)


def explorer(app, identity, metric):
    return app + "#" + urlencode({"series": identity, "measure": MEASURES[metric - 1][0], "period": "all"})


def write_page(stage, path, title, intro, body, breadcrumbs, app):
    target = stage.joinpath(*path.split("/"))
    target.mkdir(parents=True, exist_ok=False)
    relative = "../" * len(Path(path).parts)
    url = "https://coolcode.ca" + app + path + "/"
    nav = " · ".join(link(href, label) for href, label in breadcrumbs)
    markup = f'''<!doctype html><html lang="en-CA"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{escape(title)} · Salmon Lines</title><meta name="description" content="{escape(intro, quote=True)}">
<link rel="canonical" href="{escape(url, quote=True)}"><link rel="stylesheet" href="{relative}style.css">
<link rel="icon" href="{relative}icon.svg"></head><body class="profile-page">
<a class="skip" href="#main">Skip to results</a><header><a href="/">CoolCode.ca</a><nav>{nav}</nav></header>
<main id="main"><h1>{escape(title)}</h1><p class="profile-intro">{escape(intro)}</p>{body}</main></body></html>'''
    (target / "index.html").write_text(markup, encoding="utf-8")
    return url


def species_path(species):
    part = re.sub(r"[^a-z0-9]+", "-", species.lower()).strip("-")
    if not part or part[0].isdigit():
        raise ValueError(f"Invalid species URL for {species!r}")
    return "series/" + part


def profile_body(item, rows, series, pos, source, app, siblings):
    identity, name, water, species, area, run = item
    population, feature = identity.split("-")
    _, label, definition = MEASURES[pos - 1]
    observed = series[pos]
    previous, latest = observed[-2:]
    intro = (f"DFO estimated {number(latest[pos])} fish in {latest[0]} and {number(previous[pos])} in {previous[0]} "
             f"for {name} using its {label.lower()} measure.")
    body = '<p>' + link(explorer(app, identity, pos), f"Open the {label.lower()} series in Salmon Lines") + '</p>'
    body += (f'<p>{escape(definition)} DFO recorded a numerical estimate in {len(observed)} seasons from '
             f'{observed[0][0]} to {latest[0]} on this measure.</p>')
    method = source["methods"][latest[6]]
    if method:
        body += f'<p>DFO recorded “{escape(method)}” as the enumeration method for {latest[0]}.</p>'
    last_observation = rows[-1]
    if last_observation[0] != latest[0]:
        body += (f'<p>The most recent survey row is for {last_observation[0]}. It has no numerical estimate '
                 'for this measure.</p>')

    # Show recent actual records, retaining the two comparison years if recent observations have gaps.
    selected_years = {r[0] for r in rows[-8:]} | {latest[0], previous[0]}
    cells = []
    for row in reversed(rows):
        if row[0] not in selected_years:
            continue
        presence = source["presence"][row[5]] or "Unreported"
        method = source["methods"][row[6]] or "Unreported"
        cells.append(f'<tr><th scope="row">{row[0]}</th><td>{number(row[pos])}</td>'
                     f'<td>{escape(presence.capitalize())}</td><td>{escape(method)}</td></tr>')
    body += ('<h2>Survey observations</h2><div class="table-wrap"><table><caption>' + escape(label)
             + ', estimated fish by DFO analysis year</caption><thead><tr><th scope="col">Year</th>'
             '<th scope="col">Estimate</th><th scope="col">Adult presence</th>'
             '<th scope="col">Enumeration method</th></tr></thead><tbody>' + ''.join(cells) + '</tbody></table></div>'
             '<p>“No estimate” marks a blank measurement. A zero is shown only when DFO reported a numerical zero.</p>')
    other = []
    for alt, values in series.items():
        if alt == pos or not values:
            continue
        last = values[-1]
        other.append('<li>' + link(explorer(app, identity, alt), MEASURES[alt - 1][1])
                     + f' — {number(last[alt])} fish in {last[0]}.</li>')
    if other:
        body += '<h2>Other published measures</h2><ul>' + ''.join(other) + '</ul>'
    body += (f'<h2>Population and source</h2><p>DFO population {population}, waterbody feature {feature} '
             f'({escape(water)}), subdistrict {escape(area or "unreported")}.')
    if run:
        body += ' DFO identifies the run as ' + escape(run) + '.'
    retrieved = source.get("retrieved")
    timing = f"Retrieved {escape(retrieved)}." if retrieved else "Retrieval date unrecorded."
    body += (f' Survey rows span {rows[0][0]}–{rows[-1][0]}.</p><p>DFO NuSEDS edition {escape(source["edition"])}. '
             + timing + ' Survey methods and effort may vary between seasons.</p><p>'
             + link(CATALOGUE, "DFO catalogue and data dictionary") + ' · '
             + link(source["url"], "Original DFO all-areas CSV") + ' · '
             + link(LICENCE, "Open Government Licence – Canada") + '</p>')
    local_links = []
    if identity == "46982-62":
        note = (" The DFO series ends before the 2016 repair." if rows[-1][0] < 2016 else "")
        local_links.append(link("/hiddenwater/#crossing-1474", "Bench Road fish-passage repair in the Chilliwack watershed")
                           + " — the provincial record describes a specific crossing." + note)
    if water == "YORKSON CREEK" and area == "29B":
        local_links.append(link("/hiddenwater/#record=channels%3A9c7edd00-c189-44a7-a478-6b6c93f79ddf",
                                "Mapped Yorkson Creek channel in Hidden Water"))
    if local_links:
        body += '<h2>Watershed records</h2><ul>' + ''.join('<li>' + x + '</li>' for x in local_links) + '</ul>'
    related = [x for x in siblings if x[0] != identity]
    if related:
        body += ('<h2>Other DFO populations at this waterbody feature</h2><ul>'
                 + ''.join('<li>' + link('../' + x[0] + '/', x[1] + ' · ' + x[0]) + '</li>' for x in related)
                 + '</ul>')
    return intro, body


def publish_profiles(stage, tool, source):
    app = tool["url"]
    data = stage / "data"
    index = json.loads((data / "index.json").read_text())
    records = {}
    eligible = {}
    by_feature = defaultdict(list)
    by_species = defaultdict(list)
    for shard in range(source["shards"]):
        for identity, rows in json.loads((data / f"observations-{shard}.json").read_text()).items():
            values = metrics_for(rows)
            position = main_measure(values)
            if position is not None:
                records[identity] = (rows, values, position)
    for item in index:
        identity = item[0]
        if identity not in records:
            continue
        if not re.fullmatch(r"[0-9]+-[0-9]+", identity) or identity in eligible:
            raise ValueError("Invalid or duplicate population/waterbody identifier")
        eligible[identity] = item
        by_feature[identity.split("-")[1]].append(item)
        by_species[item[3]].append(item)
    if not eligible or len(eligible) != len(records):
        raise ValueError("Missing profile data or population index entries")

    # Let the explorer offer the return link using the index it already loads.
    browser_index = [[*item, item[0] in eligible] for item in index]
    (data / "index.json").write_text(json.dumps(browser_index, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")

    directory = "series"
    nav_root = [(app, "Salmon Lines explorer")]
    nav_directory = [*nav_root, (app + directory + "/", "Population profiles")]
    listing = '<ul>' + ''.join('<li>' + link('./' + species_path(sp).split('/')[1] + '/', f"{sp} · {len(items):,}") + '</li>'
                               for sp, items in sorted(by_species.items())) + '</ul>'
    intro = (f"Browse {len(eligible):,} Pacific Region salmon and steelhead population records with numerical "
             f"estimates for at least {MIN_YEARS} distinct survey years on one DFO measure.")
    urls = [write_page(stage, directory, "Salmon population profiles by species", intro, listing, nav_root, app)]
    for species, items in sorted(by_species.items()):
        axis = defaultdict(list)
        for item in sorted(items, key=lambda x: (x[1].casefold(), x[0])):
            name = item[1]
            first = name[0].upper()
            letter = first if first.isascii() and first.isalpha() else "Other"
            axis[letter].append('<li>' + link('../' + item[0] + '/', name + ' · ' + item[0]) + '</li>')
        body = '<nav aria-label="Jump to population names">' + ' · '.join(link('#letter-' + key, key) for key in axis) + '</nav>'
        for key, entries in axis.items():
            body += f'<h2 id="letter-{key}">{key}</h2><ul>' + ''.join(entries) + '</ul>'
        title = species + " population profiles by river and run"
        intro = (f"{len(items):,} population and waterbody records for {species.lower()}, listed by DFO population name and identifier."
                 if len(items) > 1 else f"One {species.lower()} population and waterbody record meets the ten-year threshold.")
        urls.append(write_page(stage, species_path(species), title, intro, body, nav_directory, app))
    for identity, item in eligible.items():
        rows, values, position = records[identity]
        intro, body = profile_body(item, rows, values, position, source, app, by_feature[identity.split("-")[1]])
        title = item[1] + " estimates · " + identity
        nav = [*nav_directory, ('../' + species_path(item[3]).split('/')[1] + '/', item[3] + ' populations')]
        urls.append(write_page(stage, directory + '/' + identity, title, intro, body, nav, app))
    sitemap = ET.Element("urlset", xmlns="http://www.sitemaps.org/schemas/sitemap/0.9")
    for url in urls:
        ET.SubElement(ET.SubElement(sitemap, "url"), "loc").text = url
    ET.indent(sitemap)
    ET.ElementTree(sitemap).write(stage / "sitemap.xml", encoding="utf-8", xml_declaration=True)
