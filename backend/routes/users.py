from fastapi import APIRouter, HTTPException, Depends
from database import db
from models import UserUpdate
from auth import get_current_user

router = APIRouter(prefix="/api")


@router.get("/usuarios/{user_id}")
async def get_user_profile(user_id: str):
    user = await db.users.find_one({"id": user_id}, {"_id": 0, "password_hash": 0})
    if not user:
        raise HTTPException(404, "Usuario no encontrado")
    auctions = await db.auctions.find({"seller_id": user_id}, {"_id": 0}).to_list(100)
    active_bids = await db.auctions.find({"bids.user_id": user_id, "status": "active"}, {"_id": 0}).to_list(100)
    won_auctions = await db.auctions.find({"winner_id": user_id, "status": "finished"}, {"_id": 0}).to_list(100)
    favs = await db.favorites.find({"user_id": user_id}, {"_id": 0}).to_list(100)
    fav_ids = [f["auction_id"] for f in favs]
    fav_auctions = await db.auctions.find({"id": {"$in": fav_ids}}, {"_id": 0}).to_list(100) if fav_ids else []
    ratings = await db.ratings.find({"rated_id": user_id}, {"_id": 0}).sort("created_at", -1).to_list(100)
    disputes = await db.disputes.find({"$or": [{"reporter_id": user_id}, {"reported_id": user_id}]}, {"_id": 0}).sort("created_at", -1).to_list(50)
    user_badges = await db.user_badges.find({"user_id": user_id}, {"_id": 0}).to_list(100)
    badge_ids = [ub["badge_id"] for ub in user_badges]
    badges_data = await db.badges.find({"id": {"$in": badge_ids}}, {"_id": 0}).to_list(100) if badge_ids else []
    return {
        "user": user,
        "auctions": auctions,
        "active_bids": active_bids,
        "won_auctions": won_auctions,
        "favorites": fav_auctions,
        "ratings": ratings,
        "rating_avg": user.get("rating_avg", 0),
        "rating_count": user.get("rating_count", 0),
        "plan": user.get("plan", "free"),
        "disputes": disputes,
        "badges": badges_data,
    }


@router.put("/usuarios/{user_id}")
async def update_user(user_id: str, data: UserUpdate, user=Depends(get_current_user)):
    if user["user_id"] != user_id:
        raise HTTPException(403, "No autorizado")
    update = {}
    if data.name:
        update["name"] = data.name
    if update:
        await db.users.update_one({"id": user_id}, {"$set": update})
    updated = await db.users.find_one({"id": user_id}, {"_id": 0, "password_hash": 0})
    return updated
