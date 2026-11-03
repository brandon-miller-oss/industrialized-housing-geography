"""Shared paths and helpers."""
from pathlib import Path
import csv

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw"
PROCESSED = ROOT / "data" / "processed"
SEED = ROOT / "data" / "seed"
REFERENCE = ROOT / "data" / "reference"
OUTPUT = ROOT / "output"


def load_states():
    """Return list of dicts from data/reference/states.csv."""
    with open(REFERENCE / "states.csv", newline="") as f:
        return list(csv.DictReader(f))


def state_lookup():
    """Map name/abbr (upper-case) -> state row."""
    out = {}
    for s in load_states():
        out[s["state_abbr"].upper()] = s
        out[s["state_name"].upper()] = s
    return out
