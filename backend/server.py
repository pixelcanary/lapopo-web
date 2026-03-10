from fastapi import FastAPI, APIRouter, HTTPException, Depends, Header
from dotenv import load_dotenv
from starlette.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
import os
import logging
from pathlib import Path
from pydantic import BaseModel
from typing import List, Optional
import uuid
from datetime import datetime, timezone, timedelta
from passlib.context import CryptContext
import jwt

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

mongo_url = os.environ['MONGO_URL']
client = AsyncIOMotorClient(mongo_url)
db = client[os.environ['DB_NAME']]

JWT_SECRET = os.environ.get('JWT_SECRET')
JWT_ALGORITHM = "HS256"
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

app = FastAPI()
api_router = APIRouter(prefix="/api")

CANARY_ISLANDS = ["Tenerife", "Gran Canaria", "Lanzarote", "Fuerteventura", "La Palma", "La Gomera", "El Hierro"]
DURATION_MAP = {
    "1h": timedelta(hours=1),
    "6h": timedelta(hours=6),
    "12h": timedelta(hours=12),
    "24h": timedelta(hours=24),
    "3d": timedelta(days=3),
    "7d": timedelta(days=7),
}
CATEGORIES = ["Electrónica", "Hogar", "Deporte", "Moda", "Motor", "Libros", "Juguetes", "Otros"]


# Models
class UserRegister(BaseModel):
    name: str
    email: str
    password: str

class UserLogin(BaseModel):
    email: str
    password: str

class BidCreate(BaseModel):
    amount: float

class AuctionCreate(BaseModel):
    title: str
    description: str
    starting_price: float
    duration: str
    category: str
    location: str
    delivery_type: str
    images: List[str]
    buy_now_price: Optional[float] = None

class UserUpdate(BaseModel):
    name: Optional[str] = None

class AutoBidCreate(BaseModel):
    max_amount: float

class MessageCreate(BaseModel):
    receiver_id: str
    auction_id: str
    content: str


# Auth helpers
def create_token(user_id: str, name: str, email: str):
    payload = {
        "user_id": user_id,
        "name": name,
        "email": email,
        "exp": datetime.now(timezone.utc) + timedelta(hours=24)
    }
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)

def verify_token(token: str):
    try:
        return jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expirado")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Token inválido")

async def get_current_user(authorization: str = Header(None)):
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="No autorizado")
    return verify_token(authorization.split(" ")[1])

async def close_expired():
    now = datetime.now(timezone.utc).isoformat()
    expired = await db.auctions.find(
        {"status": "active", "end_time": {"$lte": now}}, {"_id": 0}
    ).to_list(100)
    for auction in expired:
        winner_update = {"status": "finished"}
        if auction.get("bids"):
            winner = auction["bids"][-1]
            winner_update["winner_id"] = winner["user_id"]
            winner_update["winner_name"] = winner["user_name"]
            await create_notification(winner["user_id"], "auction_won", auction["id"], auction["title"],
                f"Has ganado la subasta \"{auction['title']}\" por {auction['current_price']:.2f} euros")
            await create_notification(auction["seller_id"], "auction_ended", auction["id"], auction["title"],
                f"Tu subasta \"{auction['title']}\" ha terminado. Ganador: {winner['user_name']}")
            notified = {winner["user_id"], auction["seller_id"]}
            for b in auction["bids"]:
                if b["user_id"] not in notified:
                    await create_notification(b["user_id"], "outbid", auction["id"], auction["title"],
                        f"La subasta \"{auction['title']}\" ha terminado. No has ganado.")
                    notified.add(b["user_id"])
        await db.auctions.update_one({"id": auction["id"]}, {"$set": winner_update})


async def create_notification(user_id, ntype, auction_id, auction_title, message):
    doc = {
        "id": str(uuid.uuid4()),
        "user_id": user_id,
        "type": ntype,
        "auction_id": auction_id,
        "auction_title": auction_title,
        "message": message,
        "read": False,
        "created_at": datetime.now(timezone.utc).isoformat()
    }
    await db.notifications.insert_one(doc)


async def process_auto_bids(auction_id, exclude_user_id):
    auction = await db.auctions.find_one({"id": auction_id}, {"_id": 0})
    if not auction or auction["status"] != "active":
        return
    auto_bids = await db.auto_bids.find(
        {"auction_id": auction_id, "active": True, "user_id": {"$ne": exclude_user_id}}
    ).sort("max_amount", -1).to_list(100)
    if not auto_bids:
        return
    current_price = auction["current_price"]
    min_bid = current_price + 0.50
    best = auto_bids[0]
    if best["max_amount"] < min_bid:
        await db.auto_bids.update_one({"id": best["id"]}, {"$set": {"active": False}})
        await create_notification(best["user_id"], "autobid_exhausted", auction_id, auction["title"],
            f"Tu puja automatica de {best['max_amount']:.2f} euros ha sido superada en \"{auction['title']}\"")
        return
    if len(auto_bids) > 1 and auto_bids[1]["max_amount"] >= min_bid:
        second = auto_bids[1]
        bid_amount = min(round(second["max_amount"] + 0.50, 2), best["max_amount"])
        await db.auto_bids.update_one({"id": second["id"]}, {"$set": {"active": False}})
        await create_notification(second["user_id"], "autobid_exhausted", auction_id, auction["title"],
            f"Tu puja automatica de {second['max_amount']:.2f} euros ha sido superada en \"{auction['title']}\"")
    else:
        bid_amount = min_bid
    bid_amount = round(bid_amount, 2)
    bid = {
        "id": str(uuid.uuid4()),
        "user_id": best["user_id"],
        "user_name": best["user_name"],
        "amount": bid_amount,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "auto": True
    }
    await db.auctions.update_one(
        {"id": auction_id},
        {"$push": {"bids": bid}, "$set": {"current_price": bid_amount}, "$inc": {"bid_count": 1}}
    )
    await create_notification(exclude_user_id, "outbid", auction_id, auction["title"],
        f"Tu puja en \"{auction['title']}\" ha sido superada. Precio actual: {bid_amount:.2f} euros")
    if best["max_amount"] <= bid_amount:
        await db.auto_bids.update_one({"id": best["id"]}, {"$set": {"active": False}})


# AUTH ENDPOINTS
@api_router.post("/auth/register")
async def register(data: UserRegister):
    if await db.users.find_one({"email": data.email}):
        raise HTTPException(400, "Email ya registrado")
    uid = str(uuid.uuid4())
    doc = {
        "id": uid,
        "name": data.name,
        "email": data.email,
        "password_hash": pwd_context.hash(data.password),
        "created_at": datetime.now(timezone.utc).isoformat()
    }
    await db.users.insert_one(doc)
    token = create_token(uid, data.name, data.email)
    return {"token": token, "user": {"id": uid, "name": data.name, "email": data.email}}

@api_router.post("/auth/login")
async def login(data: UserLogin):
    user = await db.users.find_one({"email": data.email}, {"_id": 0})
    if not user or not pwd_context.verify(data.password, user["password_hash"]):
        raise HTTPException(401, "Credenciales incorrectas")
    token = create_token(user["id"], user["name"], user["email"])
    return {"token": token, "user": {"id": user["id"], "name": user["name"], "email": user["email"]}}


# AUCTION ENDPOINTS
@api_router.get("/subastas")
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

    return await db.auctions.find(q, {"_id": 0}).sort(sort_field).to_list(100)

@api_router.get("/subastas/{auction_id}")
async def get_auction(auction_id: str):
    await close_expired()
    auction = await db.auctions.find_one({"id": auction_id}, {"_id": 0})
    if not auction:
        raise HTTPException(404, "Subasta no encontrada")
    return auction

@api_router.post("/subastas")
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

@api_router.post("/subastas/{auction_id}/pujar")
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


# USER ENDPOINTS
@api_router.get("/usuarios/{user_id}")
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
    return {"user": user, "auctions": auctions, "active_bids": active_bids, "won_auctions": won_auctions, "favorites": fav_auctions}

@api_router.put("/usuarios/{user_id}")
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


# BUY NOW
@api_router.post("/subastas/{auction_id}/comprar-ya")
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
    return updated


# CANCEL AUCTION
@api_router.post("/subastas/{auction_id}/cancelar")
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


# AUTO-BID
@api_router.post("/subastas/{auction_id}/auto-pujar")
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


# NOTIFICATIONS
@api_router.get("/notificaciones")
async def get_notifications(user=Depends(get_current_user)):
    notifs = await db.notifications.find(
        {"user_id": user["user_id"]}, {"_id": 0}
    ).sort("created_at", -1).to_list(50)
    unread = sum(1 for n in notifs if not n.get("read"))
    return {"notifications": notifs, "unread_count": unread}

@api_router.put("/notificaciones/{notif_id}/leer")
async def mark_notification_read(notif_id: str, user=Depends(get_current_user)):
    await db.notifications.update_one(
        {"id": notif_id, "user_id": user["user_id"]}, {"$set": {"read": True}})
    return {"message": "ok"}

@api_router.put("/notificaciones/leer-todas")
async def mark_all_read(user=Depends(get_current_user)):
    await db.notifications.update_many(
        {"user_id": user["user_id"], "read": False}, {"$set": {"read": True}})
    return {"message": "ok"}


# MESSAGES
@api_router.post("/mensajes")
async def send_message(data: MessageCreate, user=Depends(get_current_user)):
    doc = {"id": str(uuid.uuid4()), "auction_id": data.auction_id, "sender_id": user["user_id"],
           "sender_name": user["name"], "receiver_id": data.receiver_id, "content": data.content,
           "created_at": datetime.now(timezone.utc).isoformat()}
    await db.messages.insert_one(doc)
    auction = await db.auctions.find_one({"id": data.auction_id}, {"_id": 0})
    title = auction["title"] if auction else "subasta"
    await create_notification(data.receiver_id, "message", data.auction_id, title,
        f"Nuevo mensaje de {user['name']} sobre \"{title}\"")
    doc.pop("_id", None)
    return doc

@api_router.get("/mensajes/{auction_id}")
async def get_messages(auction_id: str, user=Depends(get_current_user)):
    msgs = await db.messages.find(
        {"auction_id": auction_id, "$or": [{"sender_id": user["user_id"]}, {"receiver_id": user["user_id"]}]},
        {"_id": 0}
    ).sort("created_at", 1).to_list(100)
    return msgs


# FAVORITES
@api_router.post("/favoritos/{auction_id}")
async def toggle_favorite(auction_id: str, user=Depends(get_current_user)):
    existing = await db.favorites.find_one({"user_id": user["user_id"], "auction_id": auction_id})
    if existing:
        await db.favorites.delete_one({"user_id": user["user_id"], "auction_id": auction_id})
        return {"favorited": False}
    await db.favorites.insert_one({"user_id": user["user_id"], "auction_id": auction_id,
                                    "created_at": datetime.now(timezone.utc).isoformat()})
    return {"favorited": True}

@api_router.get("/favoritos")
async def get_favorites(user=Depends(get_current_user)):
    favs = await db.favorites.find({"user_id": user["user_id"]}, {"_id": 0}).to_list(100)
    ids = [f["auction_id"] for f in favs]
    auctions = await db.auctions.find({"id": {"$in": ids}}, {"_id": 0}).to_list(100) if ids else []
    return auctions


# CONTACT INFO
@api_router.get("/contacto/{auction_id}")
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

@api_router.get("/categorias")
async def get_categories():
    return CATEGORIES

@api_router.get("/ubicaciones")
async def get_locations():
    return {"peninsula": ["Madrid", "Barcelona", "Valencia", "Sevilla", "Málaga", "Bilbao", "Zaragoza", "Alicante", "Murcia", "Córdoba"], "canarias": CANARY_ISLANDS}


# Include router
app.include_router(api_router)

app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=os.environ.get('CORS_ORIGINS', '*').split(','),
    allow_methods=["*"],
    allow_headers=["*"],
)

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


# SEED DATA
@app.on_event("startup")
async def seed_data():
    count = await db.auctions.count_documents({})
    if count > 0:
        return
    logger.info("Seeding database...")

    demo_id = str(uuid.uuid4())
    maria_id = str(uuid.uuid4())
    await db.users.insert_many([
        {"id": demo_id, "name": "Carlos López", "email": "carlos@lapopo.es", "password_hash": pwd_context.hash("demo123"), "created_at": datetime.now(timezone.utc).isoformat()},
        {"id": maria_id, "name": "María García", "email": "maria@lapopo.es", "password_hash": pwd_context.hash("demo123"), "created_at": datetime.now(timezone.utc).isoformat()},
    ])

    now = datetime.now(timezone.utc)
    seeds = [
        {"id": str(uuid.uuid4()), "title": "Camara Canon EOS 500D - Perfecta", "description": "Camara reflex Canon EOS 500D en perfecto estado. Incluye objetivo 18-55mm, cargador y bolsa.", "images": ["https://images.unsplash.com/photo-1588768904397-cb062c91ba55?auto=format&fit=crop&q=80&w=600"], "starting_price": 45.0, "current_price": 67.50, "buy_now_price": 120.0, "duration": "3d", "end_time": (now + timedelta(days=2, hours=5)).isoformat(), "category": "Electrónica", "location": "Madrid", "delivery_type": "shipping", "seller_id": demo_id, "seller_name": "Carlos López", "bids": [{"id": str(uuid.uuid4()), "user_id": maria_id, "user_name": "María García", "amount": 50.0, "timestamp": (now - timedelta(hours=5)).isoformat()}, {"id": str(uuid.uuid4()), "user_id": maria_id, "user_name": "María García", "amount": 67.50, "timestamp": (now - timedelta(hours=2)).isoformat()}], "bid_count": 2, "status": "active", "winner_id": None, "winner_name": None, "created_at": (now - timedelta(days=1)).isoformat()},
        {"id": str(uuid.uuid4()), "title": "iPhone 13 - 128GB Azul", "description": "iPhone 13 en color azul, 128GB. Pantalla y bateria al 92%. Sin arañazos. Incluye caja original.", "images": ["https://images.unsplash.com/photo-1592750475338-74b7b21085ab?auto=format&fit=crop&q=80&w=600"], "starting_price": 200.0, "current_price": 245.0, "buy_now_price": 400.0, "duration": "7d", "end_time": (now + timedelta(days=5, hours=12)).isoformat(), "category": "Electrónica", "location": "Barcelona", "delivery_type": "both", "seller_id": maria_id, "seller_name": "María García", "bids": [{"id": str(uuid.uuid4()), "user_id": demo_id, "user_name": "Carlos López", "amount": 220.0, "timestamp": (now - timedelta(hours=10)).isoformat()}, {"id": str(uuid.uuid4()), "user_id": demo_id, "user_name": "Carlos López", "amount": 245.0, "timestamp": (now - timedelta(hours=3)).isoformat()}], "bid_count": 2, "status": "active", "winner_id": None, "winner_name": None, "created_at": (now - timedelta(days=2)).isoformat()},
        {"id": str(uuid.uuid4()), "title": "Bicicleta de montaña Scott Scale", "description": "Bicicleta MTB Scott Scale 970 talla L. Cuadro de aluminio, frenos de disco hidraulicos.", "images": ["https://images.unsplash.com/photo-1532298229144-0ec0c57515c7?auto=format&fit=crop&q=80&w=600"], "starting_price": 150.0, "current_price": 185.0, "buy_now_price": None, "duration": "3d", "end_time": (now + timedelta(hours=18)).isoformat(), "category": "Deporte", "location": "Valencia", "delivery_type": "pickup", "seller_id": demo_id, "seller_name": "Carlos López", "bids": [{"id": str(uuid.uuid4()), "user_id": maria_id, "user_name": "María García", "amount": 170.0, "timestamp": (now - timedelta(hours=8)).isoformat()}, {"id": str(uuid.uuid4()), "user_id": maria_id, "user_name": "María García", "amount": 185.0, "timestamp": (now - timedelta(hours=1)).isoformat()}], "bid_count": 2, "status": "active", "winner_id": None, "winner_name": None, "created_at": (now - timedelta(days=1, hours=6)).isoformat()},
        {"id": str(uuid.uuid4()), "title": "Tabla de Surf 6'2 - Perfecta para Canarias", "description": "Tabla de surf shortboard 6'2. Ideal para las olas de Canarias. Incluye quillas y funda.", "images": ["https://images.unsplash.com/photo-1675008814982-a18b8efb7e7e?auto=format&fit=crop&q=80&w=600"], "starting_price": 80.0, "current_price": 95.0, "buy_now_price": 150.0, "duration": "7d", "end_time": (now + timedelta(days=4)).isoformat(), "category": "Deporte", "location": "Tenerife", "delivery_type": "pickup", "seller_id": maria_id, "seller_name": "María García", "bids": [{"id": str(uuid.uuid4()), "user_id": demo_id, "user_name": "Carlos López", "amount": 95.0, "timestamp": (now - timedelta(hours=6)).isoformat()}], "bid_count": 1, "status": "active", "winner_id": None, "winner_name": None, "created_at": (now - timedelta(days=3)).isoformat()},
        {"id": str(uuid.uuid4()), "title": "PlayStation 5 + 2 Mandos", "description": "PS5 con lector de discos. Incluye 2 mandos DualSense y 3 juegos fisicos.", "images": ["https://images.unsplash.com/photo-1606144042614-b2417e99c4e3?auto=format&fit=crop&q=80&w=600"], "starting_price": 250.0, "current_price": 310.0, "buy_now_price": 450.0, "duration": "3d", "end_time": (now + timedelta(days=1, hours=8)).isoformat(), "category": "Electrónica", "location": "Gran Canaria", "delivery_type": "both", "seller_id": demo_id, "seller_name": "Carlos López", "bids": [{"id": str(uuid.uuid4()), "user_id": maria_id, "user_name": "María García", "amount": 280.0, "timestamp": (now - timedelta(hours=12)).isoformat()}, {"id": str(uuid.uuid4()), "user_id": maria_id, "user_name": "María García", "amount": 310.0, "timestamp": (now - timedelta(hours=4)).isoformat()}], "bid_count": 2, "status": "active", "winner_id": None, "winner_name": None, "created_at": (now - timedelta(days=2)).isoformat()},
        {"id": str(uuid.uuid4()), "title": "Mesa de comedor vintage roble", "description": "Preciosa mesa de comedor estilo vintage en madera de roble macizo. 160x90cm.", "images": ["https://images.unsplash.com/photo-1592078615290-033ee584e267?auto=format&fit=crop&q=80&w=600"], "starting_price": 120.0, "current_price": 120.0, "buy_now_price": None, "duration": "7d", "end_time": (now + timedelta(days=6)).isoformat(), "category": "Hogar", "location": "Sevilla", "delivery_type": "pickup", "seller_id": maria_id, "seller_name": "María García", "bids": [], "bid_count": 0, "status": "active", "winner_id": None, "winner_name": None, "created_at": (now - timedelta(days=1)).isoformat()},
        {"id": str(uuid.uuid4()), "title": "Vestido vintage años 70", "description": "Vestido original de los años 70 en perfecto estado. Talla S/M. Estampado floral unico.", "images": ["https://images.unsplash.com/photo-1523381210434-271e8be1f52b?auto=format&fit=crop&q=80&w=600"], "starting_price": 15.0, "current_price": 22.50, "buy_now_price": 45.0, "duration": "24h", "end_time": (now + timedelta(hours=6)).isoformat(), "category": "Moda", "location": "Fuerteventura", "delivery_type": "both", "seller_id": maria_id, "seller_name": "María García", "bids": [{"id": str(uuid.uuid4()), "user_id": demo_id, "user_name": "Carlos López", "amount": 18.0, "timestamp": (now - timedelta(hours=15)).isoformat()}, {"id": str(uuid.uuid4()), "user_id": demo_id, "user_name": "Carlos López", "amount": 22.50, "timestamp": (now - timedelta(hours=7)).isoformat()}], "bid_count": 2, "status": "active", "winner_id": None, "winner_name": None, "created_at": (now - timedelta(hours=18)).isoformat()},
        {"id": str(uuid.uuid4()), "title": "Coleccion 50 vinilos rock clasico", "description": "Coleccion de 50 vinilos de rock clasico. Beatles, Pink Floyd, Led Zeppelin, Queen.", "images": ["https://images.unsplash.com/photo-1563552744114-78ff178ac8de?auto=format&fit=crop&q=80&w=600"], "starting_price": 1.0, "current_price": 35.0, "buy_now_price": None, "duration": "3d", "end_time": (now + timedelta(days=1, hours=3)).isoformat(), "category": "Otros", "location": "La Palma", "delivery_type": "pickup", "seller_id": demo_id, "seller_name": "Carlos López", "bids": [{"id": str(uuid.uuid4()), "user_id": maria_id, "user_name": "María García", "amount": 15.0, "timestamp": (now - timedelta(hours=30)).isoformat()}, {"id": str(uuid.uuid4()), "user_id": maria_id, "user_name": "María García", "amount": 25.0, "timestamp": (now - timedelta(hours=15)).isoformat()}, {"id": str(uuid.uuid4()), "user_id": maria_id, "user_name": "María García", "amount": 35.0, "timestamp": (now - timedelta(hours=5)).isoformat()}], "bid_count": 3, "status": "active", "winner_id": None, "winner_name": None, "created_at": (now - timedelta(days=2)).isoformat()},
        {"id": str(uuid.uuid4()), "title": "Sillon Eames replica - Como nuevo", "description": "Replica del famoso sillon Eames Lounge Chair. Piel sintetica negra, estructura de nogal.", "images": ["https://images.unsplash.com/photo-1567538096630-e0c55bd6374c?auto=format&fit=crop&q=80&w=600"], "starting_price": 1.0, "current_price": 55.0, "buy_now_price": None, "duration": "7d", "end_time": (now + timedelta(days=5, hours=20)).isoformat(), "category": "Hogar", "location": "Málaga", "delivery_type": "pickup", "seller_id": maria_id, "seller_name": "María García", "bids": [{"id": str(uuid.uuid4()), "user_id": demo_id, "user_name": "Carlos López", "amount": 30.0, "timestamp": (now - timedelta(hours=40)).isoformat()}, {"id": str(uuid.uuid4()), "user_id": demo_id, "user_name": "Carlos López", "amount": 55.0, "timestamp": (now - timedelta(hours=10)).isoformat()}], "bid_count": 2, "status": "active", "winner_id": None, "winner_name": None, "created_at": (now - timedelta(days=2)).isoformat()},
        {"id": str(uuid.uuid4()), "title": "Patinete electrico Xiaomi Pro 2", "description": "Patinete electrico Xiaomi Mi Electric Scooter Pro 2. 45km de autonomia.", "images": ["https://images.unsplash.com/photo-1558618666-fcd25c85f82e?auto=format&fit=crop&q=80&w=600"], "starting_price": 1.0, "current_price": 1.0, "buy_now_price": 180.0, "duration": "24h", "end_time": (now + timedelta(hours=20)).isoformat(), "category": "Motor", "location": "Tenerife", "delivery_type": "pickup", "seller_id": demo_id, "seller_name": "Carlos López", "bids": [], "bid_count": 0, "status": "active", "winner_id": None, "winner_name": None, "created_at": (now - timedelta(hours=4)).isoformat()},
        {"id": str(uuid.uuid4()), "title": "Lote libros ciencia ficcion", "description": "Lote de 20 libros de ciencia ficcion. Asimov, Clarke, Philip K. Dick.", "images": ["https://images.unsplash.com/photo-1495446815901-a7297e633e8d?auto=format&fit=crop&q=80&w=600"], "starting_price": 5.0, "current_price": 12.50, "buy_now_price": None, "duration": "3d", "end_time": (now + timedelta(hours=10)).isoformat(), "category": "Libros", "location": "Gran Canaria", "delivery_type": "both", "seller_id": maria_id, "seller_name": "María García", "bids": [{"id": str(uuid.uuid4()), "user_id": demo_id, "user_name": "Carlos López", "amount": 8.0, "timestamp": (now - timedelta(hours=20)).isoformat()}, {"id": str(uuid.uuid4()), "user_id": demo_id, "user_name": "Carlos López", "amount": 12.50, "timestamp": (now - timedelta(hours=5)).isoformat()}], "bid_count": 2, "status": "active", "winner_id": None, "winner_name": None, "created_at": (now - timedelta(days=2, hours=14)).isoformat()},
    ]
    await db.auctions.insert_many(seeds)
    logger.info(f"Seeded {len(seeds)} auctions and 2 demo users")

@app.on_event("shutdown")
async def shutdown():
    client.close()
