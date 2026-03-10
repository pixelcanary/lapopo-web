from fastapi import APIRouter, HTTPException, Depends
from typing import Optional
from database import db
from models import DisputeStatusUpdate, BadgeCreate, BadgeAssign
from auth import require_admin
from helpers import create_notification
from datetime import datetime, timezone
import uuid

router = APIRouter(prefix="/api")


# ADMIN STATS
@router.get("/admin/stats")
async def admin_stats(user=Depends(require_admin)):
    total_users = await db.users.count_documents({})
    active_auctions = await db.auctions.count_documents({"status": "active"})
    finished_auctions = await db.auctions.count_documents({"status": "finished"})
    cancelled_auctions = await db.auctions.count_documents({"status": "cancelled"})
    pipeline = [{"$group": {"_id": None, "total_bids": {"$sum": "$bid_count"}}}]
    agg = await db.auctions.aggregate(pipeline).to_list(1)
    total_bids = agg[0]["total_bids"] if agg else 0
    total_ratings = await db.ratings.count_documents({})
    return {
        "total_users": total_users,
        "active_auctions": active_auctions,
        "finished_auctions": finished_auctions,
        "cancelled_auctions": cancelled_auctions,
        "total_bids": total_bids,
        "total_ratings": total_ratings,
    }


# ADMIN USERS
@router.get("/admin/usuarios")
async def admin_list_users(user=Depends(require_admin)):
    users = await db.users.find({}, {"_id": 0, "password_hash": 0}).sort("created_at", -1).to_list(500)
    for u in users:
        u["auction_count"] = await db.auctions.count_documents({"seller_id": u["id"]})
    return users


@router.delete("/admin/usuarios/{user_id}")
async def admin_delete_user(user_id: str, user=Depends(require_admin)):
    target = await db.users.find_one({"id": user_id}, {"_id": 0})
    if not target:
        raise HTTPException(404, "Usuario no encontrado")
    if target.get("is_admin"):
        raise HTTPException(400, "No se puede eliminar un administrador")
    await db.users.delete_one({"id": user_id})
    await db.auctions.update_many({"seller_id": user_id, "status": "active"}, {"$set": {"status": "cancelled"}})
    await db.favorites.delete_many({"user_id": user_id})
    await db.notifications.delete_many({"user_id": user_id})
    await db.auto_bids.delete_many({"user_id": user_id})
    return {"message": "Usuario eliminado"}


# ADMIN AUCTIONS
@router.get("/admin/subastas")
async def admin_list_auctions(status: Optional[str] = None, user=Depends(require_admin)):
    q = {}
    if status:
        q["status"] = status
    auctions = await db.auctions.find(q, {"_id": 0}).sort("created_at", -1).to_list(500)
    return auctions


@router.delete("/admin/subastas/{auction_id}")
async def admin_delete_auction(auction_id: str, user=Depends(require_admin)):
    auction = await db.auctions.find_one({"id": auction_id}, {"_id": 0})
    if not auction:
        raise HTTPException(404, "Subasta no encontrada")
    await db.auctions.delete_one({"id": auction_id})
    await db.favorites.delete_many({"auction_id": auction_id})
    await db.auto_bids.delete_many({"auction_id": auction_id})
    await db.ratings.delete_many({"auction_id": auction_id})
    return {"message": "Subasta eliminada"}


# ADMIN DISPUTES
@router.get("/admin/disputas")
async def admin_list_disputes(status: Optional[str] = None, user=Depends(require_admin)):
    q = {}
    if status:
        q["status"] = status
    return await db.disputes.find(q, {"_id": 0}).sort("created_at", -1).to_list(200)


@router.put("/admin/disputas/{dispute_id}/estado")
async def admin_update_dispute(dispute_id: str, data: DisputeStatusUpdate, user=Depends(require_admin)):
    valid_statuses = ["open", "reviewing", "resolved_buyer", "resolved_seller", "closed"]
    if data.status not in valid_statuses:
        raise HTTPException(400, "Estado no valido")
    d = await db.disputes.find_one({"id": dispute_id}, {"_id": 0})
    if not d:
        raise HTTPException(404, "Disputa no encontrada")
    await db.disputes.update_one({"id": dispute_id}, {"$set": {"status": data.status, "updated_at": datetime.now(timezone.utc).isoformat()}})
    status_labels = {"reviewing": "en revision", "resolved_buyer": "resuelta a favor del comprador", "resolved_seller": "resuelta a favor del vendedor", "closed": "cerrada"}
    label = status_labels.get(data.status, data.status)
    for uid in [d["reporter_id"], d["reported_id"]]:
        await create_notification(uid, "dispute_update", d["auction_id"], d["auction_title"],
            f"Tu disputa sobre \"{d['auction_title']}\" ha sido {label}")
    return {"message": f"Disputa actualizada a: {label}"}


# ADMIN CONFIG
@router.get("/admin/config")
async def get_admin_config(user=Depends(require_admin)):
    payments_on = await db.settings.find_one({"key": "payments_enabled"}, {"_id": 0})
    return {"payments_enabled": payments_on["value"] if payments_on else False}


@router.put("/admin/config")
async def update_admin_config(config: dict, user=Depends(require_admin)):
    if "payments_enabled" in config:
        await db.settings.update_one({"key": "payments_enabled"}, {"$set": {"value": config["payments_enabled"]}}, upsert=True)
    return {"message": "Configuracion actualizada"}


# ADMIN BADGES
@router.post("/admin/badges")
async def admin_create_badge(data: BadgeCreate, user=Depends(require_admin)):
    doc = {"id": str(uuid.uuid4()), "name": data.name, "description": data.description, "emoji": data.emoji,
           "condition_type": data.condition_type, "condition_value": data.condition_value, "auto": data.auto,
           "created_at": datetime.now(timezone.utc).isoformat()}
    await db.badges.insert_one(doc)
    doc.pop("_id", None)
    return doc


@router.put("/admin/badges/{badge_id}")
async def admin_update_badge(badge_id: str, data: BadgeCreate, user=Depends(require_admin)):
    result = await db.badges.update_one({"id": badge_id}, {"$set": {
        "name": data.name, "description": data.description, "emoji": data.emoji,
        "condition_type": data.condition_type, "condition_value": data.condition_value, "auto": data.auto,
    }})
    if result.matched_count == 0:
        raise HTTPException(404, "Badge no encontrado")
    return {"message": "Badge actualizado"}


@router.delete("/admin/badges/{badge_id}")
async def admin_delete_badge(badge_id: str, user=Depends(require_admin)):
    await db.badges.delete_one({"id": badge_id})
    await db.user_badges.delete_many({"badge_id": badge_id})
    return {"message": "Badge eliminado"}


@router.post("/admin/badges/{badge_id}/asignar")
async def admin_assign_badge(badge_id: str, data: BadgeAssign, user=Depends(require_admin)):
    badge = await db.badges.find_one({"id": badge_id}, {"_id": 0})
    if not badge:
        raise HTTPException(404, "Badge no encontrado")
    existing = await db.user_badges.find_one({"user_id": data.user_id, "badge_id": badge_id})
    if existing:
        raise HTTPException(400, "El usuario ya tiene este badge")
    await db.user_badges.insert_one({"user_id": data.user_id, "badge_id": badge_id, "badge_name": badge["name"], "awarded_at": datetime.now(timezone.utc).isoformat()})
    return {"message": "Badge asignado"}


@router.post("/admin/badges/{badge_id}/retirar")
async def admin_remove_badge(badge_id: str, data: BadgeAssign, user=Depends(require_admin)):
    result = await db.user_badges.delete_one({"user_id": data.user_id, "badge_id": badge_id})
    if result.deleted_count == 0:
        raise HTTPException(404, "El usuario no tiene este badge")
    return {"message": "Badge retirado"}


# ADMIN RATINGS
@router.get("/admin/valoraciones")
async def admin_list_ratings(user_id: Optional[str] = None, min_rating: Optional[int] = None, max_rating: Optional[int] = None, user=Depends(require_admin)):
    q = {}
    if user_id:
        q["$or"] = [{"rater_id": user_id}, {"rated_id": user_id}]
    if min_rating:
        q["rating"] = q.get("rating", {})
        q["rating"]["$gte"] = min_rating
    if max_rating:
        q.setdefault("rating", {})["$lte"] = max_rating
    ratings = await db.ratings.find(q, {"_id": 0}).sort("created_at", -1).to_list(200)
    return ratings


@router.delete("/admin/valoraciones/{rating_id}")
async def admin_delete_rating(rating_id: str, user=Depends(require_admin)):
    rating = await db.ratings.find_one({"id": rating_id}, {"_id": 0})
    if not rating:
        raise HTTPException(404, "Valoracion no encontrada")
    await db.ratings.delete_one({"id": rating_id})
    remaining = await db.ratings.find({"rated_id": rating["rated_id"]}, {"_id": 0, "rating": 1}).to_list(1000)
    if remaining:
        avg = round(sum(r["rating"] for r in remaining) / len(remaining), 2)
        await db.users.update_one({"id": rating["rated_id"]}, {"$set": {"rating_avg": avg, "rating_count": len(remaining)}})
    else:
        await db.users.update_one({"id": rating["rated_id"]}, {"$set": {"rating_avg": 0, "rating_count": 0}})
    return {"message": "Valoracion eliminada"}
