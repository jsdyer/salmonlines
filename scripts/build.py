#!/usr/bin/env python3
"""Build a browser tool using Python's standard library; no network required."""
from datetime import datetime, timezone
import gzip
from html import escape
import json
from pathlib import Path
import re
import shutil
import tempfile
from urllib.parse import urlsplit

from search_metadata import add_search_metadata
from profiles import publish_profiles

ROOT = Path(__file__).resolve().parents[1]
SLUG = re.compile(r"[a-z0-9]+(?:-[a-z0-9]+)*")


def metadata(root=ROOT):
    tool = json.loads((root / "tool.json").read_text(encoding="utf-8"))
    required = {"id", "title", "description", "category", "tags", "icon", "url", "source", "hosting", "access"}
    if not isinstance(tool, dict) or not required <= set(tool) <= required | {"data_info"}:
        raise ValueError("tool.json has missing or unknown fields")
    for key in required - {"tags"}:
        if not isinstance(tool[key], str) or not tool[key].strip():
            raise ValueError(f"tool.json: {key} must be a nonempty string")
    if not SLUG.fullmatch(tool["id"]) or tool["url"] != f'/{tool["id"]}/' or tool["hosting"] != "project":
        raise ValueError("Use a lowercase tool ID, matching /id/ URL and project hosting")
    if not isinstance(tool["tags"], list) or not all(isinstance(t, str) and t.strip() for t in tool["tags"]):
        raise ValueError("tags must be an array of nonempty strings")
    if tool["access"] != "browser":
        raise ValueError("This starter produces an immediately usable browser tool; use access: browser")
    source = urlsplit(tool["source"])
    if source.scheme != "https" or not source.hostname or source.username is not None or any(c.isspace() for c in tool["source"]) or "\\" in tool["source"]:
        raise ValueError("source must be an HTTPS URL without credentials or whitespace")
    return tool


def dataset_metadata(source, tool):
    url = "https://coolcode.ca" + tool["url"]
    return {
        "@type": "Dataset", "@id": url + "#dataset", "url": url,
        "name": "Pacific salmon escapement records from DFO NuSEDS",
        "description": f"{source['rows']:,} annual survey records for Pacific salmon populations, with coverage from {source['years'][0]} to {source['years'][1]}. Includes adult spawner and total return estimates, missing values, presence flags and survey methods.",
        "creator": {"@type": "Organization", "name": "Fisheries and Oceans Canada"},
        "publisher": {"@type": "Organization", "name": "CoolCode", "url": "https://coolcode.ca/"},
        "isBasedOn": "https://open.canada.ca/data/en/dataset/c48669a3-045b-400d-b730-48aafe8c5ee6",
        "license": "https://open.canada.ca/en/open-government-licence-canada",
        "spatialCoverage": "DFO Pacific Region, Canada",
        "temporalCoverage": f"{source['years'][0]}/{source['years'][1]}",
        "dateModified": source["edition"],
        "distribution": [{"@type": "DataDownload", "name": "NuSEDS source CSV",
                          "contentUrl": source["url"], "encodingFormat": "text/csv"}],
    }


def build(root=ROOT):
    tool = metadata(root)
    output = root / "dist"
    if output.is_symlink():
        raise ValueError("dist must not be a symlink")
    web = root / "web"
    if web.is_symlink() or any(p.is_symlink() for p in web.rglob("*")):
        raise ValueError("web/ must not contain symlinks")
    with tempfile.TemporaryDirectory(prefix="coolcode-tool-") as temporary:
        stage = Path(temporary) / "site"
        shutil.copytree(web, stage)
        snapshot = root / "snapshot"
        data = stage / "data"
        data.mkdir()
        source = json.loads((snapshot / "source.json").read_text())
        (data / "source.json").write_text(json.dumps(dict(source, build_date=datetime.now(timezone.utc).date().isoformat())))
        label = "Data retrieved · " + escape(source["retrieved"]) if source.get("retrieved") else "Retrieval date unrecorded"
        (stage / "data-date.svg").write_text(
            f'<svg xmlns="http://www.w3.org/2000/svg" width="181" height="23" role="img" aria-label="{label}">'
            f'<title>{label}</title><rect width="181" height="23" rx="5" fill="#e8ede2"/>'
            f'<text x="8" y="16" font-family="system-ui,sans-serif" font-size="12" fill="#184940">{label}</text></svg>'
        )
        files = ["index.json", *(f"observations-{i}.json" for i in range(source["shards"]))]
        for name in files:
            with gzip.open(snapshot / (name + ".gz"), "rb") as packed, (data / name).open("wb") as unpacked:
                shutil.copyfileobj(packed, unpacked)
        publish_profiles(stage, tool, source)
        index = stage / "index.html"
        page = index.read_text(encoding="utf-8")
        for token, key in {"TITLE": "title", "DESCRIPTION": "description", "TOOL_ID": "id", "SOURCE_URL": "source"}.items():
            placeholder = "{{" + token + "}}"
            if placeholder not in page:
                raise ValueError(f"Missing template placeholder: {placeholder}")
            page = page.replace(placeholder, escape(tool[key], quote=True))
        if re.search(r"\{\{[A-Z_]+\}\}", page):
            raise ValueError("Unresolved template placeholder in web/index.html")
        dataset = dataset_metadata(source, tool)
        retrieval = f'Retrieved {escape(source["retrieved"])}.' if source.get("retrieved") else "Retrieval date unrecorded."
        summary = (f'<section id="dataset"><h2>Dataset snapshot</h2><p>{escape(dataset["description"])}</p>'
                   f'<p>Source edition {escape(source["edition"])}. {retrieval} '
                   'A new retrieval does not mean the source edition changed.</p>'
                   f'<p><a href="{escape(source["url"], quote=True)}">Download the DFO NuSEDS source CSV</a> · '
                   '<a href="./data/source.json">Read the snapshot provenance and checksum</a></p></section>')
        page = page.replace("<!-- DATASET_SUMMARY -->", summary)
        page = add_search_metadata(page, tool, category="ReferenceApplication", datasets=[dataset])
        index.write_text(page, encoding="utf-8")
        (stage / ".nojekyll").touch()
        if output.exists():
            shutil.rmtree(output)
        shutil.copytree(stage, output)
    print(f'Built dist/ for {tool["id"]}')


if __name__ == "__main__":
    try:
        build()
    except (OSError, ValueError) as exc:
        raise SystemExit(f"Build failed: {exc}")
