from fastapi import APIRouter
from database import db

router = APIRouter(prefix="/api")


@router.get("/badges")
async def list_badges():
    return await db.badges.find({}, {"_id": 0}).to_list(200)


@router.get("/badges/usuario/{user_id}")
async def get_user_badges(user_id: str):
    ub = await db.user_badges.find({"user_id": user_id}, {"_id": 0}).to_list(100)
    badge_ids = [u["badge_id"] for u in ub]
    badges = await db.badges.find({"id": {"$in": badge_ids}}, {"_id": 0}).to_list(100) if badge_ids else []
    return badges
