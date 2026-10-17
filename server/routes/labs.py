"""
Ayura AI — Lab result routes

One document per recorded result in `db.lab_results`. Results are read against
`services/lab_results.py` on the way out, never stored with their band, so a
corrected range applies to every result already recorded.
"""
import uuid
from datetime import date, datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from motor.motor_asyncio import AsyncIOMotorDatabase
from pydantic import BaseModel, Field

from database.mongodb import get_mongodb
from routes.profile import get_current_user
from schemas.user_schema import UserDocument
from services.lab_results import LAB_TESTS, catalogue, classify, latest_by_test, plausible

router = APIRouter()

_MAX_RESULTS = 500


class LabResultIn(BaseModel):
    test: str = Field(..., min_length=1, max_length=40)
    value: float
    taken_on: date
    note: Optional[str] = Field(None, max_length=200)


def _pregnant(user: UserDocument) -> bool:
    return bool(getattr(user, "pregnancy_status", None) == "pregnant")


def _out(doc: dict, user: UserDocument) -> dict:
    spec = LAB_TESTS[doc["test"]]
    return {
        "id": doc["_id"], "test": doc["test"], "label": spec["label"], "unit": spec["unit"],
        "value": doc["value"], "taken_on": str(doc["taken_on"]), "note": doc.get("note") or "",
        **classify(doc["test"], doc["value"], user.gender, _pregnant(user)),
    }


async def user_results(db, user: UserDocument) -> list[dict]:
    """Every result the user recorded, newest first, read against today's bands."""
    cursor = db.lab_results.find({"user_id": user.id}).sort("taken_on", -1).limit(_MAX_RESULTS)
    docs = await cursor.to_list(length=_MAX_RESULTS)
    return [_out(d, user) for d in docs if d.get("test") in LAB_TESTS]


@router.get("/catalogue")
async def get_catalogue():
    return catalogue()


@router.get("")
async def list_results(
    user: UserDocument = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_mongodb),
):
    results = await user_results(db, user)
    return {"latest": latest_by_test(results), "history": results}


@router.post("")
async def add_result(
    body: LabResultIn,
    user: UserDocument = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_mongodb),
):
    if body.test not in LAB_TESTS:
        raise HTTPException(status_code=422, detail="Unknown test")
    if not plausible(body.test, body.value):
        spec = LAB_TESTS[body.test]
        raise HTTPException(
            status_code=422,
            detail=f"{spec['label']} is usually between {spec['min']} and {spec['max']} {spec['unit']} "
                   "— please check the value and the unit on your report.")
    if body.taken_on > date.today() or body.taken_on.year < 1990:
        raise HTTPException(status_code=422, detail="Enter the date the sample was taken.")
    if await db.lab_results.count_documents({"user_id": user.id}) >= _MAX_RESULTS:
        raise HTTPException(status_code=422, detail="Too many results recorded; delete some old ones first.")
    doc = {
        "_id": str(uuid.uuid4()), "user_id": user.id, "test": body.test,
        "value": round(body.value, 3), "taken_on": body.taken_on.isoformat(),
        "note": (body.note or "").strip() or None,
        "created_at": datetime.now(timezone.utc),
    }
    await db.lab_results.insert_one(doc)
    return _out(doc, user)


@router.delete("/{result_id}")
async def delete_result(
    result_id: str,
    user: UserDocument = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_mongodb),
):
    res = await db.lab_results.delete_one({"_id": result_id, "user_id": user.id})
    if not getattr(res, "deleted_count", 0):
        raise HTTPException(status_code=404, detail="Result not found")
    return {"deleted": True}
