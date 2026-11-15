# Jan Aushadhi Generic Medicines: How Much Do Patients Save, and Who Can Reach a Store?

India's government sells low-cost generic medicines through **Jan Aushadhi Kendras** (stores) under the
Pradhan Mantri Bhartiya Janaushadhi Pariyojana (PMBJP). This project uses only official, public government
data to answer two questions:

1. **Savings:** how much cheaper are Jan Aushadhi tablets and capsules than the government's maximum allowed
   (ceiling) price for the same medicine?
2. **Access:** how many Jan Aushadhi stores are there for every 1 lakh (100,000) people in each state?

Built with **Python, MySQL and SQL**. No patient or personal data is used.

---

## 1. Data

All four files are in `data/`, converted from the official documents and checked as listed.

| File | What it contains | Official source | How it was checked |
|---|---|---|---|
| `ja_products.csv` | 2,445 Jan Aushadhi products with MRP (price per pack, tax included) | Jan Aushadhi product list, janaushadhi.gov.in (CSV, downloaded 2 Nov 2026) | No duplicate drug codes; every price is a number |
| `ceiling_prices.csv` | Ceiling prices of 767 essential medicines, per tablet/capsule/ml, **before GST**, effective 1 Apr 2026 | NPPA order S.O. 1575(E), 25 Mar 2026: https://nppa.gov.in/uploads/tender/0fd8be342c35d5a46a13b281cadc5e4f.pdf | All 767 rows, Sl. No. 1–767, no gaps; `sl_no` is the serial number in the order |
| `kendra_counts_district.csv` | Number of stores in each of 767 districts, as on 31 Dec 2025 | Annexure-I, PIB/Department of Pharmaceuticals, Feb 2026: https://static.pib.gov.in/WriteReadData/specificdocs/documents/2026/feb/doc202626781301.pdf | Total = 17,990 stores, same as the document; districts per state match its Annexure-II |
| `population.csv` | Population of today's 36 states and union territories | Census 2011, "Basic Population Figures of India, States and Districts", censusindia.gov.in | Adds up to India's 2011 total of 1,21,08,54,977 |

Population adjustments for today's states (each one is written in the `source` column): Telangana and Andhra
Pradesh use their official 2011 figures (3,50,03,674 and 4,95,77,103); Ladakh = Leh + Kargil districts, taken
out of Jammu and Kashmir; Dadra and Nagar Haveli + Daman and Diu are combined (merged in 2020).

---

## 2. How it works

```
data/*.csv ──► load_data.py ──► MySQL database ──► match_medicines.py ──► run_analysis.py ──► results/*.csv
               (clean + load)                       (pair each Jan Aushadhi     (SQL questions)
                                                     medicine with its
                                                     government ceiling price)
```

**Comparing like with like**
- Prices are compared **per tablet or capsule**: Jan Aushadhi MRP is per pack, so it is divided by the pack
  size (`10's` = 10 tablets).
- Ceiling prices **exclude GST** but MRP **includes** it, so GST is added to the ceiling price (5%, the rate for
  most medicines since 22 Sep 2025; set in `config.ini`).
- Only tablets and capsules are compared. Liquids, creams and injections come in packs that can't be compared
  per unit.
- **Saving % = (ceiling price with GST − Jan Aushadhi price) ÷ ceiling price with GST × 100.**

**Matching the same medicine in two lists** (`match_medicines.py`), in three passes:
1. **auto:** same medicine name, strength, form (tablet/capsule) and release type (e.g. SR, ER, chewable).
2. **auto-salt:** the same after ignoring salt words one list often leaves out ("Metformin Hydrochloride" =
   "Metformin"). Sodium and potassium salts are never ignored, because e.g. diclofenac sodium and diclofenac
   potassium are different products.
3. **manual:** a person's decision, written in `data/manual_matches.csv` (`drug_code, ceiling_id`; `0` means
   "no equivalent").

The same molecule sometimes has two names; these are joined in `normalize.py` (`NAME_SYNONYMS`): aspirin =
acetylsalicylic acid, frusemide = furosemide, levothyroxine = thyroxine, mesalazine/mesalamine =
5-aminosalicylic acid. Every rule is plain text handling, with no machine learning, so each decision can be
explained.

---

## 3. Run it

**Install:** Python 3, MySQL Server with MySQL Workbench. (On Windows, type `py` if `python` doesn't work.)

```
pip install -r requirements.txt
```

1. In MySQL Workbench, open `schema.sql` and run it. It creates the `jan_aushadhi` database and its tables.
2. Copy `config.example.ini` to `config.ini` and type your MySQL password into it.
3. Run, in this order (each one is safe to run again):
   ```
   python load_data.py
   python match_medicines.py
   python run_analysis.py
   ```

Without `config.ini` the scripts use a small local test database instead of MySQL and say so. This is handy for
a first try, but use MySQL for the real results.

---

## 4. Checks before reporting

Before reporting, I reviewed every uncertain match, hand-checked 30 random automatic matches, and confirmed the GST rate. Details are in CHECKS.md.

---

## 5. Output files (in `results/`)

| File | What it shows |
|---|---|
| `Q1.csv` | How many products have a price, how many can be compared, how many were matched |
| `Q2.csv` | **Average saving %**, lowest and highest saving, how many cost less than half the ceiling |
| `Q3.csv` | Average saving by medicine group (groups with at least 5 matched medicines) |
| `Q4.csv` | Every matched medicine: Jan Aushadhi price, ceiling price with GST, saving %, how it was matched |
| `Q5.csv` | Data check: medicines priced above the ceiling (should be empty) |
| `Q6.csv` | **Stores per lakh people, by state**, lowest first |
| `Q7.csv` | Optional district view; empty unless district populations are added |
| `no_ceiling_equivalent.csv` | Products with no ceiling price at all (mostly combination tablets), so nothing to compare |
| `zero_mrp_products.csv` | 345 products listed with MRP 0 (no price published); left out |
| `review_needed.csv` | Products that needed a manual decision (all 116 now decided in `data/manual_matches.csv`) |
| `auto_match_check.csv` | 30 random automatic matches, checked by hand (30 of 30 correct) |

---

## 6. Results

222 Jan Aushadhi tablets and capsules matched to NPPA ceiling prices. Median saving 68% below the GST-inclusive ceiling; 198 cost less than half. A hand-check of 30 random automatic matches found 30 correct; reviewing 116 unclear cases found one parsing error (Trihexyphenidyl), now fixed. Stores per lakh people range from 0.5 (Jharkhand) to 5.1 (Kerala); Telangana has 0.6. Details in CHECKS.md.

---

## 7. Limitations

- The saving is measured against the **ceiling (maximum allowed) price**, not every brand's actual price.
  Many brands sell below the ceiling, so the saving against a cheap brand is smaller.
- Only medicines under price control have a ceiling price, so many Jan Aushadhi products can't be compared.
- GST is added at 5% for every medicine. A few life-saving medicines are GST-free; for them the saving
  shown is about 1–2 percentage points too high.
- Tablets and capsules only.
- Store counts are from December 2025 but population is from 2011. India's population has grown since, so the
  true number of stores per lakh people is lower than shown. The ranking between states is still meaningful.
- A store being open doesn't show whether it has a medicine in stock.

## 8. Next steps

- District-level access for Telangana and Andhra Pradesh, using the states' official populations for
  their present-day districts.
- Compare with real brand prices for 10 common medicines.
- Repeat with the next price order to see how prices change.



---

## Project files

| File | Purpose |
|---|---|
| `schema.sql` | Creates the MySQL database and tables |
| `load_data.py` | Checks the files in `data/` and loads them |
| `normalize.py` | The text rules that clean medicine names, strengths and pack sizes |
| `match_medicines.py` | Pairs each Jan Aushadhi medicine with its ceiling price |
| `analysis.sql` | The SQL questions (Q1–Q7) |
| `run_analysis.py` | Runs `analysis.sql` and saves the results |
| `db.py` | Connects to MySQL (or the local test database) |
| `config.example.ini` | Template for the MySQL settings and the GST rate |
