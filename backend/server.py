from fastapi import FastAPI, APIRouter, HTTPException, Depends, Header, Request, UploadFile, File, Form
from dotenv import load_dotenv
from starlette.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
import os
import logging
from pathlib import Path
from pydantic import BaseModel
from typing import List, Optional, Dict
import uuid
import secrets
from datetime import datetime, timezone, timedelta
from passlib.context import CryptContext
import jwt
import cloudinary
import cloudinary.uploader
from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail
from emergentintegrations.payments.stripe.checkout import StripeCheckout, CheckoutSessionRequest

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

cloudinary.config(
    cloud_name=os.environ.get("CLOUDINARY_CLOUD_NAME"),
    api_key=os.environ.get("CLOUDINARY_API_KEY"),
    api_secret=os.environ.get("CLOUDINARY_API_SECRET"),
)

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

class RatingCreate(BaseModel):
    auction_id: str
    rated_user_id: str
    rating: int
    comment: Optional[str] = None

class DisputeCreate(BaseModel):
    auction_id: str
    reason: str
    description: str

class DisputeMessage(BaseModel):
    content: str
    images: Optional[List[str]] = None

class DisputeStatusUpdate(BaseModel):
    status: str

class CheckoutRequest(BaseModel):
    plan: Optional[str] = None
    featured_type: Optional[str] = None
    auction_id: Optional[str] = None
    origin_url: str

class ChangePassword(BaseModel):
    current_password: str
    new_password: str

class ForgotPassword(BaseModel):
    email: str

class ResetPassword(BaseModel):
    token: str
    new_password: str

class ChatMessage(BaseModel):
    auction_id: str
    receiver_id: str
    content: str
    images: Optional[List[str]] = None

class BadgeCreate(BaseModel):
    name: str
    description: str
    emoji: str
    condition_type: str
    condition_value: int
    auto: bool = True

class BadgeAssign(BaseModel):
    user_id: str


# Plan & Featured constants
PLANS = {
    "free": {"name": "Gratis", "price": 0.0, "max_auctions": 5, "featured_free": 0, "verified": False},
    "vendedor": {"name": "Vendedor", "price": 2.99, "max_auctions": None, "featured_free": 1, "verified": False},
    "pro": {"name": "Pro", "price": 6.99, "max_auctions": None, "featured_free": 3, "verified": True},
}
FEATURED_OPTIONS = {
    "destacada": {"name": "Subasta Destacada", "price": 0.49, "description": "Badge dorado, prioridad en su seccion"},
    "home": {"name": "Subasta en Home", "price": 0.99, "description": "Aparece en Subastas Destacadas de la portada"},
    "urgente": {"name": "Urgente", "price": 0.29, "description": "Badge naranja Termina pronto con prioridad visual"},
}
DISPUTE_REASONS = [
    "Producto no recibido",
    "Producto no coincide con la descripcion",
    "Vendedor no responde",
    "Comprador no paga",
    "Producto danado",
    "Otro",
]


# Auth helpers
def create_token(user_id: str, name: str, email: str, is_admin: bool = False):
    payload = {
        "user_id": user_id,
        "name": name,
        "email": email,
        "is_admin": is_admin,
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

async def require_admin(authorization: str = Header(None)):
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="No autorizado")
    user = verify_token(authorization.split(" ")[1])
    if not user.get("is_admin"):
        raise HTTPException(status_code=403, detail="Solo administradores")
    return user

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
            await evaluate_badges(winner["user_id"])
            await evaluate_badges(auction["seller_id"])
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


async def enrich_with_ratings(auctions):
    seller_ids = list(set(a["seller_id"] for a in auctions))
    if not seller_ids:
        return auctions
    users = await db.users.find({"id": {"$in": seller_ids}}, {"_id": 0, "id": 1, "rating_avg": 1, "rating_count": 1, "plan": 1}).to_list(len(seller_ids))
    rating_map = {u["id"]: (u.get("rating_avg", 0), u.get("rating_count", 0), u.get("plan", "free")) for u in users}
    for a in auctions:
        avg, count, plan = rating_map.get(a["seller_id"], (0, 0, "free"))
        a["seller_rating_avg"] = avg
        a["seller_rating_count"] = count
        a["seller_plan"] = plan
    return auctions


async def enrich_with_featured(auctions):
    auc_ids = [a["id"] for a in auctions]
    if not auc_ids:
        return auctions
    feats = await db.featured_listings.find({"auction_id": {"$in": auc_ids}, "active": True}, {"_id": 0}).to_list(500)
    feat_map = {}
    for f in feats:
        feat_map.setdefault(f["auction_id"], []).append(f["type"])
    for a in auctions:
        a["featured"] = feat_map.get(a["id"], [])
    return auctions


async def get_payments_enabled():
    s = await db.settings.find_one({"key": "payments_enabled"}, {"_id": 0})
    return s["value"] if s else False


async def get_user_plan(user_id):
    u = await db.users.find_one({"id": user_id}, {"_id": 0, "plan": 1})
    return u.get("plan", "free") if u else "free"


async def count_user_auctions_this_month(user_id):
    now = datetime.now(timezone.utc)
    start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    return await db.auctions.count_documents({"seller_id": user_id, "created_at": {"$gte": start.isoformat()}})


DEFAULT_BADGES = [
    {"name": "Primera venta", "description": "Completaste tu primera venta", "emoji": "🏷️", "condition_type": "sales", "condition_value": 1, "auto": True},
    {"name": "5 ventas", "description": "5 subastas vendidas", "emoji": "🎯", "condition_type": "sales", "condition_value": 5, "auto": True},
    {"name": "10 ventas", "description": "10 subastas vendidas", "emoji": "🏆", "condition_type": "sales", "condition_value": 10, "auto": True},
    {"name": "50 ventas", "description": "50 subastas vendidas", "emoji": "💎", "condition_type": "sales", "condition_value": 50, "auto": True},
    {"name": "100% positivas", "description": "Todas tus valoraciones son positivas (min 3)", "emoji": "⭐", "condition_type": "positive_ratings", "condition_value": 100, "auto": True},
    {"name": "Comprador frecuente", "description": "Has ganado 5 subastas", "emoji": "🛒", "condition_type": "purchases", "condition_value": 5, "auto": True},
    {"name": "Canario", "description": "Has vendido en las Islas Canarias", "emoji": "🌴", "condition_type": "canarias_sales", "condition_value": 1, "auto": True},
]


async def evaluate_badges(user_id):
    badges = await db.badges.find({"auto": True}, {"_id": 0}).to_list(100)
    existing = set()
    for ub in await db.user_badges.find({"user_id": user_id}, {"_id": 0, "badge_id": 1}).to_list(100):
        existing.add(ub["badge_id"])
    for badge in badges:
        if badge["id"] in existing:
            continue
        earned = False
        ct = badge["condition_type"]
        cv = badge["condition_value"]
        if ct == "sales":
            count = await db.auctions.count_documents({"seller_id": user_id, "status": "finished", "winner_id": {"$exists": True}})
            earned = count >= cv
        elif ct == "purchases":
            count = await db.auctions.count_documents({"winner_id": user_id, "status": "finished"})
            earned = count >= cv
        elif ct == "positive_ratings":
            ratings = await db.ratings.find({"rated_id": user_id}, {"_id": 0, "rating": 1}).to_list(1000)
            if len(ratings) >= 3:
                earned = all(r["rating"] >= 4 for r in ratings)
        elif ct == "canarias_sales":
            count = await db.auctions.count_documents({"seller_id": user_id, "status": "finished", "location": {"$in": CANARY_ISLANDS}})
            earned = count >= cv
        elif ct == "bids_received":
            pipeline = [{"$match": {"seller_id": user_id}}, {"$group": {"_id": None, "total": {"$sum": "$bid_count"}}}]
            agg = await db.auctions.aggregate(pipeline).to_list(1)
            total = agg[0]["total"] if agg else 0
            earned = total >= cv
        elif ct == "positive_pct":
            ratings = await db.ratings.find({"rated_id": user_id}, {"_id": 0, "rating": 1}).to_list(1000)
            if len(ratings) >= 3:
                pct = (sum(1 for r in ratings if r["rating"] >= 4) / len(ratings)) * 100
                earned = pct >= cv
        if earned:
            await db.user_badges.insert_one({"user_id": user_id, "badge_id": badge["id"], "badge_name": badge["name"], "awarded_at": datetime.now(timezone.utc).isoformat()})


async def send_recovery_email(email: str, token: str, frontend_url: str):
    try:
        sg = SendGridAPIClient(os.environ.get("SENDGRID_API_KEY"))
        reset_link = f"{frontend_url}/auth?tab=reset&token={token}"
        msg = Mail(
            from_email=os.environ.get("SENDGRID_FROM_EMAIL", "noreply@lapopo.es"),
            to_emails=email,
            subject="Lapopo - Recupera tu contrasena",
            html_content=f'<p>Hola,</p><p>Haz clic en el siguiente enlace para restablecer tu contrasena:</p><p><a href="{reset_link}">{reset_link}</a></p><p>Este enlace expira en 1 hora.</p><p>Si no solicitaste este cambio, ignora este email.</p>',
        )
        sg.send(msg)
        logger.info(f"Recovery email sent to {email}")
    except Exception as e:
        logger.error(f"SendGrid error: {e}")


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
    token = create_token(uid, data.name, data.email, False)
    return {"token": token, "user": {"id": uid, "name": data.name, "email": data.email, "is_admin": False}}

@api_router.post("/auth/login")
async def login(data: UserLogin):
    user = await db.users.find_one({"email": data.email}, {"_id": 0})
    if not user or not pwd_context.verify(data.password, user["password_hash"]):
        raise HTTPException(401, "Credenciales incorrectas")
    is_admin = user.get("is_admin", False)
    token = create_token(user["id"], user["name"], user["email"], is_admin)
    return {"token": token, "user": {"id": user["id"], "name": user["name"], "email": user["email"], "is_admin": is_admin}}


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

    auctions = await db.auctions.find(q, {"_id": 0}).sort(sort_field).to_list(100)
    auctions = await enrich_with_ratings(auctions)
    auctions = await enrich_with_featured(auctions)
    return auctions

@api_router.get("/subastas/autocomplete")
async def search_autocomplete(q: str = ""):
    if len(q) < 2:
        return []
    auctions = await db.auctions.find(
        {"status": "active", "title": {"$regex": q, "$options": "i"}},
        {"_id": 0, "id": 1, "title": 1, "images": 1, "current_price": 1}
    ).limit(8).to_list(8)
    return auctions

@api_router.get("/subastas/{auction_id}")
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
    await evaluate_badges(user["user_id"])
    await evaluate_badges(auction["seller_id"])
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


# MESSAGES / CHAT
@api_router.post("/mensajes")
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

@api_router.get("/mensajes/{auction_id}")
async def get_messages(auction_id: str, user=Depends(get_current_user)):
    msgs = await db.messages.find(
        {"auction_id": auction_id, "$or": [{"sender_id": user["user_id"]}, {"receiver_id": user["user_id"]}]},
        {"_id": 0}
    ).sort("created_at", 1).to_list(200)
    return msgs

@api_router.get("/chat/conversaciones")
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


# RATINGS
@api_router.post("/valoraciones")
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

@api_router.get("/valoraciones/usuario/{user_id}")
async def get_user_ratings(user_id: str):
    ratings = await db.ratings.find({"rated_id": user_id}, {"_id": 0}).sort("created_at", -1).to_list(100)
    u = await db.users.find_one({"id": user_id}, {"_id": 0, "rating_avg": 1, "rating_count": 1})
    return {"ratings": ratings, "average": u.get("rating_avg", 0) if u else 0, "count": u.get("rating_count", 0) if u else 0}

@api_router.get("/valoraciones/subasta/{auction_id}")
async def get_auction_ratings(auction_id: str, user=Depends(get_current_user)):
    ratings = await db.ratings.find({"auction_id": auction_id}, {"_id": 0}).to_list(10)
    my_ratings = [r for r in ratings if r["rater_id"] == user["user_id"]]
    return {"ratings": ratings, "my_ratings": my_ratings}


# ADMIN
@api_router.get("/admin/stats")
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

@api_router.get("/admin/usuarios")
async def admin_list_users(user=Depends(require_admin)):
    users = await db.users.find({}, {"_id": 0, "password_hash": 0}).sort("created_at", -1).to_list(500)
    for u in users:
        u["auction_count"] = await db.auctions.count_documents({"seller_id": u["id"]})
    return users

@api_router.get("/admin/subastas")
async def admin_list_auctions(status: Optional[str] = None, user=Depends(require_admin)):
    q = {}
    if status:
        q["status"] = status
    auctions = await db.auctions.find(q, {"_id": 0}).sort("created_at", -1).to_list(500)
    return auctions

@api_router.delete("/admin/usuarios/{user_id}")
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

@api_router.delete("/admin/subastas/{auction_id}")
async def admin_delete_auction(auction_id: str, user=Depends(require_admin)):
    auction = await db.auctions.find_one({"id": auction_id}, {"_id": 0})
    if not auction:
        raise HTTPException(404, "Subasta no encontrada")
    await db.auctions.delete_one({"id": auction_id})
    await db.favorites.delete_many({"auction_id": auction_id})
    await db.auto_bids.delete_many({"auction_id": auction_id})
    await db.ratings.delete_many({"auction_id": auction_id})
    return {"message": "Subasta eliminada"}


# PLANS & SUBSCRIPTIONS
@api_router.get("/planes")
async def get_plans():
    payments_on = await get_payments_enabled()
    return {"plans": PLANS, "featured_options": FEATURED_OPTIONS, "payments_enabled": payments_on, "dispute_reasons": DISPUTE_REASONS}

@api_router.get("/suscripciones/mi-plan")
async def my_plan(user=Depends(get_current_user)):
    u = await db.users.find_one({"id": user["user_id"]}, {"_id": 0, "plan": 1})
    plan = u.get("plan", "free") if u else "free"
    payments_on = await get_payments_enabled()
    auc_count = await count_user_auctions_this_month(user["user_id"])
    plan_info = PLANS.get(plan, PLANS["free"])
    return {"plan": plan, "plan_info": plan_info, "auctions_this_month": auc_count, "payments_enabled": payments_on}

@api_router.post("/suscripciones/crear-sesion")
async def create_subscription_session(data: CheckoutRequest, request: Request, user=Depends(get_current_user)):
    if data.plan not in ["vendedor", "pro"]:
        raise HTTPException(400, "Plan no valido")
    plan_info = PLANS[data.plan]
    stripe_key = os.environ.get("STRIPE_API_KEY")
    host_url = str(request.base_url).rstrip("/")
    webhook_url = f"{host_url}/api/webhook/stripe"
    stripe_checkout = StripeCheckout(api_key=stripe_key, webhook_url=webhook_url)
    success_url = f"{data.origin_url}/precios?session_id={{CHECKOUT_SESSION_ID}}"
    cancel_url = f"{data.origin_url}/precios"
    req = CheckoutSessionRequest(
        amount=plan_info["price"], currency="eur",
        success_url=success_url, cancel_url=cancel_url,
        metadata={"user_id": user["user_id"], "type": "subscription", "plan": data.plan}
    )
    session = await stripe_checkout.create_checkout_session(req)
    await db.payment_transactions.insert_one({
        "id": str(uuid.uuid4()), "session_id": session.session_id, "user_id": user["user_id"],
        "type": "subscription", "plan": data.plan, "amount": plan_info["price"], "currency": "eur",
        "payment_status": "pending", "created_at": datetime.now(timezone.utc).isoformat()
    })
    return {"url": session.url, "session_id": session.session_id}

@api_router.post("/suscripciones/cancelar")
async def cancel_subscription(user=Depends(get_current_user)):
    await db.users.update_one({"id": user["user_id"]}, {"$set": {"plan": "free"}})
    return {"message": "Plan cancelado. Ahora tienes el plan Gratis."}


# FEATURED LISTINGS
@api_router.post("/destacados/crear-sesion")
async def create_featured_session(data: CheckoutRequest, request: Request, user=Depends(get_current_user)):
    if data.featured_type not in FEATURED_OPTIONS:
        raise HTTPException(400, "Tipo de destacado no valido")
    if not data.auction_id:
        raise HTTPException(400, "auction_id requerido")
    auction = await db.auctions.find_one({"id": data.auction_id, "seller_id": user["user_id"]}, {"_id": 0})
    if not auction:
        raise HTTPException(404, "Subasta no encontrada o no eres el propietario")
    feat_info = FEATURED_OPTIONS[data.featured_type]
    stripe_key = os.environ.get("STRIPE_API_KEY")
    host_url = str(request.base_url).rstrip("/")
    webhook_url = f"{host_url}/api/webhook/stripe"
    stripe_checkout = StripeCheckout(api_key=stripe_key, webhook_url=webhook_url)
    success_url = f"{data.origin_url}/subasta/{data.auction_id}?session_id={{CHECKOUT_SESSION_ID}}"
    cancel_url = f"{data.origin_url}/subasta/{data.auction_id}"
    req = CheckoutSessionRequest(
        amount=feat_info["price"], currency="eur",
        success_url=success_url, cancel_url=cancel_url,
        metadata={"user_id": user["user_id"], "type": "featured", "featured_type": data.featured_type, "auction_id": data.auction_id}
    )
    session = await stripe_checkout.create_checkout_session(req)
    await db.payment_transactions.insert_one({
        "id": str(uuid.uuid4()), "session_id": session.session_id, "user_id": user["user_id"],
        "type": "featured", "featured_type": data.featured_type, "auction_id": data.auction_id,
        "amount": feat_info["price"], "currency": "eur",
        "payment_status": "pending", "created_at": datetime.now(timezone.utc).isoformat()
    })
    return {"url": session.url, "session_id": session.session_id}

@api_router.post("/destacados/activar-gratis")
async def activate_free_featured(data: CheckoutRequest, user=Depends(get_current_user)):
    if data.featured_type not in FEATURED_OPTIONS:
        raise HTTPException(400, "Tipo no valido")
    if not data.auction_id:
        raise HTTPException(400, "auction_id requerido")
    auction = await db.auctions.find_one({"id": data.auction_id, "seller_id": user["user_id"]}, {"_id": 0})
    if not auction:
        raise HTTPException(404, "Subasta no encontrada")
    plan = await get_user_plan(user["user_id"])
    plan_info = PLANS.get(plan, PLANS["free"])
    free_featured = plan_info.get("featured_free", 0)
    if free_featured <= 0:
        raise HTTPException(403, "Tu plan no incluye destacados gratis")
    now = datetime.now(timezone.utc)
    start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    used = await db.featured_listings.count_documents({"user_id": user["user_id"], "free": True, "created_at": {"$gte": start.isoformat()}})
    if used >= free_featured:
        raise HTTPException(403, f"Ya has usado tus {free_featured} destacados gratis este mes")
    await db.featured_listings.insert_one({
        "id": str(uuid.uuid4()), "auction_id": data.auction_id, "user_id": user["user_id"],
        "type": data.featured_type, "active": True, "free": True,
        "created_at": now.isoformat()
    })
    return {"message": "Destacado activado gratis"}


# PAYMENT STATUS & WEBHOOK
@api_router.get("/pagos/estado/{session_id}")
async def check_payment_status(session_id: str, request: Request, user=Depends(get_current_user)):
    tx = await db.payment_transactions.find_one({"session_id": session_id}, {"_id": 0})
    if not tx:
        raise HTTPException(404, "Transaccion no encontrada")
    if tx.get("payment_status") == "paid":
        return {"status": "paid", "type": tx.get("type"), "plan": tx.get("plan")}
    stripe_key = os.environ.get("STRIPE_API_KEY")
    host_url = str(request.base_url).rstrip("/")
    webhook_url = f"{host_url}/api/webhook/stripe"
    stripe_checkout = StripeCheckout(api_key=stripe_key, webhook_url=webhook_url)
    status = await stripe_checkout.get_checkout_status(session_id)
    if status.payment_status == "paid":
        existing = await db.payment_transactions.find_one({"session_id": session_id, "payment_status": "paid"})
        if not existing:
            await db.payment_transactions.update_one({"session_id": session_id}, {"$set": {"payment_status": "paid", "updated_at": datetime.now(timezone.utc).isoformat()}})
            if tx.get("type") == "subscription":
                await db.users.update_one({"id": tx["user_id"]}, {"$set": {"plan": tx["plan"]}})
            elif tx.get("type") == "featured":
                await db.featured_listings.insert_one({
                    "id": str(uuid.uuid4()), "auction_id": tx["auction_id"], "user_id": tx["user_id"],
                    "type": tx["featured_type"], "active": True, "free": False,
                    "created_at": datetime.now(timezone.utc).isoformat()
                })
    return {"status": status.status, "payment_status": status.payment_status, "type": tx.get("type"), "plan": tx.get("plan")}

@api_router.post("/webhook/stripe")
async def stripe_webhook(request: Request):
    body = await request.body()
    sig = request.headers.get("Stripe-Signature", "")
    stripe_key = os.environ.get("STRIPE_API_KEY")
    host_url = str(request.base_url).rstrip("/")
    webhook_url = f"{host_url}/api/webhook/stripe"
    stripe_checkout = StripeCheckout(api_key=stripe_key, webhook_url=webhook_url)
    try:
        event = await stripe_checkout.handle_webhook(body, sig)
        if event.payment_status == "paid":
            tx = await db.payment_transactions.find_one({"session_id": event.session_id, "payment_status": {"$ne": "paid"}})
            if tx:
                await db.payment_transactions.update_one({"session_id": event.session_id}, {"$set": {"payment_status": "paid"}})
                if tx.get("type") == "subscription":
                    await db.users.update_one({"id": tx["user_id"]}, {"$set": {"plan": tx["plan"]}})
                elif tx.get("type") == "featured":
                    await db.featured_listings.insert_one({
                        "id": str(uuid.uuid4()), "auction_id": tx["auction_id"], "user_id": tx["user_id"],
                        "type": tx["featured_type"], "active": True, "free": False,
                        "created_at": datetime.now(timezone.utc).isoformat()
                    })
    except Exception as e:
        logger.error(f"Webhook error: {e}")
    return {"received": True}


# DISPUTES
@api_router.post("/disputas")
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

@api_router.get("/disputas/mis-disputas")
async def my_disputes(user=Depends(get_current_user)):
    disputes = await db.disputes.find(
        {"$or": [{"reporter_id": user["user_id"]}, {"reported_id": user["user_id"]}]},
        {"_id": 0}
    ).sort("created_at", -1).to_list(50)
    return disputes

@api_router.get("/disputas/{dispute_id}")
async def get_dispute(dispute_id: str, user=Depends(get_current_user)):
    d = await db.disputes.find_one({"id": dispute_id}, {"_id": 0})
    if not d:
        raise HTTPException(404, "Disputa no encontrada")
    uid = user["user_id"]
    is_admin = user.get("is_admin", False)
    if not is_admin and uid != d["reporter_id"] and uid != d["reported_id"]:
        raise HTTPException(403, "No tienes acceso a esta disputa")
    return d

@api_router.post("/disputas/{dispute_id}/mensaje")
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

@api_router.get("/admin/disputas")
async def admin_list_disputes(status: Optional[str] = None, user=Depends(require_admin)):
    q = {}
    if status:
        q["status"] = status
    return await db.disputes.find(q, {"_id": 0}).sort("created_at", -1).to_list(200)

@api_router.put("/admin/disputas/{dispute_id}/estado")
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
@api_router.get("/admin/config")
async def get_admin_config(user=Depends(require_admin)):
    payments_on = await get_payments_enabled()
    return {"payments_enabled": payments_on}

@api_router.put("/admin/config")
async def update_admin_config(config: dict, user=Depends(require_admin)):
    if "payments_enabled" in config:
        await db.settings.update_one({"key": "payments_enabled"}, {"$set": {"value": config["payments_enabled"]}}, upsert=True)
    return {"message": "Configuracion actualizada"}


# CLOUDINARY UPLOAD
@api_router.post("/upload")
async def upload_image(file: UploadFile = File(...), user=Depends(get_current_user)):
    if not file.content_type or not file.content_type.startswith("image/"):
        raise HTTPException(400, "Solo se permiten imagenes")
    contents = await file.read()
    if len(contents) > 10 * 1024 * 1024:
        raise HTTPException(400, "Imagen demasiado grande (max 10MB)")
    result = cloudinary.uploader.upload(contents, folder="lapopo", resource_type="image")
    return {"url": result["secure_url"], "public_id": result["public_id"]}

@api_router.post("/upload/base64")
async def upload_base64(data: dict, user=Depends(get_current_user)):
    img = data.get("image", "")
    if not img:
        raise HTTPException(400, "Imagen requerida")
    result = cloudinary.uploader.upload(img, folder="lapopo", resource_type="image")
    return {"url": result["secure_url"], "public_id": result["public_id"]}


# SEARCH AUTOCOMPLETE - already moved above


# PASSWORD CHANGE & RECOVERY
@api_router.put("/auth/cambiar-password")
async def change_password(data: ChangePassword, user=Depends(get_current_user)):
    if len(data.new_password) < 8:
        raise HTTPException(400, "La contrasena debe tener al menos 8 caracteres")
    u = await db.users.find_one({"id": user["user_id"]})
    if not u or not pwd_context.verify(data.current_password, u["password_hash"]):
        raise HTTPException(400, "Contrasena actual incorrecta")
    new_hash = pwd_context.hash(data.new_password)
    await db.users.update_one({"id": user["user_id"]}, {"$set": {"password_hash": new_hash}})
    return {"message": "Contrasena actualizada correctamente"}

@api_router.post("/auth/recuperar-password")
async def forgot_password(data: ForgotPassword, request: Request):
    token = secrets.token_urlsafe(32)
    expires = datetime.now(timezone.utc) + timedelta(hours=1)
    u = await db.users.find_one({"email": data.email})
    if u:
        await db.password_resets.insert_one({"email": data.email, "token": token, "expires_at": expires.isoformat(), "used": False})
        frontend_url = request.headers.get("origin", request.headers.get("referer", "https://lapopo.es")).rstrip("/")
        await send_recovery_email(data.email, token, frontend_url)
    return {"message": "Si ese email esta registrado, recibiras un enlace de recuperacion"}

@api_router.post("/auth/resetear-password")
async def reset_password(data: ResetPassword):
    if len(data.new_password) < 8:
        raise HTTPException(400, "La contrasena debe tener al menos 8 caracteres")
    reset = await db.password_resets.find_one({"token": data.token, "used": False})
    if not reset:
        raise HTTPException(400, "Enlace invalido o expirado")
    if datetime.fromisoformat(reset["expires_at"]) < datetime.now(timezone.utc):
        raise HTTPException(400, "El enlace ha expirado")
    u = await db.users.find_one({"email": reset["email"]})
    if not u:
        raise HTTPException(400, "Usuario no encontrado")
    new_hash = pwd_context.hash(data.new_password)
    await db.users.update_one({"id": u["id"]}, {"$set": {"password_hash": new_hash}})
    await db.password_resets.update_one({"token": data.token}, {"$set": {"used": True}})
    return {"message": "Contrasena restablecida correctamente"}


# BADGES
@api_router.get("/badges")
async def list_badges():
    return await db.badges.find({}, {"_id": 0}).to_list(200)

@api_router.get("/badges/usuario/{user_id}")
async def get_user_badges(user_id: str):
    ub = await db.user_badges.find({"user_id": user_id}, {"_id": 0}).to_list(100)
    badge_ids = [u["badge_id"] for u in ub]
    badges = await db.badges.find({"id": {"$in": badge_ids}}, {"_id": 0}).to_list(100) if badge_ids else []
    return badges

@api_router.post("/admin/badges")
async def admin_create_badge(data: BadgeCreate, user=Depends(require_admin)):
    doc = {"id": str(uuid.uuid4()), "name": data.name, "description": data.description, "emoji": data.emoji,
           "condition_type": data.condition_type, "condition_value": data.condition_value, "auto": data.auto,
           "created_at": datetime.now(timezone.utc).isoformat()}
    await db.badges.insert_one(doc)
    doc.pop("_id", None)
    return doc

@api_router.put("/admin/badges/{badge_id}")
async def admin_update_badge(badge_id: str, data: BadgeCreate, user=Depends(require_admin)):
    result = await db.badges.update_one({"id": badge_id}, {"$set": {
        "name": data.name, "description": data.description, "emoji": data.emoji,
        "condition_type": data.condition_type, "condition_value": data.condition_value, "auto": data.auto,
    }})
    if result.matched_count == 0:
        raise HTTPException(404, "Badge no encontrado")
    return {"message": "Badge actualizado"}

@api_router.delete("/admin/badges/{badge_id}")
async def admin_delete_badge(badge_id: str, user=Depends(require_admin)):
    await db.badges.delete_one({"id": badge_id})
    await db.user_badges.delete_many({"badge_id": badge_id})
    return {"message": "Badge eliminado"}

@api_router.post("/admin/badges/{badge_id}/asignar")
async def admin_assign_badge(badge_id: str, data: BadgeAssign, user=Depends(require_admin)):
    badge = await db.badges.find_one({"id": badge_id}, {"_id": 0})
    if not badge:
        raise HTTPException(404, "Badge no encontrado")
    existing = await db.user_badges.find_one({"user_id": data.user_id, "badge_id": badge_id})
    if existing:
        raise HTTPException(400, "El usuario ya tiene este badge")
    await db.user_badges.insert_one({"user_id": data.user_id, "badge_id": badge_id, "badge_name": badge["name"], "awarded_at": datetime.now(timezone.utc).isoformat()})
    return {"message": "Badge asignado"}

@api_router.post("/admin/badges/{badge_id}/retirar")
async def admin_remove_badge(badge_id: str, data: BadgeAssign, user=Depends(require_admin)):
    result = await db.user_badges.delete_one({"user_id": data.user_id, "badge_id": badge_id})
    if result.deleted_count == 0:
        raise HTTPException(404, "El usuario no tiene este badge")
    return {"message": "Badge retirado"}


# ADMIN RATINGS MANAGEMENT
@api_router.get("/admin/valoraciones")
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

@api_router.delete("/admin/valoraciones/{rating_id}")
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
    admin_id = str(uuid.uuid4())
    await db.users.insert_many([
        {"id": demo_id, "name": "Carlos López", "email": "carlos@lapopo.es", "password_hash": pwd_context.hash("demo123"), "is_admin": False, "rating_avg": 0, "rating_count": 0, "plan": "free", "created_at": datetime.now(timezone.utc).isoformat()},
        {"id": maria_id, "name": "María García", "email": "maria@lapopo.es", "password_hash": pwd_context.hash("demo123"), "is_admin": False, "rating_avg": 0, "rating_count": 0, "plan": "free", "created_at": datetime.now(timezone.utc).isoformat()},
        {"id": admin_id, "name": "Admin Lapopo", "email": "admin@lapopo.es", "password_hash": pwd_context.hash("admin123"), "is_admin": True, "rating_avg": 0, "rating_count": 0, "plan": "pro", "created_at": datetime.now(timezone.utc).isoformat()},
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
    await db.settings.insert_one({"key": "payments_enabled", "value": False})
    for b in DEFAULT_BADGES:
        b["id"] = str(uuid.uuid4())
        b["created_at"] = datetime.now(timezone.utc).isoformat()
    await db.badges.insert_many(DEFAULT_BADGES)
    logger.info(f"Seeded {len(seeds)} auctions, 3 users, settings, and {len(DEFAULT_BADGES)} badges")

@app.on_event("shutdown")
async def shutdown():
    client.close()
