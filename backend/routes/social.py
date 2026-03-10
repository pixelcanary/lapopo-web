from fastapi import APIRouter, HTTPException, Depends
from database import db
from models import ChatMessage
from auth import get_current_user
from helpers import create_notification
from datetime import datetime, timezone
import uuid

router = APIRouter(prefix="/api")


# NOTIFICATIONS
@router.get("/notificaciones")
async def get_notifications(user=Depends(get_current_user)):
    notifs = await db.notifications.find(
        {"user_id": user["user_id"]}, {"_id": 0}
    ).sort("created_at", -1).to_list(50)
    unread = sum(1 for n in notifs if not n.get("read"))
    return {"notifications": notifs, "unread_count": unread}


@router.put("/notificaciones/{notif_id}/leer")
async def mark_notification_read(notif_id: str, user=Depends(get_current_user)):
    await db.notifications.update_one(
        {"id": notif_id, "user_id": user["user_id"]}, {"$set": {"read": True}})
    return {"message": "ok"}


@router.put("/notificaciones/leer-todas")
async def mark_all_read(user=Depends(get_current_user)):
    await db.notifications.update_many(
        {"user_id": user["user_id"], "read": False}, {"$set": {"read": True}})
    return {"message": "ok"}


# MESSAGES / CHAT
@router.post("/mensajes")
async def send_message(data: ChatMessage, user=Depends(get_current_user)):
    auction = await db.auctions.find_one({"id": data.auction_id}, {"_id": 0})
    if not auction:
        raise HTTPException(404, "Subasta no encontrada")
    uid = user["user_id"]
    is_seller = uid == auction["seller_id"]
    is_bidder = any(b["user_id"] == uid for b in auction.get("bids", []))
    is_winner = uid == auction.get("winner_id")
    if not is_seller and not is_bidder and not is_winner:
        raise HTTPException(403, "Debes pujar primero para enviar mensajes")
    images = data.images[:3] if data.images else []
    doc = {"id": str(uuid.uuid4()), "auction_id": data.auction_id, "sender_id": uid,
           "sender_name": user["name"], "receiver_id": data.receiver_id, "content": data.content,
           "images": images, "created_at": datetime.now(timezone.utc).isoformat()}
    await db.messages.insert_one(doc)
    title = auction["title"]
    await create_notification(data.receiver_id, "message", data.auction_id, title,
        f"Nuevo mensaje de {user['name']} sobre \"{title}\"")
    doc.pop("_id", None)
    return doc


@router.get("/mensajes/{auction_id}")
async def get_messages(auction_id: str, user=Depends(get_current_user)):
    msgs = await db.messages.find(
        {"auction_id": auction_id, "$or": [{"sender_id": user["user_id"]}, {"receiver_id": user["user_id"]}]},
        {"_id": 0}
    ).sort("created_at", 1).to_list(200)
    return msgs


@router.get("/chat/conversaciones")
async def get_conversations(user=Depends(get_current_user)):
    uid = user["user_id"]
    pipeline = [
        {"$match": {"$or": [{"sender_id": uid}, {"receiver_id": uid}]}},
        {"$sort": {"created_at": -1}},
        {"$group": {
            "_id": "$auction_id",
            "last_message": {"$first": "$$ROOT"},
            "count": {"$sum": 1},
        }},
        {"$sort": {"last_message.created_at": -1}},
        {"$limit": 50},
    ]
    convos = await db.messages.aggregate(pipeline).to_list(50)
    result = []
    for c in convos:
        lm = c["last_message"]
        lm.pop("_id", None)
        auction = await db.auctions.find_one({"id": c["_id"]}, {"_id": 0, "title": 1, "images": 1, "seller_id": 1, "seller_name": 1})
        other_id = lm["receiver_id"] if lm["sender_id"] == uid else lm["sender_id"]
        other_name = lm.get("sender_name") if lm["sender_id"] != uid else None
        if not other_name:
            other_user = await db.users.find_one({"id": other_id}, {"_id": 0, "name": 1})
            other_name = other_user["name"] if other_user else "Usuario"
        result.append({
            "auction_id": c["_id"],
            "auction_title": auction["title"] if auction else "",
            "auction_image": auction["images"][0] if auction and auction.get("images") else "",
            "other_user_id": other_id,
            "other_user_name": other_name,
            "last_message": lm["content"],
            "last_date": lm["created_at"],
            "message_count": c["count"],
        })
    return result


# FAVORITES
@router.post("/favoritos/{auction_id}")
async def toggle_favorite(auction_id: str, user=Depends(get_current_user)):
    existing = await db.favorites.find_one({"user_id": user["user_id"], "auction_id": auction_id})
    if existing:
        await db.favorites.delete_one({"user_id": user["user_id"], "auction_id": auction_id})
        return {"favorited": False}
    await db.favorites.insert_one({"user_id": user["user_id"], "auction_id": auction_id,
                                    "created_at": datetime.now(timezone.utc).isoformat()})
    return {"favorited": True}


@router.get("/favoritos")
async def get_favorites(user=Depends(get_current_user)):
    favs = await db.favorites.find({"user_id": user["user_id"]}, {"_id": 0}).to_list(100)
    ids = [f["auction_id"] for f in favs]
    auctions = await db.auctions.find({"id": {"$in": ids}}, {"_id": 0}).to_list(100) if ids else []
    return auctions


# CONTACT INFO
@router.get("/contacto/{auction_id}")
async def get_contact(auction_id: str, user=Depends(get_current_user)):
    auction = await db.auctions.find_one({"id": auction_id}, {"_id": 0})
    if not auction:
        raise HTTPException(404, "Subasta no encontrada")
    if auction["status"] != "finished":
        raise HTTPException(400, "La subasta no ha terminado")
    uid = user["user_id"]
    if uid != auction["seller_id"] and uid != auction.get("winner_id"):
        raise HTTPException(403, "No tienes acceso")
    if uid == auction["seller_id"]:
        if not auction.get("winner_id"):
            raise HTTPException(404, "No hay ganador")
        w = await db.users.find_one({"id": auction["winner_id"]}, {"_id": 0, "password_hash": 0})
        return {"contact_name": w["name"], "contact_email": w["email"], "role": "winner"}
    s = await db.users.find_one({"id": auction["seller_id"]}, {"_id": 0, "password_hash": 0})
    return {"contact_name": s["name"], "contact_email": s["email"], "role": "seller"}
