import asyncio
import json
import os
import sys

# Add server to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from motor.motor_asyncio import AsyncIOMotorClient
from core.kb_cache import kb_cache
from services.remedy_engine import filter_remedies, build_remedy_plan

PROFILES = [
    {
        "name": "Profile 1: Vata (Standard)",
        "user_profile": {"id": "1", "dominant_dosha": "vata", "secondary_dosha": "pitta", "pregnancy_or_nursing": False, "current_medications": [], "medical_history": [], "allergies": []},
        "req": {"symptoms": ["headache", "fatigue"], "severity": {"headache": "mild", "fatigue": "moderate"}, "duration": {"headache": "recent", "fatigue": "weeks"}}
    },
    {
        "name": "Profile 2: Pitta (Standard)",
        "user_profile": {"id": "2", "dominant_dosha": "pitta", "secondary_dosha": "kapha", "pregnancy_or_nursing": False, "current_medications": [], "medical_history": [], "allergies": []},
        "req": {"symptoms": ["acid_reflux", "acne"], "severity": {"acid_reflux": "mild", "acne": "mild"}, "duration": {"acid_reflux": "recent", "acne": "weeks"}}
    },
    {
        "name": "Profile 3: Kapha (Chronic)",
        "user_profile": {"id": "3", "dominant_dosha": "kapha", "secondary_dosha": "vata", "pregnancy_or_nursing": False, "current_medications": [], "medical_history": [], "allergies": []},
        "req": {"symptoms": ["congestion", "low_immunity"], "severity": {"congestion": "moderate", "low_immunity": "mild"}, "duration": {"congestion": "recent", "low_immunity": "months"}}
    },
    {
        "name": "Profile 4: Kapha (Blood Thinners)",
        "user_profile": {"id": "4", "dominant_dosha": "kapha", "secondary_dosha": "vata", "pregnancy_or_nursing": False, "current_medications": ["blood thinners"], "medical_history": [], "allergies": []},
        "req": {"symptoms": ["headache", "joint_pain"], "severity": {"headache": "mild", "joint_pain": "mild"}, "duration": {"headache": "recent", "joint_pain": "recent"}}
    },
    {
        "name": "Profile 5: Pitta (Pregnant)",
        "user_profile": {"id": "5", "dominant_dosha": "pitta", "secondary_dosha": "kapha", "pregnancy_or_nursing": True, "current_medications": [], "medical_history": [], "allergies": []},
        "req": {"symptoms": ["nausea", "fatigue"], "severity": {"nausea": "mild", "fatigue": "mild"}, "duration": {"nausea": "recent", "fatigue": "recent"}}
    },
    {
        "name": "Profile 6: Severe Gate",
        "user_profile": {"id": "6", "dominant_dosha": "vata", "secondary_dosha": "pitta", "pregnancy_or_nursing": False, "current_medications": [], "medical_history": [], "allergies": []},
        "req": {"symptoms": ["headache"], "severity": {"headache": "severe"}, "duration": {"headache": "recent"}}
    }
]

async def run_tests():
    print("Loading KB Cache...")
    client = AsyncIOMotorClient("mongodb://localhost:27017")
    db = client.ayura
    await kb_cache.load(db)
    
    passed = 0
    
    print("\n---------------------------------------")
    print(" REMEDY ENGINE TEST RUN")
    print("\n---------------------------------------")
    
    for p in PROFILES:
        print(f"\n[{p['name']}]")
        print(f"Symptoms requested: {p['req']['symptoms']}")
        
        filtered = filter_remedies(p["user_profile"], p["req"])
        plan = build_remedy_plan(filtered, p["user_profile"], p["req"])
        
        addressed = len(plan["symptoms_addressed"])
        blocked = len(plan["doctor_referrals"])
        
        print(f"Remedies returned: {addressed} symptoms addressed")
        print(f"Doctor referrals: {blocked} symptoms blocked")
        
        # Checking flags
        drug_interactions = any("interaction_found" in str(f) for f in filtered)
        pregnancy_applied = p["user_profile"]["pregnancy_or_nursing"] and any("pregnancy_safe" in str(f) or "pregnancy" in str(f) for f in filtered)
        severe_triggered = any(f.get("action") == "see_doctor" for f in filtered)
        
        print(f"Drug interactions flagged: {'YES' if drug_interactions else 'NO'}")
        print(f"Pregnancy filter applied: {'YES' if pregnancy_applied else 'NO'}")
        print(f"Severe gate triggered: {'YES' if severe_triggered else 'NO'}")
        print(f"Dosha used: {p['user_profile']['dominant_dosha']}")
        
        remedy_names = [s["remedy"]["name"] for s in plan["symptoms_addressed"] if "remedy" in s and s["remedy"]]
        print(f"Remedy names: {remedy_names}")
        
        # Validation
        success = True
        if p["user_profile"]["id"] == "4" and not drug_interactions:
            success = False
        if p["user_profile"]["id"] == "5":
            for s in plan["symptoms_addressed"]:
                remedy_kb = next((r for r in kb_cache.ayurvedic_remedies if r["symptom_id"] == s["symptom_id"]), None)
                if remedy_kb and not remedy_kb.get("pregnancy_safe"):
                    success = False
        if p["user_profile"]["id"] == "6" and addressed > 0:
            success = False
            
        if success:
            passed += 1
            
    print("\n---------------------------------------")
    print(f"PASSED: {passed}/6")
    print(f"FAILED: {6 - passed}/6")
    print("\n---------------------------------------")

if __name__ == "__main__":
    asyncio.run(run_tests())
