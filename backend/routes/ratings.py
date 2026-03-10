from fastapi import APIRouter, HTTPException, Depends
from database import db
from models import RatingCreate
from auth import get_current_user
from helpers import evaluate_badges
from datetime import datetime, timezone
import uuid

router = APIRouter(prefix="/api")


@router.post("/valoraciones")
async def create_rating(data: RatingCreate, user=Depends(get_current_user)):
    if data.rating < 1 or data.rating > 5:
        raise HTTPException(400, "La valoracion debe ser entre 1 y 5")
    auction = await db.auctions.find_one({"id": data.auction_id}, {"_id": 0})
    if not auction:
        raise HTTPException(404, "Subasta no encontrada")
    if auction["status"] != "finished":
        raise HTTPException(400, "La subasta no ha terminado")
    uid = user["user_id"]
    is_seller = uid == auction["seller_id"]
    is_winner = uid == auction.get("winner_id")
    if not is_seller and not is_winner:
        raise HTTPException(403, "Solo el comprador o vendedor pueden valorar")
    if uid == data.rated_user_id:
        raise HTTPException(400, "No puedes valorarte a ti mismo")
    if is_seller and data.rated_user_id != auction.get("winner_id"):
        raise HTTPException(400, "Solo puedes valorar al ganador")
    if is_winner and data.rated_user_id != auction["seller_id"]:
        raise HTTPException(400, "Solo puedes valorar al vendedor")
    existing = await db.ratings.find_one({"auction_id": data.auction_id, "rater_id": uid, "rated_id": data.rated_user_id})
    if existing:
        raise HTTPException(400, "Ya has valorado a este usuario en esta subasta")
    doc = {
        "id": str(uuid.uuid4()),
        "auction_id": data.auction_id,
        "rater_id": uid,
        "rater_name": user["name"],
        "rated_id": data.rated_user_id,
        "rating": data.rating,
        "comment": data.comment or "",
        "created_at": datetime.now(timezone.utc).isoformat()
    }
    await db.ratings.insert_one(doc)
    all_ratings = await db.ratings.find({"rated_id": data.rated_user_id}, {"_id": 0, "rating": 1}).to_list(1000)
    avg = round(sum(r["rating"] for r in all_ratings) / len(all_ratings), 2)
    await db.users.update_one({"id": data.rated_user_id}, {"$set": {"rating_avg": avg, "rating_count": len(all_ratings)}})
    await evaluate_badges(data.rated_user_id)
    doc.pop("_id", None)
    return doc


@router.get("/valoraciones/usuario/{user_id}")
async def get_user_ratings(user_id: str):
    ratings = await db.ratings.find({"rated_id": user_id}, {"_id": 0}).sort("created_at", -1).to_list(100)
    u = await db.users.find_one({"id": user_id}, {"_id": 0, "rating_avg": 1, "rating_count": 1})
    return {"ratings": ratings, "average": u.get("rating_avg", 0) if u else 0, "count": u.get("rating_count", 0) if u else 0}


@router.get("/valoraciones/subasta/{auction_id}")
async def get_auction_ratings(auction_id: str, user=Depends(get_current_user)):
    ratings = await db.ratings.find({"auction_id": auction_id}, {"_id": 0}).to_list(10)
    my_ratings = [r for r in ratings if r["rater_id"] == user["user_id"]]
    return {"ratings": ratings, "my_ratings": my_ratings}
