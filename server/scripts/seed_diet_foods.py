import json
from pathlib import Path
from collections import defaultdict

BASE_DIR = Path(__file__).resolve().parent.parent
OUTPUT_DIR = BASE_DIR / "data" / "knowledge_base"
OUTPUT_FILE = OUTPUT_DIR / "diet_foods.json"

# List of foods by category to ensure we get exactly 150
CATEGORIES = {
    "grain": ["basmati_rice", "brown_rice", "white_rice", "roti_whole_wheat", "paratha", "poha", "upma", "oats", "quinoa", "millet_bajra", "millet_jowar", "daliya", "semolina_rava", "bread_whole_wheat", "rice_flakes", "barley", "amaranth", "buckwheat", "corn", "sabudana"],
    "legume": ["moong_dal_yellow", "moong_dal_green", "masoor_dal", "chana_dal", "toor_dal", "urad_dal", "rajma", "chhole", "black_eyed_peas", "sprouted_moong", "lentils_brown", "soya_chunks", "tofu_firm", "tempeh", "edamame", "peanuts", "chickpea_flour_besan", "green_peas", "kidney_beans", "black_beans"],
    "vegetable": ["spinach", "methi_fenugreek_leaves", "palak", "broccoli", "cauliflower", "cabbage", "carrot", "beetroot", "bottle_gourd", "ridge_gourd", "bitter_gourd_karela", "drumstick_moringa", "tomato", "onion", "garlic", "ginger", "capsicum_bell_pepper", "potato", "sweet_potato", "yam", "pumpkin", "raw_banana", "jackfruit", "mushroom", "corn_sweet", "french_beans", "cluster_beans_gavar", "ivy_gourd_tindora", "raw_papaya", "lotus_stem", "colocasia_arbi", "raw_mango", "cucumber", "zucchini", "asparagus"],
    "dairy": ["milk_full_fat", "curd_yogurt", "paneer", "ghee", "butter", "buttermilk_chaas", "whey", "cottage_cheese", "cream", "lassi"],
    "vegan_protein": ["coconut_milk", "almond_milk", "soy_milk", "oat_milk", "coconut_yogurt", "vegan_paneer_tofu", "nutritional_yeast", "coconut_cream", "cashew_cream", "flax_milk"],
    "fruit": ["banana", "apple", "mango", "papaya", "pomegranate", "amla", "coconut", "dates", "figs", "guava", "watermelon", "orange", "mosambi_sweet_lime", "pear", "chikoo_sapota", "jamun", "pineapple", "kiwi", "strawberry", "grapes"],
    "nut_seed": ["almonds", "walnuts", "cashews", "pistachios", "peanuts_roasted", "sunflower_seeds", "pumpkin_seeds", "chia_seeds", "flax_seeds", "sesame_seeds_til", "hemp_seeds", "melon_seeds_magaz", "pine_nuts", "fox_nuts_makhana", "watermelon_seeds"],
    "spice": ["turmeric", "cumin_jeera", "coriander_dhania", "fennel_saunf", "cardamom_elaichi", "cinnamon_dalchini", "black_pepper", "ginger_dry_saunth", "fenugreek_seeds_methi", "ajwain"],
    "oil": ["sesame_oil", "coconut_oil", "ghee_oil", "mustard_oil", "olive_oil"],
    "beverage": ["green_tea", "tulsi_tea", "ginger_tea", "coconut_water", "lemon_water"]
}

# Override specific nutrition macros per 100g (Calories, Protein, Carbs, Fat, Fiber)
NUTRITION_DB = {
    "basmati_rice": (130, 2.7, 28, 0.3, 0.4),
    "moong_dal_yellow": (105, 7.0, 19, 0.4, 4.1), # Cooked
    "moong_dal_green": (105, 7.0, 19, 0.4, 4.1),
    "paneer": (265, 18.0, 1.2, 20.0, 0),
    "ghee": (900, 0, 0, 100.0, 0),
    "spinach": (23, 2.9, 3.6, 0.4, 2.2),
    "palak": (23, 2.9, 3.6, 0.4, 2.2),
    "banana": (89, 1.1, 23.0, 0.3, 2.6),
    "almonds": (579, 21.0, 22.0, 50.0, 12.5),
    "tofu_firm": (76, 8.0, 2.0, 4.0, 0.3),
    "vegan_paneer_tofu": (76, 8.0, 2.0, 4.0, 0.3),
    "oats": (389, 17.0, 66.0, 7.0, 10.6),
    "chickpea_flour_besan": (387, 22.0, 58.0, 6.0, 10.0),

    # Other common values (approximations for 100g raw/standard)
    "brown_rice": (111, 2.6, 23, 0.9, 1.8),
    "white_rice": (130, 2.7, 28, 0.3, 0.4),
    "roti_whole_wheat": (297, 9.6, 46, 7.8, 6.8),
    "paratha": (330, 7.0, 42, 14.0, 4.5),
    "poha": (350, 6.6, 77.3, 1.2, 0.7),
    "quinoa": (120, 4.4, 21.3, 1.9, 2.8),
    "masoor_dal": (116, 9.0, 20.0, 0.4, 8.0),
    "rajma": (127, 8.7, 22.8, 0.5, 6.4),
    "chhole": (164, 8.9, 27.4, 2.6, 7.6),
    "soya_chunks": (345, 52.0, 33.0, 0.5, 13.0),
    "potato": (77, 2.0, 17.0, 0.1, 2.2),
    "sweet_potato": (86, 1.6, 20.1, 0.1, 3.0),
    "tomato": (18, 0.9, 3.9, 0.2, 1.2),
    "onion": (40, 1.1, 9.3, 0.1, 1.7),
    "garlic": (149, 6.4, 33.1, 0.5, 2.1),
    "ginger": (80, 1.8, 17.8, 0.7, 2.0),
    "milk_full_fat": (61, 3.2, 4.8, 3.3, 0),
    "curd_yogurt": (98, 9.0, 3.4, 4.3, 0),
    "butter": (717, 0.8, 0.1, 81.0, 0),
    "coconut_milk": (230, 2.3, 5.5, 24.0, 2.2),
    "apple": (52, 0.3, 13.8, 0.2, 2.4),
    "mango": (60, 0.8, 15.0, 0.4, 1.6),
    "walnuts": (654, 15.2, 13.7, 65.2, 6.7),
    "cashews": (553, 18.2, 30.2, 43.8, 3.3),
    "chia_seeds": (486, 16.5, 42.1, 30.7, 34.4),
    "sesame_oil": (884, 0, 0, 100.0, 0),
    "coconut_oil": (862, 0, 0, 100.0, 0),
    "olive_oil": (884, 0, 0, 100.0, 0),
}

# Generic macros by category (if not explicitly defined)
CATEGORY_MACROS = {
    "grain": (350, 10, 70, 2, 5),
    "legume": (340, 22, 60, 1.5, 15),
    "vegetable": (30, 2, 5, 0.2, 3),
    "dairy": (150, 8, 5, 10, 0),
    "vegan_protein": (50, 3, 4, 2, 1),
    "fruit": (50, 0.5, 13, 0.2, 2),
    "nut_seed": (600, 20, 20, 50, 10),
    "spice": (300, 10, 60, 5, 20),
    "oil": (900, 0, 0, 100, 0),
    "beverage": (10, 0, 2, 0, 0)
}

def get_name(item_id):
    return item_id.replace("_", " ").title()

def get_ayurvedic_props(item_id, category):
    # Default values based on category
    rasa = ["sweet"]
    virya = "cooling"
    vipaka = "sweet"
    vata, pitta, kapha = 0, 0, 0
    agni = "moderate"
    best_for = []

    # Base V/P/K mapping by category
    if category == "grain":
        vata, pitta, kapha = -1, -1, 1
        rasa = ["sweet"]
        virya = "cooling"
        agni = "moderate"
    elif category == "legume":
        vata, pitta, kapha = 1, -1, -1
        rasa = ["sweet", "astringent"]
        virya = "cooling"
        vipaka = "pungent"
        agni = "heavy"
    elif category == "vegetable":
        vata, pitta, kapha = 1, -1, -1
        rasa = ["bitter", "astringent"]
        virya = "cooling"
        vipaka = "pungent"
        agni = "easy"
    elif category == "dairy":
        vata, pitta, kapha = -1, -1, 1
        rasa = ["sweet"]
        virya = "cooling"
        vipaka = "sweet"
        agni = "heavy"
    elif category == "vegan_protein":
        vata, pitta, kapha = 0, -1, 1
        rasa = ["sweet"]
        virya = "cooling"
    elif category == "fruit":
        vata, pitta, kapha = -1, -1, 1
        rasa = ["sweet"]
        virya = "cooling"
        agni = "easy"
    elif category == "nut_seed":
        vata, pitta, kapha = -1, 1, 1
        rasa = ["sweet"]
        virya = "heating"
        agni = "heavy"
    elif category == "spice":
        vata, pitta, kapha = -1, 1, -1
        rasa = ["pungent"]
        virya = "heating"
        vipaka = "pungent"
        agni = "easy"
    elif category == "oil":
        vata, pitta, kapha = -1, 1, 1
        rasa = ["sweet"]
        virya = "heating"
        agni = "heavy"
    elif category == "beverage":
        vata, pitta, kapha = -1, -1, -1
        rasa = ["sweet", "astringent"]
        virya = "cooling"
        agni = "easy"

    # Specific Overrides
    name = item_id.lower()

    # VATA PACIFYING OVERRIDES (warm, oily, sweet, sour, salty, heavy, cooked)
    if name in ["ghee", "sesame_oil", "basmati_rice", "moong_dal_yellow", "moong_dal_green", "sweet_potato", "carrot", "beetroot", "banana", "dates", "mango", "almonds", "walnuts", "cashews"]:
        vata = -1
    # VATA AGGRAVATING
    if name in ["cabbage", "broccoli", "cauliflower", "bitter_gourd_karela", "watermelon", "kidney_beans", "rajma", "chhole"]:
        vata = 1

    # PITTA PACIFYING
    if name in ["coconut", "cucumber", "spinach", "palak", "basmati_rice", "moong_dal_yellow", "moong_dal_green", "apple", "pear", "coriander_dhania", "fennel_saunf", "cardamom_elaichi", "coconut_milk", "ghee", "coconut_water"]:
        pitta = -1
        virya = "cooling"
    # PITTA AGGRAVATING
    if name in ["garlic", "onion", "tomato", "mustard_oil", "sesame_oil", "lemon_water", "ginger", "black_pepper", "curd_yogurt", "buttermilk_chaas"]:
        pitta = 1
        virya = "heating"

    # KAPHA PACIFYING
    if name in ["millet_bajra", "millet_jowar", "barley", "moong_dal_yellow", "moong_dal_green", "bitter_gourd_karela", "bottle_gourd", "ridge_gourd", "ginger", "black_pepper", "turmeric", "apple", "pomegranate", "honey"]:
        kapha = -1
    # KAPHA AGGRAVATING
    if name in ["wheat", "bread_whole_wheat", "curd_yogurt", "paneer", "cheese", "avocado", "banana", "dates", "coconut_milk", "sweet_potato"]:
        kapha = 1

    # RASA
    if "lemon" in name or "tamarind" in name or "tomato" in name or "curd" in name:
        rasa = ["sour"]
    elif "ginger" in name or "garlic" in name or "onion" in name or "pepper" in name or "mustard" in name:
        rasa = ["pungent"]
    elif "bitter" in name or "turmeric" in name or "methi" in name or "spinach" in name or "palak" in name:
        rasa = ["bitter"]

    # VIRYA
    if name in ["ginger", "garlic", "onion", "mustard_oil", "sesame_oil", "turmeric", "black_pepper", "cumin_jeera", "walnuts", "almonds", "honey"]:
        virya = "heating"
    if name in ["coconut", "cucumber", "spinach", "palak", "apple", "pear", "milk_full_fat", "ghee", "fennel_saunf", "coriander_dhania", "cardamom_elaichi", "watermelon"]:
        virya = "cooling"

    # AGNI
    if name in ["moong_dal_yellow", "moong_dal_green", "basmati_rice", "ghee", "coconut_water", "apple", "papaya"]:
        agni = "easy"
    if name in ["urad_dal", "rajma", "chhole", "paneer", "soya_chunks", "cheese", "butter"]:
        agni = "heavy"

    # BEST FOR
    if "moong" in name: best_for = ["digestive_weakness", "fever", "postpartum", "weight_loss"]
    if name == "ghee": best_for = ["vata_imbalance", "dry_skin", "constipation", "joint_pain"]
    if "bitter" in name: best_for = ["diabetes", "kapha_excess", "skin_conditions"]
    if name == "amla": best_for = ["pitta_excess", "hair_health", "immunity", "acidity"]
    if "ginger" in name: best_for = ["poor_digestion", "cold", "nausea"]
    if "turmeric" in name: best_for = ["inflammation", "immunity", "skin_health"]

    return {
        "rasa": rasa,
        "virya": virya,
        "vipaka": vipaka,
        "dosha_effect": {"vata": vata, "pitta": pitta, "kapha": kapha},
        "agni_effect": agni,
        "best_for": best_for
    }

def main():
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    foods = []

    for category, items in CATEGORIES.items():
        for item_id in items:
            name = get_name(item_id)

            vegan = category != "dairy"
            dietary_type = ["vegetarian"]
            if vegan: dietary_type.append("vegan")

            cal, pro, carbs, fat, fib = NUTRITION_DB.get(item_id, CATEGORY_MACROS[category])

            ayurvedic = get_ayurvedic_props(item_id, category)

            # Meal suitability
            meals = []
            if category in ["grain", "fruit", "dairy", "beverage", "vegan_protein"]: meals.append("breakfast")
            if category in ["grain", "legume", "vegetable", "dairy", "vegan_protein"]: meals.append("lunch")
            if category in ["grain", "vegetable", "legume"]: meals.append("dinner")
            if category in ["fruit", "nut_seed", "beverage", "dairy"] or item_id in ["fox_nuts_makhana"]: meals.append("snack")
            if not meals: meals = ["lunch", "dinner"]

            # Allergens
            allergen = False
            if category in ["dairy", "nut_seed"]: allergen = True
            if "soya" in item_id or "tofu" in item_id or "soy" in item_id or "peanuts" in item_id or "wheat" in item_id: allergen = True

            food_doc = {
                "id": item_id,
                "name": name,
                "category": category,
                "dietary_type": dietary_type,
                "nutrition_per_100g": {
                    "calories": float(cal),
                    "protein_g": float(pro),
                    "carbs_g": float(carbs),
                    "fat_g": float(fat),
                    "fiber_g": float(fib)
                },
                "ayurvedic": ayurvedic,
                "meal_suitable": meals,
                "prep_time_minutes": 15 if category in ["vegetable", "grain"] else (30 if category == "legume" else 0),
                "season_suitable": ["all"],
                "vegan": vegan,
                "common_allergen": allergen
            }
            foods.append(food_doc)

    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(foods, f, indent=2, ensure_ascii=False)

    stats_cat = defaultdict(int)
    vata_pac = pitta_pac = kapha_pac = easy_digest = veg_only = vegan_count = 0

    for f in foods:
        stats_cat[f["category"]] += 1
        if f["ayurvedic"]["dosha_effect"]["vata"] == -1: vata_pac += 1
        if f["ayurvedic"]["dosha_effect"]["pitta"] == -1: pitta_pac += 1
        if f["ayurvedic"]["dosha_effect"]["kapha"] == -1: kapha_pac += 1
        if f["ayurvedic"]["agni_effect"] == "easy": easy_digest += 1
        if f["vegan"]: vegan_count += 1
        else: veg_only += 1

    print(f"Total foods seeded: {len(foods)} (target: 150)")
    print(f"By category: {dict(stats_cat)}")
    print(f"Vegetarian only (dairy): {veg_only}")
    print(f"Vegan suitable: {vegan_count}")
    print("Dosha pacifying count:")
    print(f"  vata_pacifying: {vata_pac}")
    print(f"  pitta_pacifying: {pitta_pac}")
    print(f"  kapha_pacifying: {kapha_pac}")
    print(f"Easy to digest: {easy_digest}")

if __name__ == "__main__":
    main()
