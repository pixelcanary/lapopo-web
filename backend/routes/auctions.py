from fastapi import APIRouter, HTTPException, Depends
from typing import Optional
from database import db
from models import AuctionCreate, BidCreate, AutoBidCreate, DURATION_MAP, PLANS, CATEGORIES, CANARY_ISLANDS
from auth import get_current_user
from helpers import close_expired, enrich_with_ratings, enrich_with_featured, get_payments_enabled, get_user_plan, count_user_auctions_this_month, create_notification, process_auto_bids, evaluate_badges
from datetime import datetime, timezone, timedelta
import uuid

router = APIRouter(prefix="/api")


@router.get("/subastas")
async def list_auctions(
    category: Optional[str] = None,
    location: Optional[str] = None,
    status: Optional[str] = "active",
    search: Optional[str] = None,
    canarias: Optional[bool] = None,
    sort: Optional[str] = None,
    min_price: Optional[float] = None,
    max_price: Optional[float] = None
):
    await close_expired()
    q = {}
    if status:
        q["status"] = status
    if status != "cancelled":
        q.setdefault("status", {"$ne": "cancelled"})
    if category:
        q["category"] = category
    if location:
        q["location"] = location
    if canarias:
        q["location"] = {"$in": CANARY_ISLANDS}
    if search:
        q["$or"] = [
            {"title": {"$regex": search, "$options": "i"}},
            {"description": {"$regex": search, "$options": "i"}}
        ]
    if min_price is not None:
        q.setdefault("current_price", {})["$gte"] = min_price
    if max_price is not None:
        q.setdefault("current_price", {})["$lte"] = max_price

    sort_field = [("created_at", -1)]
    if sort == "ending_soon":
        sort_field = [("end_time", 1)]
    elif sort == "price_low":
        sort_field = [("current_price", 1)]
    elif sort == "price_high":
        sort_field = [("current_price", -1)]
    elif sort == "most_bids":
        sort_field = [("bid_count", -1)]

    auctions = await db.auctions.find(q, {"_id": 0}).sort(sort_field).to_list(100)
    auctions = await enrich_with_ratings(auctions)
    auctions = await enrich_with_featured(auctions)
    return auctions


@router.get("/subastas/autocomplete")
async def search_autocomplete(q: str = ""):
    if len(q) < 2:
        return []
    auctions = await db.auctions.find(
        {"status": "active", "title": {"$regex": q, "$options": "i"}},
        {"_id": 0, "id": 1, "title": 1, "images": 1, "current_price": 1}
    ).limit(8).to_list(8)
    return auctions


@router.get("/subastas/{auction_id}")
async def get_auction(auction_id: str):
    await close_expired()
    auction = await db.auctions.find_one({"id": auction_id}, {"_id": 0})
    if not auction:
        raise HTTPException(404, "Subasta no encontrada")
    seller = await db.users.find_one({"id": auction["seller_id"]}, {"_id": 0, "rating_avg": 1, "rating_count": 1, "plan": 1})
    auction["seller_rating_avg"] = seller.get("rating_avg", 0) if seller else 0
    auction["seller_rating_count"] = seller.get("rating_count", 0) if seller else 0
    auction["seller_plan"] = seller.get("plan", "free") if seller else "free"
    feats = await db.featured_listings.find({"auction_id": auction_id, "active": True}, {"_id": 0}).to_list(10)
    auction["featured"] = [f["type"] for f in feats]
    return auction


@router.post("/subastas")
async def create_auction(data: AuctionCreate, user=Depends(get_current_user)):
    if data.starting_price < 1:
        raise HTTPException(400, "Precio minimo: 1 euro")
    if data.duration not in DURATION_MAP:
        raise HTTPException(400, "Duracion no valida")
    if len(data.images) < 1:
        raise HTTPException(400, "Minimo 1 foto")
    if len(data.images) > 6:
        raise HTTPException(400, "Maximo 6 fotos")
    if data.buy_now_price is not None and data.buy_now_price <= data.starting_price:
        raise HTTPException(400, "El precio de compra inmediata debe ser mayor que el precio de salida")

    payments_on = await get_payments_enabled()
    if payments_on:
        plan = await get_user_plan(user["user_id"])
        plan_info = PLANS.get(plan, PLANS["free"])
        if plan_info["max_auctions"] is not None:
            count = await count_user_auctions_this_month(user["user_id"])
            if count >= plan_info["max_auctions"]:
                raise HTTPException(403, f"Has alcanzado el limite de {plan_info['max_auctions']} subastas/mes. Mejora tu plan para publicar mas.")

    now = datetime.now(timezone.utc)
    aid = str(uuid.uuid4())
    doc = {
        "id": aid,
        "title": data.title,
        "description": data.description,
        "images": data.images,
        "starting_price": data.starting_price,
        "current_price": data.starting_price,
        "buy_now_price": data.buy_now_price,
        "duration": data.duration,
        "end_time": (now + DURATION_MAP[data.duration]).isoformat(),
        "category": data.category,
        "location": data.location,
        "delivery_type": data.delivery_type,
        "seller_id": user["user_id"],
        "seller_name": user["name"],
        "bids": [],
        "bid_count": 0,
        "status": "active",
        "winner_id": None,
        "winner_name": None,
        "created_at": now.isoformat()
    }
    await db.auctions.insert_one(doc)
    doc.pop("_id", None)
    return doc


@router.post("/subastas/{auction_id}/pujar")
async def place_bid(auction_id: str, data: BidCreate, user=Depends(get_current_user)):
    auction = await db.auctions.find_one({"id": auction_id}, {"_id": 0})
    if not auction:
        raise HTTPException(404, "Subasta no encontrada")
    if auction["status"] != "active":
        raise HTTPException(400, "Subasta no activa")
    if auction["seller_id"] == user["user_id"]:
        raise HTTPException(400, "No puedes pujar en tu propia subasta")
    min_bid = auction["current_price"] + 0.50
    if data.amount < min_bid:
        raise HTTPException(400, f"Puja minima: {min_bid:.2f} euros")

    if auction.get("bids"):
        prev = auction["bids"][-1]
        if prev["user_id"] != user["user_id"]:
            await create_notification(prev["user_id"], "outbid", auction_id, auction["title"],
                f"Tu puja en \"{auction['title']}\" ha sido superada. Precio actual: {data.amount:.2f} euros")

    bid = {
        "id": str(uuid.uuid4()),
        "user_id": user["user_id"],
        "user_name": user["name"],
        "amount": data.amount,
        "timestamp": datetime.now(timezone.utc).isoformat()
    }
    await db.auctions.update_one(
        {"id": auction_id},
        {"$push": {"bids": bid}, "$set": {"current_price": data.amount}, "$inc": {"bid_count": 1}}
    )
    await process_auto_bids(auction_id, user["user_id"])
    updated = await db.auctions.find_one({"id": auction_id}, {"_id": 0})
    return updated


@router.post("/subastas/{auction_id}/comprar-ya")
async def buy_now(auction_id: str, user=Depends(get_current_user)):
    auction = await db.auctions.find_one({"id": auction_id}, {"_id": 0})
    if not auction:
        raise HTTPException(404, "Subasta no encontrada")
    if auction["status"] != "active":
        raise HTTPException(400, "Subasta no activa")
    if auction["seller_id"] == user["user_id"]:
        raise HTTPException(400, "No puedes comprar tu propia subasta")
    if not auction.get("buy_now_price"):
        raise HTTPException(400, "Sin precio de compra inmediata")
    buy_price = auction["buy_now_price"]
    bid = {"id": str(uuid.uuid4()), "user_id": user["user_id"], "user_name": user["name"],
           "amount": buy_price, "timestamp": datetime.now(timezone.utc).isoformat(), "buy_now": True}
    await db.auctions.update_one({"id": auction_id}, {
        "$push": {"bids": bid},
        "$set": {"current_price": buy_price, "status": "finished", "winner_id": user["user_id"], "winner_name": user["name"]},
        "$inc": {"bid_count": 1}
    })
    await create_notification(user["user_id"], "auction_won", auction_id, auction["title"],
        f"Has comprado \"{auction['title']}\" por {buy_price:.2f} euros")
    await create_notification(auction["seller_id"], "auction_ended", auction_id, auction["title"],
        f"Tu subasta \"{auction['title']}\" se ha vendido por {buy_price:.2f} euros a {user['name']}")
    notified = set()
    for b in auction.get("bids", []):
        if b["user_id"] not in notified and b["user_id"] != user["user_id"]:
            await create_notification(b["user_id"], "auction_ended", auction_id, auction["title"],
                f"La subasta \"{auction['title']}\" ha sido comprada por otro usuario")
            notified.add(b["user_id"])
    updated = await db.auctions.find_one({"id": auction_id}, {"_id": 0})
    await evaluate_badges(user["user_id"])
    await evaluate_badges(auction["seller_id"])
    return updated


@router.post("/subastas/{auction_id}/cancelar")
async def cancel_auction(auction_id: str, user=Depends(get_current_user)):
    auction = await db.auctions.find_one({"id": auction_id}, {"_id": 0})
    if not auction:
        raise HTTPException(404, "Subasta no encontrada")
    if auction["seller_id"] != user["user_id"]:
        raise HTTPException(403, "Solo el vendedor puede cancelar")
    if auction["status"] != "active":
        raise HTTPException(400, "Solo se pueden cancelar subastas activas")
    has_bids = auction["bid_count"] > 0
    if has_bids:
        end_time = datetime.fromisoformat(auction["end_time"])
        now = datetime.now(timezone.utc)
        if (end_time - now) <= timedelta(hours=2):
            raise HTTPException(400, "No se puede cancelar en las ultimas 2 horas si hay pujas")
    await db.auctions.update_one({"id": auction_id},
        {"$set": {"status": "cancelled", "cancelled_at": datetime.now(timezone.utc).isoformat()}})
    notified = set()
    for b in auction.get("bids", []):
        if b["user_id"] not in notified:
            await create_notification(b["user_id"], "auction_cancelled", auction_id, auction["title"],
                f"La subasta \"{auction['title']}\" ha sido cancelada por el vendedor")
            notified.add(b["user_id"])
    return {"message": "Subasta cancelada"}


@router.post("/subastas/{auction_id}/auto-pujar")
async def set_auto_bid(auction_id: str, data: AutoBidCreate, user=Depends(get_current_user)):
    auction = await db.auctions.find_one({"id": auction_id}, {"_id": 0})
    if not auction:
        raise HTTPException(404, "Subasta no encontrada")
    if auction["status"] != "active":
        raise HTTPException(400, "Subasta no activa")
    if auction["seller_id"] == user["user_id"]:
        raise HTTPException(400, "No puedes pujar en tu propia subasta")
    min_bid = auction["current_price"] + 0.50
    if data.max_amount < min_bid:
        raise HTTPException(400, f"El maximo debe ser al menos {min_bid:.2f} euros")
    await db.auto_bids.update_many(
        {"auction_id": auction_id, "user_id": user["user_id"]}, {"$set": {"active": False}})
    doc = {"id": str(uuid.uuid4()), "auction_id": auction_id, "user_id": user["user_id"],
           "user_name": user["name"], "max_amount": data.max_amount, "active": True,
           "created_at": datetime.now(timezone.utc).isoformat()}
    await db.auto_bids.insert_one(doc)
    if not auction.get("bids") or auction["bids"][-1]["user_id"] != user["user_id"]:
        bid_amount = min_bid
        bid = {"id": str(uuid.uuid4()), "user_id": user["user_id"], "user_name": user["name"],
               "amount": bid_amount, "timestamp": datetime.now(timezone.utc).isoformat(), "auto": True}
        await db.auctions.update_one({"id": auction_id},
            {"$push": {"bids": bid}, "$set": {"current_price": bid_amount}, "$inc": {"bid_count": 1}})
        if auction.get("bids"):
            prev = auction["bids"][-1]
            if prev["user_id"] != user["user_id"]:
                await create_notification(prev["user_id"], "outbid", auction_id, auction["title"],
                    f"Tu puja en \"{auction['title']}\" ha sido superada. Precio actual: {bid_amount:.2f} euros")
    return {"message": f"Puja automatica configurada hasta {data.max_amount:.2f} euros", "max_amount": data.max_amount}


@router.get("/categorias")
async def get_categories():
    return CATEGORIES


@router.get("/ubicaciones")
async def get_locations():
    return {"peninsula": ["Madrid", "Barcelona", "Valencia", "Sevilla", "Málaga", "Bilbao", "Zaragoza", "Alicante", "Murcia", "Córdoba"], "canarias": CANARY_ISLANDS}
