from fastapi import APIRouter, HTTPException, Depends
from database import db
from models import DisputeCreate, DisputeMessage
from auth import get_current_user
from helpers import create_notification
from datetime import datetime, timezone
import uuid

router = APIRouter(prefix="/api")


@router.post("/disputas")
async def create_dispute(data: DisputeCreate, user=Depends(get_current_user)):
    auction = await db.auctions.find_one({"id": data.auction_id}, {"_id": 0})
    if not auction:
        raise HTTPException(404, "Subasta no encontrada")
    if auction["status"] != "finished":
        raise HTTPException(400, "Solo puedes abrir disputa en subastas finalizadas")
    uid = user["user_id"]
    is_seller = uid == auction["seller_id"]
    is_winner = uid == auction.get("winner_id")
    if not is_seller and not is_winner:
        raise HTTPException(403, "Solo el comprador o vendedor pueden abrir una disputa")
    existing = await db.disputes.find_one({"auction_id": data.auction_id, "reporter_id": uid})
    if existing:
        raise HTTPException(400, "Ya tienes una disputa abierta para esta subasta")
    reported_id = auction.get("winner_id") if is_seller else auction["seller_id"]
    reported_name = auction.get("winner_name") if is_seller else auction["seller_name"]
    doc = {
        "id": str(uuid.uuid4()),
        "auction_id": data.auction_id,
        "auction_title": auction["title"],
        "reporter_id": uid,
        "reporter_name": user["name"],
        "reported_id": reported_id,
        "reported_name": reported_name,
        "reason": data.reason,
        "description": data.description,
        "status": "open",
        "messages": [],
        "created_at": datetime.now(timezone.utc).isoformat(),
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }
    await db.disputes.insert_one(doc)
    doc.pop("_id", None)
    return doc


@router.get("/disputas/mis-disputas")
async def my_disputes(user=Depends(get_current_user)):
    disputes = await db.disputes.find(
        {"$or": [{"reporter_id": user["user_id"]}, {"reported_id": user["user_id"]}]},
        {"_id": 0}
    ).sort("created_at", -1).to_list(50)
    return disputes


@router.get("/disputas/{dispute_id}")
async def get_dispute(dispute_id: str, user=Depends(get_current_user)):
    d = await db.disputes.find_one({"id": dispute_id}, {"_id": 0})
    if not d:
        raise HTTPException(404, "Disputa no encontrada")
    uid = user["user_id"]
    is_admin = user.get("is_admin", False)
    if not is_admin and uid != d["reporter_id"] and uid != d["reported_id"]:
        raise HTTPException(403, "No tienes acceso a esta disputa")
    return d


@router.post("/disputas/{dispute_id}/mensaje")
async def add_dispute_message(dispute_id: str, data: DisputeMessage, user=Depends(get_current_user)):
    d = await db.disputes.find_one({"id": dispute_id}, {"_id": 0})
    if not d:
        raise HTTPException(404, "Disputa no encontrada")
    uid = user["user_id"]
    is_admin = user.get("is_admin", False)
    if not is_admin and uid != d["reporter_id"] and uid != d["reported_id"]:
        raise HTTPException(403, "No tienes acceso")
    if d["status"] == "closed":
        raise HTTPException(400, "La disputa esta cerrada")
    images = data.images[:3] if hasattr(data, 'images') and data.images else []
    msg = {"id": str(uuid.uuid4()), "sender_id": uid, "sender_name": user["name"], "content": data.content, "images": images, "is_admin": is_admin, "created_at": datetime.now(timezone.utc).isoformat()}
    await db.disputes.update_one({"id": dispute_id}, {"$push": {"messages": msg}})
    for notify_id in [d["reporter_id"], d["reported_id"]]:
        if notify_id != uid:
            role = "Admin" if is_admin else user["name"]
            await create_notification(notify_id, "dispute_message", d["auction_id"], d["auction_title"],
                f"Nuevo mensaje de {role} en tu disputa sobre \"{d['auction_title']}\"")
    return msg
