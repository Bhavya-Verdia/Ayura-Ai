import re
from pathlib import Path

file_path = Path("server/routes/plans.py")
content = file_path.read_text("utf-8")

# 1. Add helper function at the top
helper_code = """
import hashlib
import json

async def _check_plan_cache(db: AsyncIOMotorDatabase, user_id: str, plan_type: str, user_profile: dict, feature_prefs: dict, force_regenerate: bool):
    if force_regenerate:
        return None, None
        
    relevant_data = {
        "dosha": user_profile.get("dominant_dosha"),
        "pregnancy": user_profile.get("pregnancy_or_nursing"),
        "allergies": user_profile.get("allergies"),
        "symptoms": user_profile.get("current_symptoms"),
        "injuries": user_profile.get("injuries_or_limitations"),
        "feature_prefs": feature_prefs
    }
    pref_hash = hashlib.sha256(json.dumps(relevant_data, sort_keys=True).encode()).hexdigest()
    
    latest_plan = await db.plan_history.find_one(
        {"user_id": user_id, "plan_type": plan_type, "preference_hash": pref_hash},
        sort=[("generated_at", -1)]
    )
    if latest_plan:
        return latest_plan.get("plan_data", {}).get(f"{plan_type}_plan", latest_plan.get("plan_data")), pref_hash
    return None, pref_hash

"""

if "_check_plan_cache" not in content:
    content = content.replace("router = APIRouter()", helper_code + "\nrouter = APIRouter()")


endpoints = [
    ("yoga", "services.yoga_plan_engine", "yoga_plan", "yoga_plan_enricher", "yoga_plan"),
    ("diet", "services.diet_plan_engine", "diet_plan", "diet_plan_enricher", "diet_plan"),
    ("gym", "services.gym_plan_engine", "gym_plan", "gym_plan_enricher", "gym_plan"),
    ("panchakarma", "services.panchakarma_engine", "panchakarma_plan", "panchakarma_enricher", "panchakarma_plan"),
    ("remedies", "services.remedy_engine", "remedies_plan", "remedy_enricher", "home_remedies", "home_remedy"),
    ("medicines", "services.remedy_engine", "medicines_plan", "remedy_enricher", "medicines", "clinical_medicine")
]

# I will just write a custom block for the bottom of plans.py
# that REPLACES the existing @router.post("/yoga") ... @router.post("/generate") block
# with the new cached ones.

# Find where @router.post("/yoga") starts
start_idx = content.find('@router.post("/yoga")')
end_idx = content.find('@router.get("/job/{job_id}")')

new_endpoints = []
for item in endpoints:
    if len(item) == 5:
        ep, engine_mod, enricher_func, enricher_mod, plan_data_key = item
        target_type = None
    else:
        ep, engine_mod, enricher_func, enricher_mod, plan_data_key, target_type = item

    target_arg = f", '{target_type}'" if target_type else ""
    pref_key = "remedy" if ep in ["remedies", "medicines"] else ep

    code = f"""@router.post("/{ep}")
async def generate_{ep}_plan(
    req: dict = Body(default={{}}),
    user: UserDocument = Depends(get_current_user), 
    db: AsyncIOMotorDatabase = Depends(get_mongodb)
):
    from {engine_mod} import generate_{ep}_plan as engine_generate
    from {enricher_mod} import enrich_{ep}_plan
    
    force_regenerate = req.get("force_regenerate", False)
    user_profile = user.model_dump()
    prefs_doc = await db.user_preferences.find_one({{"user_id": user.id}})
    
    if not prefs_doc or not prefs_doc.get("{pref_key}"):
        raise HTTPException(status_code=422, detail="Complete {ep} preferences first")
        
    {ep}_prefs = prefs_doc.get("{pref_key}")
    
    # 1. Check Cache
    cached_plan, pref_hash = await _check_plan_cache(db, user.id, "{ep}", user_profile, {ep}_prefs, force_regenerate)
    if cached_plan:
        return cached_plan
        
    # 2. Generate new plan
    raw_plan = engine_generate(user_profile, {ep}_prefs{target_arg})
    enriched_plan = await enrich_{ep}_plan(raw_plan, user_profile, {ep}_prefs)
    
    plan_id = enriched_plan.get("plan_id")
    model_used = enriched_plan.get("enrichment_model", "{engine_mod}")
    
    history = PlanHistoryDocument(
        _id=plan_id,
        user_id=user.id,
        plan_type="{ep}",
        generation_method="agentic" if enriched_plan.get("enriched") else "rule_based",
        model_used=model_used,
        preference_hash=pref_hash,
        plan_data={{
            "{plan_data_key}": enriched_plan,
            "generated_at": datetime.now(timezone.utc).isoformat()
        }},
        generated_at=datetime.now(timezone.utc)
    )
    await db.plan_history.insert_one(history.model_dump(by_alias=True))
    
    return enriched_plan

"""
    new_endpoints.append(code)

new_endpoints.append("""@router.post("/generate")
async def generate_holistic_plan(req: PlanGenerationRequest, background_tasks: BackgroundTasks, user: UserDocument = Depends(get_current_user), db: AsyncIOMotorDatabase = Depends(get_mongodb)):
    return await _enqueue_plan("holistic", req, user, db, background_tasks)

""")

new_content = content[:start_idx] + "\n".join(new_endpoints) + content[end_idx:]

file_path.write_text(new_content, "utf-8")
print("Routes updated successfully.")
