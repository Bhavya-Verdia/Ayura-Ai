import re
from pathlib import Path

BASE_DIR = Path(".")

# 1. Update plans.py
plans_path = BASE_DIR / "routes" / "plans.py"
content = plans_path.read_text("utf-8")

# Yoga
content = content.replace('raw_plan = engine_generate(user_profile, yoga_prefs)',
'''    yoga_poses = await db.kb_yoga_poses.find().to_list(None)
    pranayama_list = await db.kb_pranayama.find().to_list(None)
    raw_plan = engine_generate(user_profile, yoga_prefs, yoga_poses, pranayama_list)''')

# Diet
content = content.replace('raw_plan = engine_generate(user_profile, diet_prefs)',
'''    diet_foods = await db.kb_diet_foods.find().to_list(None)
    raw_plan = engine_generate(user_profile, diet_prefs, diet_foods)''')

# Gym
content = content.replace('raw_plan = engine_generate(user_profile, gym_prefs)',
'''    gym_exercises = await db.kb_gym_exercises.find().to_list(None)
    raw_plan = engine_generate(user_profile, gym_prefs, gym_exercises)''')

# Panchakarma
content = content.replace('raw_plan = engine_generate(user_profile, panchakarma_prefs)',
'''    panchakarma_therapies = await db.kb_panchakarma_therapies.find().to_list(None)
    raw_plan = engine_generate(user_profile, panchakarma_prefs, panchakarma_therapies)''')

# Remedies
content = content.replace("raw_plan = engine_generate(user_profile, remedies_prefs, 'home_remedies')",
'''    ayurvedic_remedies = await db.kb_ayurvedic_remedies.find().to_list(None)
    raw_plan = engine_generate(user_profile, remedies_prefs, ayurvedic_remedies, 'home_remedies')''')

# Medicines
content = content.replace("raw_plan = engine_generate(user_profile, medicines_prefs, 'clinical_medicine')",
'''    ayurvedic_remedies = await db.kb_ayurvedic_remedies.find().to_list(None)
    raw_plan = engine_generate(user_profile, medicines_prefs, ayurvedic_remedies, 'clinical_medicine')''')

plans_path.write_text(content, "utf-8")

# 2. Update Yoga Engine
yoga_path = BASE_DIR / "services" / "yoga_plan_engine.py"
y_content = yoga_path.read_text("utf-8")
y_content = y_content.replace('def filter_poses(user_profile, yoga_prefs):', 'def filter_poses(user_profile, yoga_prefs, yoga_poses):')
y_content = y_content.replace('def select_pranayama(user_profile, yoga_prefs, count=3):', 'def select_pranayama(user_profile, yoga_prefs, pranayama_list, count=3):')
y_content = y_content.replace('def generate_yoga_plan(user_profile, yoga_prefs):', 'def generate_yoga_plan(user_profile, yoga_prefs, yoga_poses_db=None, pranayama_list_db=None):')
y_content = y_content.replace('filtered_poses = filter_poses(user_profile, yoga_prefs)', '''    yp = yoga_poses_db if yoga_poses_db is not None else yoga_poses
    pl = pranayama_list_db if pranayama_list_db is not None else pranayama_list
    filtered_poses = filter_poses(user_profile, yoga_prefs, yp)''')
y_content = y_content.replace('pranayamas = select_pranayama(user_profile, yoga_prefs, count=3)', 'pranayamas = select_pranayama(user_profile, yoga_prefs, pl, count=3)')
yoga_path.write_text(y_content, "utf-8")

# 3. Update Diet Engine
diet_path = BASE_DIR / "services" / "diet_plan_engine.py"
d_content = diet_path.read_text("utf-8")
d_content = d_content.replace('def filter_and_score_foods(user_profile, diet_prefs):', 'def filter_and_score_foods(user_profile, diet_prefs, diet_foods):')
d_content = d_content.replace('def generate_diet_plan(user_profile, diet_prefs):', 'def generate_diet_plan(user_profile, diet_prefs, diet_foods_db=None):')
d_content = d_content.replace('food_pool = filter_and_score_foods(user_profile, diet_prefs)', '''    df = diet_foods_db if diet_foods_db is not None else diet_foods
    food_pool = filter_and_score_foods(user_profile, diet_prefs, df)''')
diet_path.write_text(d_content, "utf-8")

# 4. Update Gym Engine
gym_path = BASE_DIR / "services" / "gym_plan_engine.py"
g_content = gym_path.read_text("utf-8")
g_content = g_content.replace('def filter_exercises(user_profile, gym_prefs):', 'def filter_exercises(user_profile, gym_prefs, gym_exercises):')
g_content = g_content.replace('def generate_gym_plan(user_profile, gym_prefs):', 'def generate_gym_plan(user_profile, gym_prefs, gym_exercises_db=None):')
g_content = g_content.replace('filtered_ex = filter_exercises(user_profile, gym_prefs)', '''    ge = gym_exercises_db if gym_exercises_db is not None else gym_exercises
    filtered_ex = filter_exercises(user_profile, gym_prefs, ge)''')
gym_path.write_text(g_content, "utf-8")

# 5. Update Panchakarma Engine
pk_path = BASE_DIR / "services" / "panchakarma_engine.py"
pk_content = pk_path.read_text("utf-8")
pk_content = pk_content.replace('def get_relevant_therapies(dosha, goals):', 'def get_relevant_therapies(dosha, goals, panchakarma_therapies):')
pk_content = pk_content.replace('def generate_panchakarma_plan(user_profile, pk_prefs):', 'def generate_panchakarma_plan(user_profile, pk_prefs, pk_therapies_db=None):')
pk_content = pk_content.replace('pool = get_relevant_therapies(dosha, [g])', '''    pkt = pk_therapies_db if pk_therapies_db is not None else panchakarma_therapies
    pool = get_relevant_therapies(dosha, [g], pkt)''')
pk_path.write_text(pk_content, "utf-8")

# 6. Update Remedy Engine
rem_path = BASE_DIR / "services" / "remedy_engine.py"
r_content = rem_path.read_text("utf-8")
r_content = r_content.replace('def filter_remedies(user_profile, remedy_type):', 'def filter_remedies(user_profile, remedy_type, ayurvedic_remedies):')
r_content = r_content.replace('def generate_remedies_plan(user_profile, prefs, remedy_type="home_remedies"):', 'def generate_remedies_plan(user_profile, prefs, ayurvedic_remedies_db=None, remedy_type="home_remedies"):')
r_content = r_content.replace('remedy_pool = filter_remedies(user_profile, remedy_type)', '''    ar = ayurvedic_remedies_db if ayurvedic_remedies_db is not None else ayurvedic_remedies
    remedy_pool = filter_remedies(user_profile, remedy_type, ar)''')
rem_path.write_text(r_content, "utf-8")

print("Engines refactored successfully.")
