# Checks done before reporting (15 Nov 2026)

These are the three checks from README section 4. Komal: open each file, re-check a few rows
yourself, and make sure you can explain every decision before you quote any number.

## 1. Hand-check of 30 random automatic matches -> 30 of 30 correct
File: `results/auto_match_check.csv` (column `correct (yes/no)`).
For each row: same medicine (allowing salt names, e.g. Valganciclovir Hydrochloride = Valganciclovir),
same strength, same form (tablet/capsule). The per-unit prices were then recomputed by hand from
`data/ja_products.csv` (MRP / pack size) and `data/ceiling_prices.csv` (ceiling x 1.05 GST) and all 30
agree with `results/Q4.csv`. Pack sizes like "30's Bottle", "28's Bottle" and "100's" were all parsed correctly.

## 2. Review of the 116 medicines that needed a human decision -> 25 matched, 91 no equivalent
File: `data/manual_matches.csv` (each row has a `note` with the reason).

- **One error found and fixed:** Trihexyphenidyl 2 mg (drug code 1087) was marked "no ceiling entry with the same
  strength", but the ceiling list has Trihexyphenidyl Tablet 2mg (sl_no 740). The product name contains a second
  name in brackets, "(Benzhexol Hydrochloride Tablets IP 2mg)", which confused the strength parser. Fixed by a
  manual match. A good next step is to strip bracketed alternate names in `normalize.py`.
- **The 6 "YOU DECIDE" rows:**
  | Code | Product | Decision | Why |
  |---|---|---|---|
  | 11 | Diclofenac gastro-resistant 50 mg | match 250 | ordinary diclofenac sodium 50 mg tablets are enteric coated as standard |
  | 492 | Sulfasalazine delayed release 500 mg | no match (0) | plain and enteric-coated (EN) sulfasalazine are both sold and are different products; ceiling entry doesn't say which -> conservative |
  | 1059 | Sodium valproate EC 200 mg | match 679 | ordinary sodium valproate tablets are always enteric coated (stomach irritant) |
  | 1060 | Sodium valproate GR 300 mg | match 677 | same reason |
  | 1806 | Sodium valproate 200 + valproic acid 87 mg CR | match 682 | = 300 mg sodium valproate equivalent (NPPA note g); CR = Modified Release 300 mg |
  | 1807 | Sodium valproate 333 + valproic acid 145 mg CR | match 680 | = 500 mg equivalent; Modified Release 500 mg |
- **Other suggestions accepted after checking:** slow-release products were only matched where the ceiling list
  has a modified-release entry of the same strength (e.g. Metformin SR 1000 -> MR 1000, but Metformin PR 500 -> no
  match because only the ordinary 500 mg tablet has a ceiling); combination tablets (e.g. Amitriptyline +
  Chlordiazepoxide) are never matched to single-drug ceilings; Thyroxine = Levothyroxine.

## 3. GST rate -> 5% confirmed
Since 22 Sep 2025 all drugs and medicines are taxed at a concessional 5% except a list of about 33 life-saving
drugs at nil (GST Council FAQ, gstcouncil.gov.in/sites/default/files/2025-09/faq.pdf). Sensitivity check: with
0% GST for every medicine, the median saving falls only from about 68% to 66%, so the conclusion does not depend
on the GST assumption.

## Q5 data check
No Jan Aushadhi medicine is priced above its ceiling price (Q5 is empty), which supports the matches and pack sizes.
