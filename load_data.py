"""Loads the files in data/ into the database. Safe to re-run: it clears the tables and reloads everything.

Required files (column names must match exactly; see README):
  data/ja_products.csv      drug_code, generic_name, unit_size, mrp, group_name
  data/ceiling_prices.csv   medicine, strength, unit, ceiling_price
  data/population.csv       state, district, population, source     (district empty = whole state)
At least one of (if you give more than one, the first one in this list is used):
  data/kendras.csv                 kendra_code, state, district, pin_code       (one row per store)
  data/kendra_counts_district.csv  state, district, kendras, as_of, source      (district totals, e.g. PIB/Parliament annexure)
  data/kendra_counts_state.csv     state, kendras, as_of, source                (state totals only)
"""
import csv, os, re, sys
sys.stdout.reconfigure(errors="replace")
from db import connect, settings
from normalize import name_key, strength_key, form_of, release_of, pack_count, units_in, state_key, district_key

REQUIRED = {
    "ja_products.csv": ["drug_code", "generic_name", "unit_size", "mrp", "group_name"],
    "ceiling_prices.csv": ["medicine", "strength", "unit", "ceiling_price"],
    "population.csv": ["state", "district", "population", "source"],
}
OPTIONAL = {
    "kendras.csv": ["kendra_code", "state", "district", "pin_code"],
    "kendra_counts_district.csv": ["state", "district", "kendras", "as_of", "source"],
    "kendra_counts_state.csv": ["state", "kendras", "as_of", "source"],
}
problems = []
os.makedirs("results", exist_ok=True)

def read(name, cols, required=True):
    path = os.path.join("data", name)
    if not os.path.exists(path):
        if required: problems.append(f"missing file data/{name}")
        return None
    with open(path, newline="", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        # Accept the official headers as downloaded: "Drug Code" -> drug_code, "MRP" -> mrp
        reader.fieldnames = [re.sub(r"[^a-z0-9]+", "_", (h or "").strip().lower()).strip("_") for h in (reader.fieldnames or [])]
        header = reader.fieldnames
        missing = [c for c in cols if c not in header]
        if missing:
            problems.append(f"data/{name}: missing column(s) {missing}. Found: {header}")
            return None
        rows = []
        for n, r in enumerate(reader, start=2):
            r = {(k or "").strip(): (v or "").strip() for k, v in r.items()}
            if any(r.values()):
                r["_row"] = n; rows.append(r)
        return rows

def number(r, col, file, cast=float, positive=True):
    try:
        v = cast(r[col].replace(",", "").replace("₹", "").replace("Rs.", "").replace("Rs", "").strip())
        if positive and v <= 0: raise ValueError
        return v
    except ValueError:
        problems.append(f"data/{file} row {r['_row']}: '{col}' must be a {'positive ' if positive else ''}number (got '{r[col]}')")
        return None

ja = read("ja_products.csv", REQUIRED["ja_products.csv"])
cp = read("ceiling_prices.csv", REQUIRED["ceiling_prices.csv"])
pop = read("population.csv", REQUIRED["population.csv"])
kl = read("kendras.csv", OPTIONAL["kendras.csv"], required=False)
kd = read("kendra_counts_district.csv", OPTIONAL["kendra_counts_district.csv"], required=False)
kc = read("kendra_counts_state.csv", OPTIONAL["kendra_counts_state.csv"], required=False)
if kl is None and kd is None and kc is None and not any("kendra" in p for p in problems):
    problems.append("add data/kendras.csv, data/kendra_counts_district.csv or data/kendra_counts_state.csv (needed for the access questions)")
if problems:
    sys.exit("Please fix these first:\n  " + "\n  ".join(problems))

conn, P = connect(); cur = conn.cursor()
for t in ("medicine_matches", "ja_medicines", "ceiling_prices", "kendras", "kendra_counts_district", "kendra_counts_state", "regions", "settings"):
    cur.execute(f"DELETE FROM {t}")
cur.execute(f"INSERT INTO settings(name,value) VALUES ({P},{P})", ("gst_percent", settings()["gst_percent"]))

# --- Jan Aushadhi products
seen, no_pack, zero_mrp = set(), 0, []
for r in ja:
    code = r["drug_code"]
    if code in seen: problems.append(f"data/ja_products.csv row {r['_row']}: drug_code {code} appears twice"); continue
    seen.add(code)
    if re.fullmatch(r"0+(\.0+)?", r["mrp"].strip()):
        zero_mrp.append(r); continue                     # no price published: left out and listed, not treated as free
    mrp = number(r, "mrp", "ja_products.csv")
    if mrp is None: continue
    form = form_of(r["generic_name"], r["unit_size"])
    count = pack_count(r["unit_size"]) if form in ("tablet", "capsule") else None
    if form in ("tablet", "capsule") and count is None: no_pack += 1
    cur.execute(f"""INSERT INTO ja_medicines(drug_code,generic_name,unit_size,mrp,group_name,name_key,strength_key,form,pack_count,price_per_unit)
                    VALUES ({P},{P},{P},{P},{P},{P},{P},{P},{P},{P})""",
                (code, r["generic_name"], r["unit_size"], mrp, r["group_name"], name_key(r["generic_name"]),
                 strength_key(r["generic_name"]), form, count, round(mrp / count, 4) if count else None))

# --- NPPA ceiling prices
for i, r in enumerate(cp, start=1):
    if r.get("sl_no", "").isdigit(): i = int(r["sl_no"])      # use the Sl. No. printed in the NPPA order
    price = number(r, "ceiling_price", "ceiling_prices.csv")
    if price is None: continue
    full = f"{r['medicine']} {r['strength']}"
    form = form_of(r["strength"], r["unit"], r["medicine"])
    rel = release_of(full)
    key = name_key(r["medicine"]); key = key.split("|")[0] + ("|" + rel if rel else "")
    cur.execute(f"""INSERT INTO ceiling_prices(ceiling_id,medicine,strength,unit,ceiling_price,name_key,strength_key,form)
                    VALUES ({P},{P},{P},{P},{P},{P},{P},{P})""",
                (i, r["medicine"], r["strength"], r["unit"], round(price / units_in(r["unit"]), 4),
                 key, strength_key(r["strength"]) or strength_key(r["medicine"]), form))

# --- Population (state rows have an empty district)
for r in pop:
    p_ = number(r, "population", "population.csv", cast=int)
    if p_ is None: continue
    try:
        cur.execute(f"INSERT INTO regions(state,district,population,pop_source) VALUES ({P},{P},{P},{P})",
                    (state_key(r["state"]), district_key(r["district"]), p_, r["source"]))
    except Exception:
        problems.append(f"data/population.csv row {r['_row']}: {r['state']} / {r['district'] or '(state total)'} appears twice")
cur.execute("SELECT state FROM regions WHERE district = ''")
states_with_pop = {row[0] for row in cur.fetchall()}

# --- Kendras: store list (preferred), else district counts, else state totals
unmatched_districts, unknown_states = {}, set()
cur.execute("SELECT state, district FROM regions WHERE district <> ''")
known_districts = {(s_, d_) for s_, d_ in cur.fetchall()}
district_counts, used = {}, None          # (state, district) -> stores
if kl:
    used = "data/kendras.csv (store list)"
    as_of = __import__("datetime").date.fromtimestamp(os.path.getmtime("data/kendras.csv")).isoformat()
    for r in kl:
        st, dk = state_key(r["state"]), district_key(r["district"])
        try:
            cur.execute(f"INSERT INTO kendras(kendra_code,state,district,pin_code) VALUES ({P},{P},{P},{P})",
                        (r["kendra_code"], st, dk, r["pin_code"]))
        except Exception:
            problems.append(f"data/kendras.csv row {r['_row']}: kendra_code {r['kendra_code']} appears twice"); continue
        district_counts[(st, dk)] = district_counts.get((st, dk), 0) + 1
    meta = {k: (as_of, used) for k in district_counts}
elif kd:
    used, meta = "data/kendra_counts_district.csv", {}
    for r in kd:
        n = number(r, "kendras", "kendra_counts_district.csv", cast=int, positive=False)
        if n is None: continue
        key = (state_key(r["state"]), district_key(r["district"]))
        if not key[1]:
            problems.append(f"data/kendra_counts_district.csv row {r['_row']}: district is empty"); continue
        if key in district_counts:
            problems.append(f"data/kendra_counts_district.csv row {r['_row']}: {key[0]} / {key[1]} appears twice"); continue
        district_counts[key] = n; meta[key] = (r["as_of"], r["source"])

if district_counts:
    state_totals = {}
    for (st, dk), n in district_counts.items():
        cur.execute(f"INSERT INTO kendra_counts_district(state,district,kendras,as_of,count_source) VALUES ({P},{P},{P},{P},{P})",
                    (st, dk, n, meta[(st, dk)][0], meta[(st, dk)][1]))
        state_totals[st] = state_totals.get(st, 0) + n
        if known_districts and (st, dk) not in known_districts:
            unmatched_districts[(st, dk)] = n
    any_meta = next(iter(meta.values()))
    for st, n in state_totals.items():
        cur.execute(f"INSERT INTO kendra_counts_state(state,kendras,as_of,count_source) VALUES ({P},{P},{P},{P})",
                    (st, n, any_meta[0], f"sum of districts in {used}"))
        if st not in states_with_pop: unknown_states.add(st)
elif kc:
    used = "data/kendra_counts_state.csv"
    for r in kc:
        n = number(r, "kendras", "kendra_counts_state.csv", cast=int, positive=False)
        if n is None: continue
        st = state_key(r["state"])
        cur.execute(f"INSERT INTO kendra_counts_state(state,kendras,as_of,count_source) VALUES ({P},{P},{P},{P})",
                    (st, n, r["as_of"], r["source"]))
        if st not in states_with_pop: unknown_states.add(st)

conn.commit()
cur.execute("SELECT COUNT(*) FROM ja_medicines"); n_ja = cur.fetchone()[0]
cur.execute("SELECT COUNT(*) FROM ceiling_prices"); n_cp = cur.fetchone()[0]
conn.close()

print(f"Loaded {n_ja} Jan Aushadhi products, {n_cp} ceiling prices, {len(pop)} population rows.")
print(f"  Store numbers taken from: {used}")
if zero_mrp:
    with open("results/zero_mrp_products.csv", "w", newline="", encoding="utf-8-sig") as f:
        w = csv.writer(f); w.writerow(["drug_code", "generic_name", "unit_size", "group_name"])
        for r in zero_mrp: w.writerow([r["drug_code"], r["generic_name"], r["unit_size"], r["group_name"]])
    print(f"  {len(zero_mrp)} product(s) have MRP 0 (no price listed); left out -> results/zero_mrp_products.csv")
if no_pack:
    print(f"  {no_pack} tablet/capsule product(s) have a pack size the script could not read; they are left out of price comparisons.")
if unknown_states:
    print("  States with stores but no population row (spelling differs?): " + ", ".join(sorted(unknown_states)))
if unmatched_districts:
    with open("results/unmatched_districts.csv", "w", newline="", encoding="utf-8-sig") as f:
        w = csv.writer(f); w.writerow(["state", "district_in_store_data", "stores"])
        for (st, dk), n in sorted(unmatched_districts.items()): w.writerow([st, dk, n])
    print(f"  {len(unmatched_districts)} district name(s) in the store data are not in population.csv "
          "(often new districts created after 2011) -> results/unmatched_districts.csv")
if problems:
    print("Rows skipped:\n  " + "\n  ".join(problems))
print("Next: python match_medicines.py")
