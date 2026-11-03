"""Database connection + settings. Uses MySQL when config.ini exists, otherwise a local SQLite test file."""
import configparser, os, sqlite3

def settings():
    cfg = configparser.ConfigParser()
    if os.path.exists("config.ini"):
        cfg.read("config.ini")
    return {"gst_percent": float(cfg.get("study", "gst_percent", fallback="5"))}

SQLITE_SCHEMA = """
CREATE TABLE IF NOT EXISTS ja_medicines(drug_code TEXT PRIMARY KEY, generic_name TEXT, unit_size TEXT, mrp REAL, group_name TEXT,
  name_key TEXT, strength_key TEXT, form TEXT, pack_count INT, price_per_unit REAL);
CREATE TABLE IF NOT EXISTS ceiling_prices(ceiling_id INT PRIMARY KEY, medicine TEXT, strength TEXT, unit TEXT, ceiling_price REAL,
  name_key TEXT, strength_key TEXT, form TEXT);
CREATE TABLE IF NOT EXISTS medicine_matches(drug_code TEXT PRIMARY KEY, ceiling_id INT, method TEXT);
CREATE TABLE IF NOT EXISTS regions(region_id INTEGER PRIMARY KEY AUTOINCREMENT, state TEXT, district TEXT, population INT, pop_source TEXT,
  UNIQUE(state, district));
CREATE TABLE IF NOT EXISTS kendras(kendra_code TEXT PRIMARY KEY, state TEXT, district TEXT, pin_code TEXT);
CREATE TABLE IF NOT EXISTS kendra_counts_state(state TEXT PRIMARY KEY, kendras INT, as_of TEXT, count_source TEXT);
CREATE TABLE IF NOT EXISTS settings(name TEXT PRIMARY KEY, value REAL);
CREATE TABLE IF NOT EXISTS kendra_counts_district(state TEXT, district TEXT, kendras INT, as_of TEXT, count_source TEXT, PRIMARY KEY(state, district));
"""

def connect():
    if os.path.exists("config.ini"):
        import pymysql
        cfg = configparser.ConfigParser(); cfg.read("config.ini"); m = cfg["mysql"]
        conn = pymysql.connect(host=m.get("host", "localhost"), user=m["user"], password=m["password"],
                               database=m.get("database", "jan_aushadhi"), port=int(m.get("port", 3306)),
                               charset="utf8mb4")
        print(f"Using MySQL database '{m.get('database', 'jan_aushadhi')}'")
        return conn, "%s"
    print("NOTE: config.ini not found -> using local TEST database jan_aushadhi_test.db (not MySQL)")
    conn = sqlite3.connect("jan_aushadhi_test.db")
    conn.executescript(SQLITE_SCHEMA)
    return conn, "?"
