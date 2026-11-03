"""Compare factory database counts by state with CBP establishment counts.

    python scripts/completeness_check.py --year 2023

Writes output/completeness_<year>.csv, sorted by the largest shortfall, so
research time goes to the states where the database is most likely missing
factories.
"""
import argparse
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import OUTPUT, PROCESSED, load_states  # noqa: E402


def compare(master, cbp, naics="321992"):
    states = pd.DataFrame(load_states())[["state_fips", "state_abbr", "state_name"]]
    m = master[(master.status.fillna("active") == "active") & (master.residential.fillna("1") != "0")]
    m = m[m.code_basis.fillna("") != "HUD_CODE"]
    db = m.groupby("state_abbr").size().rename("db_factories").reset_index()
    c = cbp[cbp.naics_code == naics][["state_fips", "establishments"]].rename(
        columns={"establishments": f"cbp_{naics}"})
    out = states.merge(db, on="state_abbr", how="left").merge(c, on="state_fips", how="left").fillna(0)
    out["db_factories"] = out["db_factories"].astype(int)
    out[f"cbp_{naics}"] = out[f"cbp_{naics}"].astype(int)
    out["gap"] = out[f"cbp_{naics}"] - out["db_factories"]
    denom = out[f"cbp_{naics}"].where(out[f"cbp_{naics}"] > 0)
    out["coverage"] = (out["db_factories"] / denom).astype(float).round(2)
    out["flag"] = "ok"
    out.loc[out.gap >= 3, "flag"] = "likely missing factories"
    out.loc[(out[f"cbp_{naics}"] == 0) & (out.db_factories > 0), "flag"] = "db has factories CBP doesn't (check scope)"
    return out.sort_values("gap", ascending=False)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--year", type=int, default=2023)
    ap.add_argument("--naics", default="321992")
    a = ap.parse_args()
    master = pd.read_csv(PROCESSED / "plants_modular.csv", dtype=str)
    cbp = pd.read_csv(PROCESSED / f"cbp_establishments_{a.year}.csv", dtype={"state_fips": str, "naics_code": str})
    out = compare(master, cbp, a.naics)
    OUTPUT.mkdir(exist_ok=True)
    path = OUTPUT / f"completeness_{a.year}.csv"
    out.to_csv(path, index=False)
    print(out.head(15).to_string(index=False))
    print(f"\nFull table -> {path}")


if __name__ == "__main__":
    main()
