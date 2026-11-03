"""Load a FEMA National Risk Index CSV (county or tract) into data/processed/hazards_nri_<level>.csv.

Download the county or census-tract table from https://hazards.fema.gov/nri/data-resources
into data/raw/, then:

    python scripts/load_nri.py data/raw/NRI_Table_Counties.zip --level county --version 1.20
    python scripts/load_nri.py data/raw/NRI_Table_CensusTracts_Colorado.csv --level tract --version 1.20

Field names follow the NRI data dictionary. The script reports any that are
missing so a renamed field in a new release doesn't fail silently.
"""
import argparse
import sys
import zipfile
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import PROCESSED  # noqa: E402

FIELDS = {
    "WFIR_RISKS": "wildfire_risk_score",
    "WFIR_RISKR": "wildfire_risk_rating",
    "WFIR_EALT": "wildfire_eal_usd",
    "RISK_SCORE": "composite_risk_score",
    "SOVI_SCORE": "social_vulnerability",
    "RESL_SCORE": "community_resilience",
}
GEOID = {"county": "STCOFIPS", "tract": "TRACTFIPS"}


def read_nri(path):
    path = Path(path)
    if path.suffix == ".zip":
        with zipfile.ZipFile(path) as z:
            name = [n for n in z.namelist() if n.lower().endswith(".csv") and "dictionary" not in n.lower()][0]
            with z.open(name) as f:
                return pd.read_csv(f, dtype=str)
    return pd.read_csv(path, dtype=str)


def transform(df, level, version):
    gcol = GEOID[level]
    if gcol not in df.columns:
        raise SystemExit(f"Expected geography column {gcol}; found {list(df.columns)[:10]}...")
    missing = [c for c in FIELDS if c not in df.columns]
    if missing:
        print(f"WARNING: fields not in this release: {missing}")
    width = 5 if level == "county" else 11
    out = pd.DataFrame({"geoid": df[gcol].str.zfill(width), "geo_level": level, "dataset_version": version})
    for src, dst in FIELDS.items():
        if src in df.columns:
            out[dst] = df[src] if dst.endswith("rating") else pd.to_numeric(df[src], errors="coerce")
    out["source_id"] = "SRC22"
    return out


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("path")
    ap.add_argument("--level", choices=["county", "tract"], required=True)
    ap.add_argument("--version", required=True, help="NRI release, e.g. 1.20")
    a = ap.parse_args()
    out = transform(read_nri(a.path), a.level, a.version)
    path = PROCESSED / f"hazards_nri_{a.level}.csv"
    out.to_csv(path, index=False)
    co = out[out.geoid.str.startswith("08")]
    print(f"Wrote {len(out)} rows -> {path} ({len(co)} in Colorado)")


if __name__ == "__main__":
    main()
