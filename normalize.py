"""Turns messy medicine names, strengths and pack sizes into comparable values.
Every rule here is simple string handling (no machine learning) so you can explain each one."""
import re

FORM_WORDS = {
    "tablet": ["tablet", "tablets", "tab", "tabs"],
    "capsule": ["capsule", "capsules"],          # not "cap": "Knee Cap", "measuring cap"
}
# Release types change the product, so they are KEPT in the key (metformin SR is not metformin)
RELEASE = {
    "sr": ["sr", "sustained release"], "er": ["er", "xr", "extended release"],
    "pr": ["pr", "prolonged release"], "mr": ["mr", "modified release"], "cr": ["cr", "controlled release"],
    "dr": ["dr", "delayed release", "enteric coated", "ec", "gastro resistant"],
    "odt": ["odt", "orally disintegrating", "mouth dissolving", "md"],
    "chew": ["chewable"],
}
# Words that don't change the product (pharmacopoeia marks, coating, packaging)
NOISE = ["soft gelatin", "soft gel", "softgel", "i.p.", "i.p", "ip", "b.p.", "bp", "u.s.p.", "usp", "film coated", "film-coated", "fc", "uncoated",
         "dispersible", "each", "contains", "strip", "pack", "of", "with", "the", "equivalent", "eq", "to"]
# Only salt names that are written inconsistently but mean the same product in both lists.
# Do NOT add sodium/potassium/calcium here: e.g. diclofenac sodium and diclofenac potassium are different products.
# Different names for the same molecule in the two lists
NAME_SYNONYMS = {"aspirin": "acetylsalicylic acid", "acetaminophen": "paracetamol", "vitamin b12": "cyanocobalamin",
                 "frusemide": "furosemide", "levothyroxine": "thyroxine",
                 "mesalazine": "aminosalicylic acid", "mesalamine": "aminosalicylic acid",
                 "amino salicylic acid": "aminosalicylic acid", "disproxil": "disoproxil"}
SALT_SYNONYMS = {"hcl": "hydrochloride", "besilate": "besylate", "sulfate": "sulphate", "mesilate": "mesylate"}
# Salt words that are often written in one list and left out in the other ("Metformin" vs "Metformin Hydrochloride").
# Matches made by dropping them are labelled 'auto-salt' and must be spot-checked by hand.
DROPPABLE_SALTS = ["hydrochloride", "besylate", "maleate", "mesylate", "fumarate", "succinate", "tartrate",
                   "sulphate", "citrate", "phosphate", "monohydrate", "dihydrate", "trihydrate", "anhydrous"]
STATE_ALIASES = {"orissa": "odisha", "pondicherry": "puducherry", "uttaranchal": "uttarakhand",
                 "nct of delhi": "delhi", "national capital territory of delhi": "delhi"}

UNIT_RE = r"(mg|mcg|µg|ug|gm|g|iu|ml|%)"
STRENGTH_RE = re.compile(r"(\d+(?:\.\d+)?)\s*" + UNIT_RE + r"(?![a-z])", re.I)

def _num(x):
    return ("%.4f" % x).rstrip("0").rstrip(".")

def strength_key(text):
    """'Metformin 0.5 g' -> '500mg'; combos sorted: '12.5mg+40mg'."""
    out = []
    for value, unit in STRENGTH_RE.findall(text or ""):
        v, u = float(value), unit.lower()
        if u in ("g", "gm"): v, u = v * 1000, "mg"
        elif u in ("mcg", "µg", "ug"): v, u = v / 1000, "mg"
        out.append(_num(v) + u)
    return "+".join(sorted(out))

def form_of(*texts):
    """Form from the FIRST text that names one (pass the medicine name first, then pack/unit text).
    Liquids, gels, kits, inhalers etc. are 'other' even if a later text says 'measuring cap'."""
    for text in texts:
        t = " " + (text or "").lower() + " "
        if re.search(r"\b(syrup|suspension|solution|injection|infusion|drops|gel|cream|ointment|lotion|"
                     r"powder for|inhalation|inhaler|kit|spray|sachet|granules)\b", t):
            return "other"
        for form, words in FORM_WORDS.items():
            if any(re.search(r"\b" + w + r"\b", t) for w in words):
                return form
    return "other"

def release_of(text):
    t = (text or "").lower().replace("-", " ")                # "Prolonged-release" = "prolonged release"
    t = " " + re.sub(r"\(.*?\)", " ", t) + " "               # ignore notes in brackets, e.g. "(including chewable tablets)"
    for key, words in RELEASE.items():
        if any(re.search(r"\b" + re.escape(w) + r"\b", t) for w in words):
            return key
    return ""

def name_key(text):
    """'Telmisartan 40mg + Hydrochlorothiazide 12.5mg Tablets IP' -> 'hydrochlorothiazide+telmisartan'."""
    t = (text or "").lower().replace("-", " ")
    rel = release_of(t)
    t = STRENGTH_RE.sub(" ", t)
    t = re.sub(r"\(.*?\)", " ", t)
    for words in list(FORM_WORDS.values()) + list(RELEASE.values()):
        for w in sorted(words, key=len, reverse=True):
            t = re.sub(r"\b" + re.escape(w) + r"\b", " ", t)
    for w in sorted(NOISE, key=len, reverse=True):  # (splitting on 'and' happens below)
        t = re.sub(r"(?<![a-z])" + re.escape(w) + r"(?![a-z])", " ", t)
    for a, b in SALT_SYNONYMS.items():
        t = re.sub(r"\b" + a + r"\b", b, t)
    for a, b in NAME_SYNONYMS.items():
        t = re.sub(r"\b" + a + r"\b", b, t)
    parts = re.split(r"\+|/|,|&|\band\b", t)
    # dict.fromkeys removes repeated words: "amlodipine besylate eq. to amlodipine" -> "amlodipine besylate"
    molecules = sorted({" ".join(dict.fromkeys(re.sub(r"[^a-z ]", " ", p).split())) for p in parts} - {""})
    return "+".join(molecules) + ("|" + rel if rel else "")

def without_salts(key):
    """'metformin hydrochloride|sr' -> 'metformin|sr' (used only for the second, labelled matching pass)."""
    names, _, rel = key.partition("|")
    out = []
    for m in names.split("+"):
        words = [w for w in m.split() if w not in DROPPABLE_SALTS]
        out.append(" ".join(words) if words else m)
    return "+".join(sorted(out)) + ("|" + rel if rel else "")

def molecule_family(key):
    """Loose key used ONLY to decide whether a product goes to hand review: first word of each molecule.
    'diclofenac sodium|dr' -> 'diclofenac'. Never used for automatic matching."""
    names = key.split("|")[0]
    out = []
    for m in names.split("+"):
        words = [w for w in m.split() if len(w) > 1]          # skip 'n' in 'n acetylcysteine', 's' in 's amlodipine'
        if words: out.append(words[0])
    fam = "+".join(sorted(out))
    # 'sodium valproate' / 'sodium bicarbonate': the first word is the salt, so use the first two words
    return fam if not fam.startswith(("sodium", "potassium", "calcium", "magnesium", "vitamin")) else names.split("+")[0][:30]

def pack_count(unit_size):
    """"10's" -> 10, '1x10' -> 10, '3 x 10 Tablets' -> 30, 'Strip of 15' -> 15. None if unclear."""
    t = (unit_size or "").lower().replace("×", "x")
    m = re.search(r"(\d+)\s*x\s*(\d+)", t)
    if m: return int(m.group(1)) * int(m.group(2))
    if re.search(r"\d\s*(ml|gm|g|mg|kg|l)\b", t): return None   # liquids, creams, powders: not per-unit comparable
    nums = re.findall(r"\d+", t)
    return int(nums[0]) if len(nums) == 1 and int(nums[0]) > 0 else None

def units_in(unit_text):
    """NPPA 'unit' column: '1 Tablet' -> 1, '10 Tablets' -> 10, 'Tablet' -> 1."""
    nums = re.findall(r"\d+", unit_text or "")
    return int(nums[0]) if nums and int(nums[0]) > 0 else 1

def _title(t):
    small = {"and", "of", "the"}
    return " ".join(w if (i and w in small) else w.capitalize() for i, w in enumerate(t.split()))

def state_key(s):
    """'TELANGANA' -> 'Telangana', 'Jammu & Kashmir' -> 'Jammu and Kashmir', 'Orissa' -> 'Odisha'."""
    t = " ".join((s or "").lower().replace("&", "and").replace(".", " ").split())
    return _title(STATE_ALIASES.get(t, t))

def district_key(s):
    """'BHADRADRI-KOTHAGUDEM ' -> 'Bhadradri Kothagudem'."""
    return _title(" ".join(re.sub(r"[^a-z ]", " ", (s or "").lower()).split()))
