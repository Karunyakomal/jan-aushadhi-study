-- MySQL schema: Jan Aushadhi generic medicine savings and access study
CREATE DATABASE IF NOT EXISTS jan_aushadhi;
USE jan_aushadhi;

-- Jan Aushadhi (PMBJP) product list
CREATE TABLE IF NOT EXISTS ja_medicines (
  drug_code     VARCHAR(20) PRIMARY KEY,
  generic_name  VARCHAR(400) NOT NULL,
  unit_size     VARCHAR(60)  NOT NULL,     -- as printed, e.g. "10's"
  mrp           DECIMAL(10,2) NOT NULL,    -- price of one pack, GST included
  group_name    VARCHAR(120),              -- therapeutic group, e.g. Anti-diabetic
  name_key      VARCHAR(300),              -- cleaned molecule name (made by the loader)
  strength_key  VARCHAR(120),               -- cleaned strength, e.g. 500mg
  form          VARCHAR(20),               -- tablet / capsule / other
  pack_count    INT,                       -- units per pack (tablets/capsules only)
  price_per_unit DECIMAL(10,4)             -- mrp / pack_count
);

-- NPPA ceiling prices (maximum price allowed for scheduled medicines, GST NOT included)
CREATE TABLE IF NOT EXISTS ceiling_prices (
  ceiling_id    INT PRIMARY KEY,           -- = Sl. No. in the NPPA order
  medicine      VARCHAR(400) NOT NULL,
  strength      VARCHAR(120),
  unit          VARCHAR(40),               -- e.g. "1 Tablet"
  ceiling_price DECIMAL(10,4) NOT NULL,    -- per unit, before GST
  name_key      VARCHAR(300),
  strength_key  VARCHAR(120),
  form          VARCHAR(20)
);

-- Which Jan Aushadhi medicine is the same product as which ceiling-price entry
CREATE TABLE IF NOT EXISTS medicine_matches (
  drug_code   VARCHAR(20) PRIMARY KEY,
  ceiling_id  INT NOT NULL,
  method      VARCHAR(10) NOT NULL,        -- auto / manual
  FOREIGN KEY (drug_code)  REFERENCES ja_medicines(drug_code),
  FOREIGN KEY (ceiling_id) REFERENCES ceiling_prices(ceiling_id)
);

-- Population by state (and district, when available)
CREATE TABLE IF NOT EXISTS regions (
  region_id   INT AUTO_INCREMENT PRIMARY KEY,
  state       VARCHAR(80) NOT NULL,
  district    VARCHAR(80),                 -- empty = whole-state row
  population  BIGINT NOT NULL,
  pop_source  VARCHAR(500) NOT NULL,       -- e.g. "Census 2011"
  UNIQUE KEY uq_region (state, district)
);

-- Jan Aushadhi Kendras (stores)
CREATE TABLE IF NOT EXISTS kendras (
  kendra_code VARCHAR(30) PRIMARY KEY,
  state       VARCHAR(80) NOT NULL,
  district    VARCHAR(80),
  pin_code    VARCHAR(10)
);

-- Store counts by district (from the store list, or from a government table such as a PIB/Parliament annexure)
CREATE TABLE IF NOT EXISTS kendra_counts_district (
  state        VARCHAR(80) NOT NULL,
  district     VARCHAR(80) NOT NULL,
  kendras      INT NOT NULL,
  as_of        VARCHAR(40) NOT NULL,
  count_source VARCHAR(500) NOT NULL,
  PRIMARY KEY (state, district)
);

-- Used when only state-wise store counts are available (e.g. from a Parliament answer)
CREATE TABLE IF NOT EXISTS kendra_counts_state (
  state       VARCHAR(80) PRIMARY KEY,
  kendras     INT NOT NULL,
  as_of       VARCHAR(40) NOT NULL,
  count_source VARCHAR(500) NOT NULL
);

-- Study settings (GST rate used to make ceiling prices comparable with MRP)
CREATE TABLE IF NOT EXISTS settings (
  name  VARCHAR(40) PRIMARY KEY,
  value DECIMAL(10,4) NOT NULL
);
