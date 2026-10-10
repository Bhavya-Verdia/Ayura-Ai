"""Build `data/knowledge_base/diet_micronutrients.json` from the published composition tables.

The diet library carried energy, protein, carbohydrate, fat and fibre and nothing
else, so the plan could state a sodium limit, a renal potassium caution and an
anaemia note and check none of them. This adds sodium, potassium, phosphorus,
calcium, iron, folate, zinc, vitamin B12 and vitamin D per 100 g for every food a
plan can name. Iodine is not here: in an Indian kitchen it comes from iodised salt,
and `diet_nutrition` counts it from the salt component.

Every value comes from a row chosen BY HAND below, never from a name match:
  ("sr", fdc_id)            USDA FoodData Central, SR Legacy (2018-04)
  ("ifct", code)            Indian Food Composition Tables 2017 (NIN)
  ("scaled", kind, id, f)   one row scaled to the state the library holds — a cooked
                            grain from its dry flour, lemon water from lemon juice
  ("recipe", [...])         a prepared dish from its raw ingredients, salt included
  ("none", reason)          no trustworthy source; the plan treats it as unmeasured

Choices that matter:
  * cooked pulses and grains are the "without salt" rows, and rice and flour the
    UNENRICHED ones — Indian rice and atta are not iron- and folate-fortified the
    way US "enriched" rice is, and salt is counted where the cook adds it;
  * plant milks are the UNFORTIFIED rows: Indian soy and almond drinks are mostly
    sold without the calcium, B12 and vitamin D a US carton carries, so counting it
    would close a vegan's calcium gap with fortification they may not be buying;
  * IFCT 2017 reports neither B12 nor vitamin D. Plant foods carry none of either,
    so a plant row from IFCT is 0 for both; paneer takes them from a fresh
    acid-set whole-milk cheese (`VITAMINS_FROM`);
  * Indian foods come from IFCT where it has them: amla is Emblica (IFCT E021),
    not the European gooseberry, whose numbers the library's macros came from.

    python scripts/build_diet_micronutrients.py            # write the table
    python scripts/build_diet_micronutrients.py --check    # is it in sync?
    python scripts/build_diet_micronutrients.py extract SR_DIR IFCT_CSV

The rows `MAP` cites are kept in `diet_micronutrient_sources.json` beside this
script, so the table builds and checks without the source datasets (~100 MB). Run
`extract` after adding or changing a row in `MAP`: SR_DIR is the unzipped
https://fdc.nal.usda.gov/fdc-datasets/FoodData_Central_sr_legacy_food_csv_2018-04.zip
and IFCT_CSV is compositions/index.csv from the ifct2017 dataset
(github.com/nodef/ifct2017).
"""
import csv
import json
import sys
from pathlib import Path

OUT = Path(__file__).resolve().parents[1] / "data" / "knowledge_base" / "diet_micronutrients.json"
SOURCES = Path(__file__).resolve().parent / "diet_micronutrient_sources.json"
KEYS = ("sodium_mg", "potassium_mg", "phosphorus_mg", "calcium_mg", "iron_mg", "folate_ug",
        "zinc_mg", "b12_ug", "vitd_ug")
_SR_IDS = {"1093": "sodium_mg", "1092": "potassium_mg", "1091": "phosphorus_mg",
           "1087": "calcium_mg", "1089": "iron_mg", "1190": "folate_dfe", "1177": "folate_total",
           "1095": "zinc_mg", "1178": "b12_ug", "1114": "vitd_ug",
           "1008": "kcal", "1003": "protein"}
_IFCT_COLS = {"na": "sodium_mg", "k": "potassium_mg", "p": "phosphorus_mg", "ca": "calcium_mg",
              "fe": "iron_mg", "folsum": "folate_ug", "zn": "zinc_mg"}

S, I = "sr", "ifct"
RICE_RAW, URAD_RAW, TOOR_RAW, CHANA_RAW = ("sr", "169756"), ("sr", "174259"), ("sr", "172436"), ("sr", "173756")
SALT, OIL = ("sr", "173468"), ("sr", "171410")

MAP = {
    # spices
    "turmeric": (S, "172231"), "cumin_jeera": (S, "170923"), "coriander_dhania": (S, "170922"),
    "fennel_saunf": (S, "171323"), "cardamom_elaichi": (S, "170919"),
    "cinnamon_dalchini": (S, "171320"), "black_pepper": (S, "170931"),
    "ginger_dry_saunth": (S, "170926"), "fenugreek_seeds_methi": (S, "171324"),
    "ajwain": (I, "G029"),
    # oils and fats
    "sesame_oil": (S, "171016"), "coconut_oil": (S, "171412"), "mustard_oil": (S, "172337"),
    "ghee_oil": (S, "173412"), "olive_oil": (S, "171413"), "ghee": (S, "173412"),
    "groundnut_oil": (S, "171410"), "sunflower_oil": (S, "171017"), "rice_bran_oil": (S, "171013"),
    # beverages
    "green_tea": (S, "171917"), "tulsi_tea": (S, "173232"), "ginger_tea": (S, "173232"),
    "coconut_water": (S, "170174"), "lemon_water": ("scaled", S, "167747", 0.27),
    # dairy and plant milks
    "milk_full_fat": (S, "172217"), "curd_yogurt": (S, "171284"),
    "buttermilk_chaas": ("scaled", S, "170886", 0.5), "paneer": (I, "L003"), "butter": (S, "173430"),
    "whey": (S, "171282"), "cream": (S, "170859"), "cottage_cheese": (S, "172179"),
    "lassi": ("scaled", S, "171284", 0.85), "coconut_milk": (S, "170172"),
    # Plant drinks: unfortified, scaled to the energy the library's row states — a
    # drink of that energy holds that share of its source.
    "almond_milk": ("scaled", S, "170567", 0.026), "soy_milk": (S, "172446"),
    "oat_milk": ("scaled", S, "173904", 0.113),
    "coconut_yogurt": ("scaled", S, "170172", 0.42),
    "vegan_paneer_tofu": (S, "172476"),
    # Inactive dried Saccharomyces, counted UNFORTIFIED: the B12 some brands add is
    # not counted, so a vegan is never told a sprinkle covers it.
    "nutritional_yeast": (S, "175043"),
    "coconut_cream": (S, "170580"), "cashew_cream": ("scaled", S, "170162", 0.45),
    "flax_milk": ("scaled", S, "169414", 0.047),
    # grains (cooked unless stated)
    "basmati_rice": (S, "169757"), "white_rice": (S, "169757"), "brown_rice": (S, "169704"),
    "roti_whole_wheat": ("scaled", S, "168893", 0.87), "paratha": ("scaled", S, "168893", 0.75),
    "poha": ("scaled", I, "A011", 0.37), "rice_flakes": (I, "A011"),
    "upma_rava": ("scaled", S, "169715", 0.40), "oats": (S, "173905"), "quinoa": (S, "168917"),
    "millet_bajra": (S, "168871"), "millet_jowar": ("scaled", I, "A005", 0.34),
    "daliya": (S, "170287"), "semolina_rava": ("scaled", S, "169715", 0.28),
    "bread_whole_wheat": (S, "172688"), "barley": (S, "170285"), "amaranth": (S, "170683"),
    "buckwheat": (S, "170686"), "corn": (S, "169999"),
    "sabudana": ("scaled", S, "169717", 0.36),
    # pulses
    "moong_dal_yellow": (S, "174257"), "moong_dal_green": (S, "174257"),
    "sprouted_moong": (S, "169957"), "masoor_dal": (S, "172421"), "lentils_brown": (S, "172421"),
    "chana_dal": (S, "173757"), "chhole": (S, "173757"), "chickpea_flour_besan": (S, "174288"),
    "toor_dal": (S, "172437"), "urad_dal": (S, "172427"), "black_eyed_peas": (S, "173759"),
    "green_peas": (S, "170420"), "rajma": (S, "173740"), "kidney_beans": (S, "173740"),
    "black_beans": (S, "173735"),
    # Defatted soy flour is what the chunks are extruded from; hydrated ~3x.
    "soya_chunks": ("scaled", S, "174275", 0.32),
    "tofu_firm": (S, "172476"), "tempeh": (S, "174272"), "edamame": (S, "168411"),
    "peanuts": (S, "172430"),
    # nuts and seeds
    "almonds": (S, "170567"), "walnuts": (S, "170187"), "cashews": (S, "170162"),
    "pistachios": (S, "170184"), "peanuts_roasted": (S, "173806"),
    "sesame_seeds_til": (S, "170150"), "flax_seeds": (S, "169414"),
    "pumpkin_seeds": (S, "170556"), "melon_seeds_magaz": (S, "169407"),
    "watermelon_seeds": (S, "169407"),
    "fox_nuts_makhana": ("none", "Euryale ferox is in neither SR Legacy nor IFCT 2017, and "
                                 "published figures for popped makhana disagree up to ten-fold "
                                 "(potassium 42 to 500 mg/100 g)"),
    "sunflower_seeds": (S, "170562"), "chia_seeds": (S, "170554"), "hemp_seeds": (S, "170148"),
    "pine_nuts": (S, "170591"),
    # fruits
    "banana": (S, "173944"), "apple": (S, "171688"), "mango": (S, "169910"),
    "papaya": (S, "169926"), "pomegranate": (S, "169134"), "amla": (I, "E021"),
    "coconut": (S, "170169"), "dates": (S, "168191"), "figs": (S, "173021"),
    "guava": (S, "173044"), "watermelon": (S, "167765"), "orange": (S, "169097"),
    "mosambi_sweet_lime": (I, "E034"), "pear": (S, "169118"), "jamun": (S, "168150"),
    "grapes": (S, "174683"), "chikoo_sapota": (I, "E060"), "pineapple": (S, "169124"),
    "kiwi": (S, "168153"), "strawberry": (S, "167762"),
    # vegetables
    "spinach": (S, "168462"), "palak": (S, "168462"), "methi_fenugreek_leaves": (I, "C020"),
    "broccoli": (S, "169967"), "cauliflower": (S, "169986"), "cabbage": (S, "169975"),
    "carrot": (S, "170393"), "beetroot": (S, "169145"), "potato": (S, "170026"),
    "sweet_potato": (S, "168482"), "yam": (S, "170071"), "colocasia_arbi": (S, "169308"),
    "lotus_stem": (S, "169250"), "bottle_gourd": (I, "D007"), "ridge_gourd": (I, "D068"),
    "bitter_gourd_karela": (S, "168393"), "ivy_gourd_tindora": (I, "D055"),
    "pumpkin": (S, "168448"), "cucumber": (S, "168409"), "zucchini": (S, "169291"),
    "onion": (S, "170000"), "garlic": (S, "169230"), "ginger": (S, "169231"),
    "capsicum_bell_pepper": (S, "170108"), "tomato": (S, "170457"),
    "drumstick_moringa": (S, "170483"), "raw_banana": (I, "D063"), "jackfruit": (S, "174687"),
    "raw_mango": (S, "169910"), "raw_papaya": (S, "169926"), "french_beans": (S, "169961"),
    "cluster_beans_gavar": (I, "D039"), "asparagus": (S, "168389"), "mushroom": (S, "169251"),
    "corn_sweet": (S, "169999"),
    # cooking ingredients (diet_nutrition.EXTRAS)
    "sugar": (S, "169655"), "jaggery": (I, "I001"), "honey": (S, "169640"),
    "raisins": (S, "168165"), "wheat_flour_atta": (S, "168893"), "maida": (S, "169761"),
    "ragi_flour": (I, "A010"), "jowar_flour": (I, "A005"), "bajra_flour": (I, "A003"),
    "rice_raw": (S, "169756"), "vermicelli": (S, "168927"),
    "sattu": ("scaled", S, "173756", 0.98),
    "idli": ("recipe", [(RICE_RAW, 30), (URAD_RAW, 10), (SALT, 0.8)]),
    "dosa": ("recipe", [(RICE_RAW, 28), (URAD_RAW, 9), (OIL, 4), (SALT, 0.8)]),
    "sambar": ("recipe", [(TOOR_RAW, 7), (("sr", "170483"), 10), (("sr", "168448"), 10),
                          (("sr", "170457"), 10), (("sr", "167763"), 2), (OIL, 1.5), (SALT, 1.0)]),
    "coconut_chutney": ("recipe", [(("sr", "170169"), 40), (CHANA_RAW, 8), (OIL, 1), (SALT, 1.0)]),
    "okra_bhindi": (S, "169260"), "brinjal_baingan": (S, "169228"), "tinda": (I, "D073"),
    "parwal": (I, "D060"), "green_chilli": (S, "170497"), "lemon_juice": (S, "167747"),
    "salt": (S, "173468"), "rock_salt": (S, "173468"), "mustard_seeds": (S, "170929"),
    "hing": (I, "G019"),
    "curry_leaves": (I, "G010"), "coriander_leaves": (S, "169997"), "mint_leaves": (S, "173474"),
    "tamarind": (S, "167763"), "red_chilli_powder": (S, "171319"),
    "garam_masala": ("recipe", [(("sr", "170922"), 30), (("sr", "170923"), 30),
                                (("sr", "170931"), 15), (("sr", "170919"), 10),
                                (("sr", "171320"), 10), (("sr", "171321"), 5)]),
    "water": ("zero", "tap water"),
}


# IFCT 2017 has no B12 or vitamin D column. Animal foods take both from the SR row
# closest in kind; every other food from IFCT is a plant, which carries neither.
VITAMINS_FROM = {"paneer": ("sr", "170851")}      # ricotta, whole milk: fresh, acid-set
_VITAMINS = ("b12_ug", "vitd_ug")
# Foods of animal origin. A plant row with no reported B12 or vitamin D is 0 for it;
# an animal row with none reported stays unmeasured.
ANIMAL = {"milk_full_fat", "curd_yogurt", "buttermilk_chaas", "paneer", "butter", "whey",
          "cream", "cottage_cheese", "lassi", "ghee", "ghee_oil", "honey"}


def _load_sr(sr_dir: Path) -> dict:
    rows: dict = {}
    with open(sr_dir / "food_nutrient.csv") as f:
        for r in csv.DictReader(f):
            k = _SR_IDS.get(r["nutrient_id"])
            if k:
                rows.setdefault(r["fdc_id"], {})[k] = float(r["amount"])
    desc = {}
    with open(sr_dir / "food.csv") as f:
        for r in csv.DictReader(f):
            desc[r["fdc_id"]] = r["description"]
    out = {}
    for fid, v in rows.items():
        folate = v.get("folate_dfe", v.get("folate_total"))
        out[fid] = {"sodium_mg": v.get("sodium_mg"), "potassium_mg": v.get("potassium_mg"),
                    "phosphorus_mg": v.get("phosphorus_mg"), "calcium_mg": v.get("calcium_mg"),
                    "iron_mg": v.get("iron_mg"), "folate_ug": folate,
                    "zinc_mg": v.get("zinc_mg"), "b12_ug": v.get("b12_ug"),
                    "vitd_ug": v.get("vitd_ug"),
                    "kcal": v.get("kcal"), "protein": v.get("protein"),
                    "label": f"USDA SR Legacy {fid}: {desc.get(fid, '')}"}
    return out


def _load_ifct(path: Path) -> dict:
    out = {}
    with open(path) as f:
        for r in csv.DictReader(f):
            vals = {}
            for col, key in _IFCT_COLS.items():
                # The dataset stores every nutrient in GRAMS per 100 g: ragi's calcium
                # is 0.364, i.e. 364 mg. Minerals to mg, folate to micrograms.
                scale = 1e6 if key == "folate_ug" else 1e3
                try:
                    vals[key] = (round(float(r[col]) * scale, 3)
                                 if r.get(col) not in (None, "") else None)
                except ValueError:
                    vals[key] = None
            try:
                vals["kcal"] = round(float(r["enerc"]) / 4.184, 1)
            except (TypeError, ValueError):
                vals["kcal"] = None
            vals["protein"] = float(r["protcnt"]) if r.get("protcnt") else None
            vals["label"] = f"IFCT 2017 {r['code']}: {r['name']}"
            out[r["code"]] = vals
    return out


def _row(kind, ref, sr, ifct):
    src = sr if kind == "sr" else ifct
    if ref not in src:
        raise KeyError(f"{kind} {ref} not found")
    return src[ref]


def resolve(entry, sr, ifct) -> dict:
    kind = entry[0]
    if kind in ("sr", "ifct"):
        r = _row(kind, entry[1], sr, ifct)
        return {**{k: r.get(k) for k in KEYS}, "source": r["label"]}
    if kind == "scaled":
        _, k2, ref, f = entry
        r = _row(k2, ref, sr, ifct)
        return {**{k: (None if r.get(k) is None else round(r[k] * f, 3)) for k in KEYS},
                "source": f"{r['label']} × {f} (cooked or diluted state)"}
    if kind == "recipe":
        tot = dict.fromkeys(KEYS, 0.0)
        parts = []
        for (k2, ref), grams in entry[1]:
            r = _row(k2, ref, sr, ifct)
            for k in KEYS:
                tot[k] += (r.get(k) or 0.0) * grams / 100
            parts.append(f"{grams} g {r['label'].split(': ', 1)[-1]}")
        return {**{k: round(v, 3) for k, v in tot.items()},
                "source": "recipe per 100 g: " + "; ".join(parts)}
    if kind == "zero":
        return {**dict.fromkeys(KEYS, 0.0), "source": entry[1]}
    return {**dict.fromkeys(KEYS, None), "source": f"not available — {entry[1]}"}


def cited() -> set:
    """Every (kind, ref) a row of `MAP` reads."""
    out = set()
    for entry in MAP.values():
        if entry[0] in ("sr", "ifct"):
            out.add((entry[0], entry[1]))
        elif entry[0] == "scaled":
            out.add((entry[1], entry[2]))
        elif entry[0] == "recipe":
            out.update(ref for ref, _ in entry[1])
    out.update(VITAMINS_FROM.values())
    return out


def extract(sr_dir: Path, ifct_csv: Path) -> dict:
    """The cited rows only, from the full datasets."""
    full = {"sr": _load_sr(sr_dir), "ifct": _load_ifct(ifct_csv)}
    out: dict = {"sr": {}, "ifct": {}}
    for kind, ref in sorted(cited()):
        row = _row(kind, ref, full["sr"], full["ifct"])
        out[kind][ref] = {k: row.get(k) for k in (*KEYS, "label")}
    return out


def build(sources: dict | None = None) -> dict:
    src = sources or json.loads(SOURCES.read_text())
    out = {}
    for fid, entry in sorted(MAP.items()):
        row = resolve(entry, src["sr"], src["ifct"])
        if fid in VITAMINS_FROM:
            kind, ref = VITAMINS_FROM[fid]
            v = _row(kind, ref, src["sr"], src["ifct"])
            for k in _VITAMINS:
                row[k] = v.get(k)
            row["source"] += f"; B12 and vitamin D from {v['label']}"
        elif fid not in ANIMAL and row["sodium_mg"] is not None:
            for k in _VITAMINS:
                if row[k] is None:
                    row[k] = 0.0
        out[fid] = row
    return out


def render(data: dict) -> str:
    return json.dumps(data, indent=1, sort_keys=True) + "\n"


if __name__ == "__main__":
    if sys.argv[1:2] == ["extract"]:
        SOURCES.write_text(json.dumps(extract(Path(sys.argv[2]), Path(sys.argv[3])),
                                      indent=1, sort_keys=True) + "\n")
        print(f"wrote {SOURCES} ({len(cited())} rows)")
        sys.exit(0)
    text = render(build())
    if "--check" in sys.argv:
        same = OUT.exists() and OUT.read_text() == text
        print("in sync" if same else "OUT OF SYNC — rebuild")
        sys.exit(0 if same else 1)
    OUT.write_text(text)
    print(f"wrote {OUT} ({len(MAP)} foods)")
