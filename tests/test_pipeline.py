"""Offline tests using synthetic fixtures shaped like the real sources.

Run: pytest -q
"""
import sqlite3
import sys
from pathlib import Path

import pandas as pd
import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import build_db  # noqa: E402
import fetch_acs  # noqa: E402
import geocode_plants  # noqa: E402
import load_nri  # noqa: E402
import load_shipments  # noqa: E402
import parse_mhi_plant_list  # noqa: E402


@pytest.fixture
def plant_pdf(tmp_path):
    """Mimic the MHI layout: plant table on the left, state-count table on the right."""
    from reportlab.lib.pagesizes import letter
    from reportlab.pdfgen import canvas
    path = tmp_path / "plants.pdf"
    c = canvas.Canvas(str(path), pagesize=letter)
    c.setFont("Helvetica", 8)
    xs = [30, 60, 110, 290, 380, 430, 510]
    y = 740
    for x, t in zip(xs, ["MFG #", "Plant Code", "Manufacturer", "CITY", "STATE", "State", "Number of Plants"]):
        c.drawString(x, y, t)
    rows = [
        ("1", "ADVH01", "ADVENTURE HOMES", "GARRETT", "IN", "Alabama", "19"),
        ("2", "CAVC04", "CAVCO-GOODYEAR", "GOODYEAR", "AZ", "Arizona", "4"),
        ("3", "CHBD57", "CHAMPION #157", "CHANDLER", "AZ", "North Carolina", "8"),
        ("4", "HBOS01", "CLAYTON BUCKEYE", "BUCKEYE", "AZ", "", ""),
        ("5", "PLMH15", "CAVCO-FORT WORTH", "FORT WORTH", "TX", "", ""),
    ]
    for r in rows:
        y -= 14
        for x, t in zip(xs[:6] + [520], r):
            if t:
                c.drawString(x, y, t)
    c.save()
    return path


def test_parse_plant_list(plant_pdf):
    rows = parse_mhi_plant_list.parse(plant_pdf, "2026-01-31")
    assert [r["plant_id"] for r in rows] == ["ADVH01", "CAVC04", "CHBD57", "HBOS01", "PLMH15"]
    r = {x["plant_id"]: x for x in rows}
    assert r["PLMH15"]["city"] == "Fort Worth" and r["PLMH15"]["state_abbr"] == "TX"
    assert r["CHBD57"]["plant_name"] == "CHAMPION #157" and r["CHBD57"]["producer_guess"] == "Champion"
    assert r["CAVC04"]["producer_guess"] == "Cavco"
    assert all(len(x["state_abbr"]) == 2 for x in rows)  # side table ignored


def test_geocode(tmp_path):
    gaz = tmp_path / "gaz.txt"
    gaz.write_text(
        "USPS\tGEOID\tANSICODE\tNAME\tLSAD\tFUNCSTAT\tALAND\tAWATER\tALAND_SQMI\tAWATER_SQMI\tINTPTLAT\tINTPTLONG                \n"
        "AZ\t0428380\t1\tGoodyear city\t25\tA\t1\t0\t1\t0\t33.43\t-112.39\n"
        "TX\t4827000\t1\tFort Worth city\t25\tA\t1\t0\t1\t0\t32.78\t-97.35\n"
        "CO\t0810105\t1\tBuena Vista town\t43\tA\t1\t0\t1\t0\t38.84\t-106.13\n", encoding="latin-1")
    plants = pd.DataFrame({"plant_id": ["a", "b", "c", "d"],
                           "city": ["Goodyear", "Ft. Worth", "Buena Vista", "Nowhere"],
                           "state_abbr": ["AZ", "TX", "CO", "CO"]})
    out = geocode_plants.geocode(plants, geocode_plants.read_gazetteer(gaz))
    assert out.loc[0, "lat"] == pytest.approx(33.43)
    assert out.loc[1, "place_geoid"] == "4827000"
    assert out.loc[2, "geocode_method"] == "gazetteer_place"
    assert pd.isna(out.loc[3, "lat"])


def test_load_shipments(tmp_path):
    raw = [["Shipments of New Manufactured Homes by State", None, None, None],
           [None, None, None, None],
           ["State", 2020, 2021, 2022],
           ["United States", 94390, 105772, 112882],
           ["Colorado", 1100, 1200, "1,300"],
           ["Texas 1/", 15000, 17000, 18000],
           ["Wyoming", "(S)", 200, 210],
           ["Note: synthetic fixture", None, None, None]]
    p = tmp_path / "ship.xlsx"
    pd.DataFrame(raw).to_excel(p, header=False, index=False)
    tidy = load_shipments.load(p)
    co = tidy[tidy.state_fips == "08"].set_index("year")["units"].to_dict()
    assert co == {2020: 1100, 2021: 1200, 2022: 1300}
    assert set(tidy.state_fips) == {"08", "48", "56"}           # US total skipped
    assert len(tidy[tidy.state_fips == "56"]) == 2              # '(S)' suppressed value skipped


def test_acs_transform():
    header = ["NAME"] + list(fetch_acs.VARS) + ["state"]
    vals = {"B01003_001E": "5800000", "B25001_001E": "2500000", "B25024_001E": "2500000",
            "B25024_010E": "100000", "B19013_001E": "92000", "B25077_001E": "-666666666",
            "B25070_001E": "800000", "B25070_007E": "60000", "B25070_008E": "40000",
            "B25070_009E": "50000", "B25070_010E": "250000", "B25070_011E": "20000"}
    payload = [header, ["Colorado"] + [vals[v] for v in fetch_acs.VARS] + ["08"]]
    out = fetch_acs.transform(payload, "state", 2023)
    r = out.iloc[0]
    assert r.geoid == "08" and r.mobile_home_share == 0.04
    assert pd.isna(r.median_home_value)                         # sentinel removed
    assert r.renter_burden_30plus == 400000
    assert r.renter_burden_share == round(400000 / 780000, 4)
    _, params = fetch_acs.build_url(2023, "tract", "08")
    assert params["in"] == "state:08 county:*"


def test_build_db(tmp_path, monkeypatch):
    # Point processed inputs at a temp dir containing one geocoded plant
    proc = tmp_path / "processed"
    proc.mkdir()
    pd.DataFrame([{"plant_id": "CAVC04", "plant_name": "CAVCO-GOODYEAR", "city": "Goodyear",
                   "state_abbr": "AZ", "lat": 33.43, "lon": -112.39, "code_basis": "HUD_CODE",
                   "status": "active", "source_id": "SRC05", "producer_guess": "Cavco"}]
                 ).to_csv(proc / "plants_mhi.csv", index=False)
    pd.DataFrame([{"state_fips": "08", "year": 2022, "units": 1300, "code_basis": "HUD_CODE",
                   "source_id": "SRC01"}]).to_csv(proc / "shipments_state_year.csv", index=False)
    load_nri.transform(pd.DataFrame({"STCOFIPS": ["8031"], "WFIR_RISKS": ["55.1"], "WFIR_RISKR": ["Relatively Moderate"],
                                     "RISK_SCORE": ["90"], "SOVI_SCORE": ["60"], "RESL_SCORE": ["50"],
                                     "WFIR_EALT": ["1000"]}), "county", "test").to_csv(proc / "hazards_nri_county.csv", index=False)
    feeds = {k: [p if p.parent != build_db.PROCESSED else proc / p.name for p in v]
             for k, v in build_db.FEEDS.items()}
    monkeypatch.setattr(build_db, "FEEDS", feeds)
    monkeypatch.setattr(sys, "argv", ["build_db.py", "--out-dir", str(tmp_path / "out")])
    build_db.main()
    con = sqlite3.connect(tmp_path / "out" / "ihg.sqlite")
    assert con.execute("SELECT COUNT(*) FROM states").fetchone()[0] == 51
    assert con.execute("SELECT COUNT(*) FROM sources").fetchone()[0] == 24
    assert con.execute("SELECT COUNT(*) FROM policies WHERE state_abbr='CO'").fetchone()[0] == 6
    assert con.execute("SELECT COUNT(*) FROM plants").fetchone()[0] == 5   # 4 seed + 1
    assert con.execute("PRAGMA foreign_key_check").fetchall() == []
    import geopandas as gpd
    g = gpd.read_file(tmp_path / "out" / "ihg.gpkg", layer="plants")
    assert len(g) == 1 and g.crs.to_epsg() == 4326
    s = gpd.read_file(tmp_path / "out" / "ihg.gpkg", layer="state_summary")
    co = s[s.state_abbr == "CO"].iloc[0]
    assert co.mountain_west == 1 and s.mountain_west.sum() == 8
    assert con.execute("SELECT COUNT(*) FROM hazards").fetchone()[0] == 1
    assert co.plants_active == 4 and co.plants_hud_code == 0 and co.ship_latest_units == 1300


def test_load_nri():
    df = pd.DataFrame({"TRACTFIPS": ["8031000102"], "WFIR_RISKS": ["97.5"], "WFIR_RISKR": ["Very High"],
                       "RISK_SCORE": ["80"], "SOVI_SCORE": ["70"]})
    out = load_nri.transform(df, "tract", "1.20")
    r = out.iloc[0]
    assert r.geoid == "08031000102" and r.wildfire_risk_score == 97.5 and r.wildfire_risk_rating == "Very High"
    assert "community_resilience" not in out.columns     # missing field reported, not invented
