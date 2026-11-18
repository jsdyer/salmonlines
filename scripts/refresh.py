"""Prepare DFO NuSEDS population/site time series from its simplified all-areas CSV."""
import argparse
import csv
import gzip
import hashlib
import json
import math
from datetime import datetime, timezone
from pathlib import Path
import re
import tempfile
from urllib.parse import unquote, urlsplit
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[1]
DATASET = "c48669a3-045b-400d-b730-48aafe8c5ee6"
API = f"https://open.canada.ca/data/api/action/package_show?id={DATASET}"
MEASURES = ["NATURAL_ADULT_SPAWNERS", "NATURAL_SPAWNERS_TOTAL", "TOTAL_RETURN_TO_RIVER", "UNSPECIFIED_RETURNS"]
REQUIRED = {"POP_ID", "GFE_ID", "ANALYSIS_YR", "SPECIES", "AREA", "POPULATION", "WATERBODY", "RUN_TYPE", "ADULT_PRESENCE", "ENUMERATION_METHODS", *MEASURES}
SHARDS = 16

def download(url):
    return urlopen(Request(url, headers={"User-Agent": "CoolCode Salmon Lines open-data importer"}), timeout=120)

def current_resource():
    with download(API) as response:
        package = json.load(response)["result"]
    matches = []
    for resource in package["resources"]:
        name = unquote(urlsplit(resource["url"]).path).rsplit("/", 1)[-1]
        date = re.fullmatch(r"All Areas Simplified Version_(\d{8})\.csv", name, re.I)
        if date:
            matches.append((date[1], resource))
    if not matches:
        raise ValueError("DFO's simplified CSV was not found in the catalogue")
    date, resource = max(matches, key=lambda item: item[0])
    return resource["url"], datetime.strptime(date, "%Y%m%d").date().isoformat()

def estimate(value):
    if not value.strip():
        return None
    number = float(value)
    if not math.isfinite(number) or number < 0:
        raise ValueError(f"Unexpected estimate {value!r}")
    return int(number) if number.is_integer() else number

def transform(rows):
    index, series, presence_codes, method_codes, years = {}, {}, {}, {}, []
    seen = set()
    for row in rows:
        pop, site = row["POP_ID"], row["GFE_ID"]
        if not pop.isdecimal() or not site.isdecimal():
            raise ValueError("Missing numeric population or waterbody ID")
        key = f"{pop}-{site}"
        year = int(row["ANALYSIS_YR"])
        if (key, year) in seen:
            raise ValueError(f"Multiple estimates for {key} in {year}. Review before publishing.")
        seen.add((key, year))
        years.append(year)
        identity = [row[k].strip() for k in ("POPULATION", "WATERBODY", "SPECIES", "AREA", "RUN_TYPE")]
        if key not in index:
            index[key] = [key, *identity]
            series[key] = []
        if index[key][1:] != identity:
            raise ValueError(f"Population/site metadata conflicts for {key}")
        presence = row["ADULT_PRESENCE"].strip()
        method = row["ENUMERATION_METHODS"].strip()
        observation = [year, *[estimate(row[k]) for k in MEASURES],
                       presence_codes.setdefault(presence, len(presence_codes)),
                       method_codes.setdefault(method, len(method_codes))]
        series[key].append(observation)
    for history in series.values():
        history.sort(key=lambda row: row[0])
    ref = {"presence": list(presence_codes), "methods": list(method_codes),
           "rows": len(seen), "series": len(index), "populations": len({key.split("-")[0] for key in index}),
           "years": [min(years), max(years)], "shards": SHARDS}
    return sorted(index.values(), key=lambda item: (item[1], item[2], item[0])), series, ref

def pack(path, obj):
    raw = (json.dumps(obj, ensure_ascii=False, separators=(",", ":")) + "\n").encode()
    path.write_bytes(gzip.compress(raw, compresslevel=7, mtime=0))

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--csv", type=Path, help="Use a local copy of the current DFO resource")
    args = parser.parse_args()
    url, release = current_resource()
    target = ROOT / "snapshot"
    target.mkdir(exist_ok=True)
    with tempfile.TemporaryDirectory(dir=target.parent) as tmp:
        work = Path(tmp)
        file = args.csv or work / "dfo.csv"
        if not args.csv:
            import shutil
            with download(url) as response, file.open("wb") as stream:
                shutil.copyfileobj(response, stream)
        digest = hashlib.sha256(file.read_bytes()).hexdigest()
        manifest = target / "source.json"
        old = json.loads(manifest.read_text()) if manifest.exists() else {}
        if digest == old.get("sha256") and release == old.get("edition"):
            print("Source unchanged")
            return
        with file.open(encoding="cp1252", newline="") as stream:
            rows = csv.DictReader(stream)
            if not REQUIRED <= set(rows.fieldnames or []):
                raise ValueError("DFO source schema changed")
            index, series, ref = transform(rows)
        if ref["rows"] < max(300000, old.get("rows", 0) * 0.95) or ref["series"] < 8000:
            raise ValueError("Unexpected loss of historical records or populations")
        ref.update(edition=release, retrieved=datetime.now(timezone.utc).date().isoformat(),
                   url=url, sha256=digest, measures=MEASURES)
        pack(work / "index.json.gz", index)
        buckets = [{} for _ in range(SHARDS)]
        for key, values in series.items():
            buckets[int(key.split("-")[0]) % SHARDS][key] = values
        for i, bucket in enumerate(buckets):
            pack(work / f"observations-{i}.json.gz", bucket)
        (work / "source.json").write_text(json.dumps(ref, ensure_ascii=False, indent=2) + "\n")
        for artifact in [*work.glob("*.json.gz"), work / "source.json"]:
            artifact.replace(target / artifact.name)
        print(f"{ref['rows']:,} annual records, {ref['series']:,} population/site series, {ref['years']}")
if __name__ == "__main__":
    main()
