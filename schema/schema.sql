-- Geography of Industrialized Housing: relational schema (SQLite / GeoPackage compatible)
-- Spatial layers (plants, projects) are written to the GeoPackage by scripts/build_db.py
-- from the lat/lon columns below. Joins to boundaries use Census GEOIDs.

PRAGMA foreign_keys = ON;

-- Every record cites a source. Loaded from data/reference/source_inventory.csv
CREATE TABLE IF NOT EXISTS sources (
    source_id        TEXT PRIMARY KEY,           -- SRC01 ...
    layer            TEXT,
    name             TEXT NOT NULL,
    publisher        TEXT,
    what_it_covers   TEXT,
    geography        TEXT,
    frequency        TEXT,
    years_available  TEXT,
    format_access    TEXT,
    url              TEXT,
    limitations      TEXT,
    priority         INTEGER
);

-- Reference: states with Census region/division
CREATE TABLE IF NOT EXISTS states (
    state_fips   TEXT PRIMARY KEY,               -- '08'
    state_abbr   TEXT UNIQUE NOT NULL,           -- 'CO'
    state_name   TEXT NOT NULL,
    region       TEXT NOT NULL,                  -- Northeast | Midwest | South | West
    division     TEXT NOT NULL,                  -- e.g. Mountain
    mountain_west INTEGER DEFAULT 0              -- 1 = CHRIS core study region (AZ CO ID MT NV NM UT WY)
);

-- Companies (parent level). One producer -> many plants.
CREATE TABLE IF NOT EXISTS producers (
    producer_id      TEXT PRIMARY KEY,           -- slug, e.g. 'cavco', 'fading-west'
    name             TEXT NOT NULL,
    parent_company   TEXT,                       -- e.g. Clayton -> Berkshire Hathaway
    hq_city          TEXT,
    hq_state         TEXT REFERENCES states(state_abbr),
    ownership_type   TEXT,                       -- public | private | nonprofit | cooperative
    website          TEXT,
    notes            TEXT,
    source_id        TEXT REFERENCES sources(source_id),
    verified_date    TEXT                        -- ISO date last checked
);

-- Physical factories. product_type and code_basis drive most analysis.
CREATE TABLE IF NOT EXISTS plants (
    plant_id           TEXT PRIMARY KEY,         -- MHI plant code when available (e.g. 'CAVC04')
    producer_id        TEXT REFERENCES producers(producer_id),
    plant_name         TEXT,                     -- as listed by source, e.g. 'CAVCO-GOODYEAR'
    city               TEXT,
    state_abbr         TEXT REFERENCES states(state_abbr),
    county_fips        TEXT,                     -- 5-digit
    lat                REAL,
    lon                REAL,
    geocode_method     TEXT,                     -- gazetteer_place | address | manual
    code_basis         TEXT CHECK (code_basis IN ('HUD_CODE','STATE_MODULAR','BOTH','UNKNOWN')),
    product_type       TEXT,                     -- manufactured | modular_volumetric | panelized | tiny_home | mixed
    certifications     TEXT,                     -- semicolon list: HUD;CO_DOH_FB;CO_DOH_FBNR;NY_MHP ...
    status             TEXT DEFAULT 'active',    -- active | closed | sold | renamed
    opened_year        INTEGER,
    closed_year        INTEGER,
    capacity_units_yr  INTEGER,                  -- from survey / company disclosures
    source_id          TEXT REFERENCES sources(source_id),
    verified_date      TEXT
);

-- Public aggregate shipments (SRC01/SRC04). HUD-Code only unless noted.
CREATE TABLE IF NOT EXISTS shipments_state_year (
    state_fips    TEXT REFERENCES states(state_fips),
    year          INTEGER,
    code_basis    TEXT DEFAULT 'HUD_CODE',
    units         INTEGER,                       -- homes shipped to the state
    floors        INTEGER,                       -- sections shipped, if reported
    source_id     TEXT REFERENCES sources(source_id),
    PRIMARY KEY (state_fips, year, code_basis, source_id)
);

-- Firm-level distribution: from the survey, press releases, project records.
-- dest_geoid is the Census GEOID matching dest_geo_level.
CREATE TABLE IF NOT EXISTS producer_distribution (
    dist_id         INTEGER PRIMARY KEY AUTOINCREMENT,
    producer_id     TEXT REFERENCES producers(producer_id),
    plant_id        TEXT REFERENCES plants(plant_id),
    year            INTEGER,
    dest_geo_level  TEXT CHECK (dest_geo_level IN ('state','county','place','tract')),
    dest_geoid      TEXT,
    units           INTEGER,
    data_origin     TEXT,                        -- survey | press_release | project_record | permit | estimate
    confidence      TEXT CHECK (confidence IN ('high','medium','low')),
    confidential    INTEGER DEFAULT 0,           -- 1 = survey response, never publish disaggregated
    source_id       TEXT REFERENCES sources(source_id),
    notes           TEXT
);

-- Known developments built with factory-built units (e.g. Fading West projects, IHIP-backed units)
CREATE TABLE IF NOT EXISTS projects (
    project_id        TEXT PRIMARY KEY,
    producer_id       TEXT REFERENCES producers(producer_id),
    project_name      TEXT,
    city              TEXT,
    state_abbr        TEXT REFERENCES states(state_abbr),
    county_fips       TEXT,
    tract_geoid       TEXT,
    lat               REAL,
    lon               REAL,
    units             INTEGER,
    tenure            TEXT,                      -- rental | ownership | mixed
    housing_type      TEXT,                      -- single_family | townhome | multifamily | adu
    affordability     TEXT,                      -- e.g. '80% AMI', 'LIHTC 60%', 'market'
    funding_sources   TEXT,                      -- semicolon list: LIHTC;IHIP;Prop123;CHFA ...
    year_completed    INTEGER,
    status            TEXT,                      -- planned | under_construction | complete
    source_id         TEXT REFERENCES sources(source_id),
    url               TEXT
);

-- Policies affecting industrialized housing. One row per policy x jurisdiction.
CREATE TABLE IF NOT EXISTS policies (
    policy_id           TEXT PRIMARY KEY,        -- e.g. 'CO-SB25-002'
    jurisdiction_level  TEXT CHECK (jurisdiction_level IN ('federal','state','county','municipal')),
    state_abbr          TEXT REFERENCES states(state_abbr),
    geoid               TEXT,                    -- jurisdiction GEOID (state/county/place)
    jurisdiction_name   TEXT,
    policy_name         TEXT NOT NULL,
    citation            TEXT,                    -- bill number / statute / ordinance
    category            TEXT,                    -- see docs/data_dictionary.md policy categories
    applies_to          TEXT,                    -- HUD_CODE | FACTORY_BUILT | ALL_HOUSING
    year_enacted        INTEGER,
    effective_date      TEXT,
    status              TEXT,                    -- enacted | rules_pending | in_effect | repealed | proposed
    funding_amount_usd  REAL,
    summary             TEXT,
    url                 TEXT,
    source_id           TEXT REFERENCES sources(source_id),
    verified_date       TEXT
);

-- Demographic / need indicators (long-ish format keyed by geography and vintage)
CREATE TABLE IF NOT EXISTS demographics (
    geoid                   TEXT,
    geo_level               TEXT CHECK (geo_level IN ('state','county','tract','place')),
    name                    TEXT,
    acs_vintage             INTEGER,             -- end year of the 5-year ACS, e.g. 2023
    total_population        INTEGER,
    total_housing_units     INTEGER,
    mobile_homes            INTEGER,             -- B25024_010E
    mobile_home_share       REAL,
    median_hh_income        INTEGER,             -- B19013_001E
    median_home_value       INTEGER,             -- B25077_001E
    renter_households       INTEGER,             -- B25070_001E
    renter_burden_30plus    INTEGER,             -- B25070_007E..010E
    renter_burden_share     REAL,
    source_id               TEXT REFERENCES sources(source_id),
    PRIMARY KEY (geoid, geo_level, acs_vintage)
);

-- Cost and schedule observations: factory-built vs site-built.
-- Designed to supply cost/timeline assumptions for a factory-built scenario in the
-- Terner Housing Policy Simulator (SRC24), which works in development cost per unit.
CREATE TABLE IF NOT EXISTS cost_schedule (
    obs_id                     INTEGER PRIMARY KEY AUTOINCREMENT,
    producer_id                TEXT REFERENCES producers(producer_id),
    project_id                 TEXT REFERENCES projects(project_id),
    state_abbr                 TEXT REFERENCES states(state_abbr),
    county_fips                TEXT,
    year                       INTEGER,            -- year costs were incurred / quoted
    construction_method        TEXT CHECK (construction_method IN
                                 ('site_built','manufactured','modular_volumetric','panelized','hybrid')),
    housing_type               TEXT,               -- single_family | townhome | multifamily | adu
    units                      INTEGER,
    avg_unit_sf                REAL,
    factory_cost_per_sf        REAL,               -- delivered price from plant
    transport_set_cost_per_unit REAL,              -- shipping + crane/set
    site_work_cost_per_sf      REAL,               -- foundation, utilities, finish-out
    hard_cost_per_sf           REAL,               -- all-in vertical hard cost
    total_dev_cost_per_unit    REAL,               -- matches Terner 'development cost per unit'
    factory_duration_months    REAL,
    site_duration_months       REAL,
    total_schedule_months      REAL,               -- permit-to-CO
    site_built_comparable_months REAL,             -- developer's own site-built estimate, if given
    data_origin                TEXT,               -- survey | pro_forma | project_record | press_release | estimate
    confidence                 TEXT CHECK (confidence IN ('high','medium','low')),
    confidential               INTEGER DEFAULT 0,
    source_id                  TEXT REFERENCES sources(source_id),
    notes                      TEXT
);

-- Hazard and resilience indicators (FEMA NRI, USFS Wildfire Risk to Communities)
CREATE TABLE IF NOT EXISTS hazards (
    geoid                  TEXT,
    geo_level              TEXT CHECK (geo_level IN ('state','county','tract')),
    dataset_version        TEXT,
    wildfire_risk_score    REAL,                   -- NRI WFIR_RISKS (0-100 percentile)
    wildfire_risk_rating   TEXT,                   -- NRI WFIR_RISKR
    wildfire_eal_usd       REAL,                   -- NRI WFIR_EALT expected annual loss
    composite_risk_score   REAL,                   -- NRI RISK_SCORE
    social_vulnerability   REAL,                   -- NRI SOVI_SCORE
    community_resilience   REAL,                   -- NRI RESL_SCORE
    source_id              TEXT REFERENCES sources(source_id),
    PRIMARY KEY (geoid, geo_level, dataset_version)
);

CREATE INDEX IF NOT EXISTS idx_plants_state ON plants(state_abbr);
CREATE INDEX IF NOT EXISTS idx_dist_dest ON producer_distribution(dest_geo_level, dest_geoid);
CREATE INDEX IF NOT EXISTS idx_policies_state ON policies(state_abbr);
