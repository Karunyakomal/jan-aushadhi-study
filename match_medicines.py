"""Matches each Jan Aushadhi tablet/capsule to the same medicine in the NPPA ceiling-price list.

Pass 1 'auto'      : same cleaned name + same strength + same form.
Pass 2 'auto-salt' : same, after dropping salt words (e.g. 'Metformin Hydrochloride' = 'Metformin').
Pass 3 'manual'    : your own decisions in data/manual_matches.csv (these always win).

Writes (in results/):
  review_needed.csv      unmatched products with the 3 most similar ceiling-price entries, to decide by hand
  auto_match_check.csv   30 random automatic matches; check each by hand and fill the 'correct' column (yes/no)
Not every medicine has a ceiling price (only scheduled medicines do), so many will rightly stay unmatched."""
import csv, difflib, os, random, sys
sys.stdout.reconfigure(errors="replace")
from db import connect
from normalize import without_salts, molecule_family

os.makedirs("results", exist_ok=True)
conn, P = connect(); cur = conn.cursor()
cur.execute("DELETE FROM medicine_matches")

cur.execute("SELECT drug_code, generic_name, unit_size, name_key, strength_key, form FROM ja_medicines "
            "WHERE price_per_unit IS NOT NULL AND form IN ('tablet','capsule') AND strength_key <> ''")
ja = cur.fetchall()
cur.execute("SELECT ceiling_id, medicine, strength, unit, ceiling_price, name_key, strength_key, form FROM ceiling_prices")
cp = cur.fetchall()

def index(keyfn):
    idx = {}
    for c in cp:
        idx.setdefault((keyfn(c[5]), c[6], c[7]), []).append(c)
    return idx

exact, salt = index(lambda k: k), index(without_salts)
matched, ambiguous = {}, []
for code, name, unit_size, nk, sk, form in ja:
    for method, idx, key in (("auto", exact, nk), ("auto-salt", salt, without_salts(nk))):
        cands = idx.get((key, sk, form), [])
        prices = {round(float(c[4]), 4) for c in cands}
        if len(prices) == 1:
            matched[code] = (cands[0][0], method); break
        if len(prices) > 1:
            ambiguous.append(code); break          # same medicine listed with different prices -> decide by hand

# Manual decisions (drug_code, ceiling_id); a ceiling_id of 0 means "checked: no ceiling-price equivalent"
manual_file = "data/manual_matches.csv"
manual_bad, manual_none, undecided = [], set(), 0
ja_codes = {r[0] for r in ja}; cp_ids = {c[0] for c in cp}
if os.path.exists(manual_file):
    with open(manual_file, newline="", encoding="utf-8-sig") as f:
        for n, r in enumerate(csv.DictReader(f), start=2):
            code, cid = (r.get("drug_code") or "").strip(), (r.get("ceiling_id") or "").strip()
            if not code and not cid: continue
            if code and not cid: undecided += 1; continue          # left blank = not decided yet
            if code not in ja_codes: manual_bad.append(f"row {n}: drug_code '{code}' is not a comparable Jan Aushadhi tablet/capsule"); continue
            if cid == "0": matched.pop(code, None); manual_none.add(code); continue
            if not cid.isdigit() or int(cid) not in cp_ids: manual_bad.append(f"row {n}: ceiling_id '{cid}' does not exist"); continue
            matched[code] = (int(cid), "manual")

for code, (cid, method) in matched.items():
    cur.execute(f"INSERT INTO medicine_matches(drug_code,ceiling_id,method) VALUES ({P},{P},{P})", (code, cid, method))
conn.commit()

# Split the unmatched products:
#  - the same medicine (same molecules, ignoring salt and release words) IS in the ceiling list
#    but strength/form/release differ or several prices exist -> needs a human decision
#  - the medicine is NOT in the ceiling list at all -> no ceiling price exists; nothing to decide
def base(key):
    return molecule_family(key)
cp_bases = {base(c[5]) for c in cp}
no_equiv = [r for r in ja if r[0] not in matched and r[0] not in manual_none and base(r[3]) not in cp_bases]
no_equiv_codes = {r[0] for r in no_equiv}
with open("results/no_ceiling_equivalent.csv", "w", newline="", encoding="utf-8-sig") as f:
    w = csv.writer(f); w.writerow(["drug_code", "generic_name", "unit_size", "reason"])
    for r in no_equiv: w.writerow([r[0], r[1], r[2], "medicine (molecule combination) not in the ceiling price list"])

# Review file for unmatched products
by_id = {c[0]: c for c in cp}
labels = {c[0]: f"{c[1]} {c[2]}".lower() for c in cp}
with open("results/review_needed.csv", "w", newline="", encoding="utf-8-sig") as f:
    w = csv.writer(f)
    w.writerow(["drug_code", "generic_name", "unit_size", "reason",
                "option1_ceiling_id", "option1", "option2_ceiling_id", "option2", "option3_ceiling_id", "option3"])
    review = 0
    for code, name, unit_size, nk, sk, form in ja:
        if code in matched or code in manual_none or code in no_equiv_codes: continue
        same = [c for c in cp if base(c[5]) == base(nk)]           # show entries for the same medicine first
        best = sorted(same or cp, key=lambda c: difflib.SequenceMatcher(None, name.lower(), labels[c[0]]).ratio(), reverse=True)[:3]
        row = [code, name, unit_size, "several prices for same medicine" if code in ambiguous else "no automatic match"]
        for c in best: row += [c[0], f"{c[1]} | {c[2]} | {c[3]} | Rs {c[4]}"]
        w.writerow(row); review += 1

# Random sample of automatic matches for a hand check (fixed seed so the sample is repeatable)
autos = sorted(code for code, (_, m) in matched.items() if m.startswith("auto"))
sample = random.Random(42).sample(autos, min(30, len(autos)))
ja_by = {r[0]: r for r in ja}
with open("results/auto_match_check.csv", "w", newline="", encoding="utf-8-sig") as f:
    w = csv.writer(f); w.writerow(["drug_code", "jan_aushadhi_product", "matched_ceiling_entry", "method", "correct (yes/no)"])
    for code in sample:
        c = by_id[matched[code][0]]
        w.writerow([code, f"{ja_by[code][1]} ({ja_by[code][2]})", f"{c[1]} | {c[2]} | {c[3]}", matched[code][1], ""])

counts = {}
for _, m in matched.values(): counts[m] = counts.get(m, 0) + 1
conn.close()
print(f"Comparable Jan Aushadhi tablets/capsules: {len(ja)}")
print(f"Matched: {len(matched)}  ({', '.join(f'{k}: {v}' for k, v in sorted(counts.items())) or 'none'})")
print(f"No ceiling price exists for that medicine: {len(no_equiv)} -> results/no_ceiling_equivalent.csv")
print(f"Need a decision by hand: {review} -> results/review_needed.csv")
print(f"Hand-check sample of automatic matches: {len(sample)} -> results/auto_match_check.csv")
if undecided: print(f"Rows in data/manual_matches.csv with no ceiling_id yet (not decided): {undecided}")
if manual_bad: print("Problems in data/manual_matches.csv:\n  " + "\n  ".join(manual_bad))
print("Next: python run_analysis.py")
