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

class UserUpdate(BaseModel):
    name: Optional[str] = None


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
    await db.auctions.update_many(
        {"status": "active", "end_time": {"$lte": now}},
        {"$set": {"status": "finished"}}
    )


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
        raise HTTPException(400, "Precio mínimo: 1 euro")
    if data.duration not in DURATION_MAP:
        raise HTTPException(400, "Duración no válida")
    if len(data.images) < 1:
        raise HTTPException(400, "Mínimo 1 foto")
    if len(data.images) > 6:
        raise HTTPException(400, "Máximo 6 fotos")

    now = datetime.now(timezone.utc)
    aid = str(uuid.uuid4())
    doc = {
        "id": aid,
        "title": data.title,
        "description": data.description,
        "images": data.images,
        "starting_price": data.starting_price,
        "current_price": data.starting_price,
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
        raise HTTPException(400, f"Puja mínima: {min_bid:.2f} euros")

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
    updated = await db.auctions.find_one({"id": auction_id}, {"_id": 0})
    return updated


# USER ENDPOINTS
@api_router.get("/usuarios/{user_id}")
async def get_user_profile(user_id: str):
    user = await db.users.find_one({"id": user_id}, {"_id": 0, "password_hash": 0})
    if not user:
        raise HTTPException(404, "Usuario no encontrado")
    auctions = await db.auctions.find({"seller_id": user_id}, {"_id": 0}).to_list(100)
    bids = await db.auctions.find({"bids.user_id": user_id, "status": "active"}, {"_id": 0}).to_list(100)
    return {"user": user, "auctions": auctions, "active_bids": bids}

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
        {"id": str(uuid.uuid4()), "title": "Cámara Canon EOS 500D - Perfecta", "description": "Cámara réflex Canon EOS 500D en perfecto estado. Incluye objetivo 18-55mm, cargador y bolsa. Ideal para aprender fotografía.", "images": ["https://images.unsplash.com/photo-1588768904397-cb062c91ba55?auto=format&fit=crop&q=80&w=600"], "starting_price": 45.0, "current_price": 67.50, "duration": "3d", "end_time": (now + timedelta(days=2, hours=5)).isoformat(), "category": "Electrónica", "location": "Madrid", "delivery_type": "shipping", "seller_id": demo_id, "seller_name": "Carlos López", "bids": [{"id": str(uuid.uuid4()), "user_id": maria_id, "user_name": "María García", "amount": 50.0, "timestamp": (now - timedelta(hours=5)).isoformat()}, {"id": str(uuid.uuid4()), "user_id": maria_id, "user_name": "María García", "amount": 67.50, "timestamp": (now - timedelta(hours=2)).isoformat()}], "bid_count": 2, "status": "active", "created_at": (now - timedelta(days=1)).isoformat()},
        {"id": str(uuid.uuid4()), "title": "iPhone 13 - 128GB Azul", "description": "iPhone 13 en color azul, 128GB. Pantalla y batería al 92%. Sin arañazos. Incluye caja original y cargador.", "images": ["https://images.unsplash.com/photo-1592750475338-74b7b21085ab?auto=format&fit=crop&q=80&w=600"], "starting_price": 200.0, "current_price": 245.0, "duration": "7d", "end_time": (now + timedelta(days=5, hours=12)).isoformat(), "category": "Electrónica", "location": "Barcelona", "delivery_type": "both", "seller_id": maria_id, "seller_name": "María García", "bids": [{"id": str(uuid.uuid4()), "user_id": demo_id, "user_name": "Carlos López", "amount": 220.0, "timestamp": (now - timedelta(hours=10)).isoformat()}, {"id": str(uuid.uuid4()), "user_id": demo_id, "user_name": "Carlos López", "amount": 245.0, "timestamp": (now - timedelta(hours=3)).isoformat()}], "bid_count": 2, "status": "active", "created_at": (now - timedelta(days=2)).isoformat()},
        {"id": str(uuid.uuid4()), "title": "Bicicleta de montaña Scott Scale", "description": "Bicicleta MTB Scott Scale 970 talla L. Cuadro de aluminio, frenos de disco hidráulicos. Revisada recientemente.", "images": ["https://images.unsplash.com/photo-1532298229144-0ec0c57515c7?auto=format&fit=crop&q=80&w=600"], "starting_price": 150.0, "current_price": 185.0, "duration": "3d", "end_time": (now + timedelta(hours=18)).isoformat(), "category": "Deporte", "location": "Valencia", "delivery_type": "pickup", "seller_id": demo_id, "seller_name": "Carlos López", "bids": [{"id": str(uuid.uuid4()), "user_id": maria_id, "user_name": "María García", "amount": 170.0, "timestamp": (now - timedelta(hours=8)).isoformat()}, {"id": str(uuid.uuid4()), "user_id": maria_id, "user_name": "María García", "amount": 185.0, "timestamp": (now - timedelta(hours=1)).isoformat()}], "bid_count": 2, "status": "active", "created_at": (now - timedelta(days=1, hours=6)).isoformat()},
        {"id": str(uuid.uuid4()), "title": "Tabla de Surf 6'2 - Perfecta para Canarias", "description": "Tabla de surf shortboard 6'2. Ideal para las olas de Canarias. Incluye quillas y funda. Muy poco uso.", "images": ["https://images.unsplash.com/photo-1675008814982-a18b8efb7e7e?auto=format&fit=crop&q=80&w=600"], "starting_price": 80.0, "current_price": 95.0, "duration": "7d", "end_time": (now + timedelta(days=4)).isoformat(), "category": "Deporte", "location": "Tenerife", "delivery_type": "pickup", "seller_id": maria_id, "seller_name": "María García", "bids": [{"id": str(uuid.uuid4()), "user_id": demo_id, "user_name": "Carlos López", "amount": 95.0, "timestamp": (now - timedelta(hours=6)).isoformat()}], "bid_count": 1, "status": "active", "created_at": (now - timedelta(days=3)).isoformat()},
        {"id": str(uuid.uuid4()), "title": "PlayStation 5 + 2 Mandos", "description": "PS5 con lector de discos. Incluye 2 mandos DualSense y 3 juegos físicos. Funciona perfectamente.", "images": ["https://images.unsplash.com/photo-1606144042614-b2417e99c4e3?auto=format&fit=crop&q=80&w=600"], "starting_price": 250.0, "current_price": 310.0, "duration": "3d", "end_time": (now + timedelta(days=1, hours=8)).isoformat(), "category": "Electrónica", "location": "Gran Canaria", "delivery_type": "both", "seller_id": demo_id, "seller_name": "Carlos López", "bids": [{"id": str(uuid.uuid4()), "user_id": maria_id, "user_name": "María García", "amount": 280.0, "timestamp": (now - timedelta(hours=12)).isoformat()}, {"id": str(uuid.uuid4()), "user_id": maria_id, "user_name": "María García", "amount": 310.0, "timestamp": (now - timedelta(hours=4)).isoformat()}], "bid_count": 2, "status": "active", "created_at": (now - timedelta(days=2)).isoformat()},
        {"id": str(uuid.uuid4()), "title": "Mesa de comedor vintage roble", "description": "Preciosa mesa de comedor estilo vintage en madera de roble macizo. 160x90cm. Capacidad 6-8 personas.", "images": ["https://images.unsplash.com/photo-1592078615290-033ee584e267?auto=format&fit=crop&q=80&w=600"], "starting_price": 120.0, "current_price": 120.0, "duration": "7d", "end_time": (now + timedelta(days=6)).isoformat(), "category": "Hogar", "location": "Sevilla", "delivery_type": "pickup", "seller_id": maria_id, "seller_name": "María García", "bids": [], "bid_count": 0, "status": "active", "created_at": (now - timedelta(days=1)).isoformat()},
        {"id": str(uuid.uuid4()), "title": "MacBook Pro 2021 M1 Pro", "description": "MacBook Pro 14 pulgadas con chip M1 Pro, 16GB RAM, 512GB SSD. Ciclos de batería: 120. En perfecto estado.", "images": ["https://images.unsplash.com/photo-1517336714731-489689fd1ca8?auto=format&fit=crop&q=80&w=600"], "starting_price": 800.0, "current_price": 875.0, "duration": "7d", "end_time": (now + timedelta(days=3, hours=16)).isoformat(), "category": "Electrónica", "location": "Lanzarote", "delivery_type": "shipping", "seller_id": demo_id, "seller_name": "Carlos López", "bids": [{"id": str(uuid.uuid4()), "user_id": maria_id, "user_name": "María García", "amount": 850.0, "timestamp": (now - timedelta(hours=20)).isoformat()}, {"id": str(uuid.uuid4()), "user_id": maria_id, "user_name": "María García", "amount": 875.0, "timestamp": (now - timedelta(hours=8)).isoformat()}], "bid_count": 2, "status": "active", "created_at": (now - timedelta(days=4)).isoformat()},
        {"id": str(uuid.uuid4()), "title": "Vestido vintage años 70", "description": "Vestido original de los años 70 en perfecto estado. Talla S/M. Estampado floral único. Pieza de coleccionista.", "images": ["https://images.unsplash.com/photo-1523381210434-271e8be1f52b?auto=format&fit=crop&q=80&w=600"], "starting_price": 15.0, "current_price": 22.50, "duration": "24h", "end_time": (now + timedelta(hours=6)).isoformat(), "category": "Moda", "location": "Fuerteventura", "delivery_type": "both", "seller_id": maria_id, "seller_name": "María García", "bids": [{"id": str(uuid.uuid4()), "user_id": demo_id, "user_name": "Carlos López", "amount": 18.0, "timestamp": (now - timedelta(hours=15)).isoformat()}, {"id": str(uuid.uuid4()), "user_id": demo_id, "user_name": "Carlos López", "amount": 22.50, "timestamp": (now - timedelta(hours=7)).isoformat()}], "bid_count": 2, "status": "active", "created_at": (now - timedelta(hours=18)).isoformat()},
        {"id": str(uuid.uuid4()), "title": "Colección 50 vinilos rock clásico", "description": "Colección de 50 vinilos de rock clásico. Beatles, Pink Floyd, Led Zeppelin, Queen y más. Estado general muy bueno.", "images": ["https://images.unsplash.com/photo-1563552744114-78ff178ac8de?auto=format&fit=crop&q=80&w=600"], "starting_price": 1.0, "current_price": 35.0, "duration": "3d", "end_time": (now + timedelta(days=1, hours=3)).isoformat(), "category": "Otros", "location": "La Palma", "delivery_type": "pickup", "seller_id": demo_id, "seller_name": "Carlos López", "bids": [{"id": str(uuid.uuid4()), "user_id": maria_id, "user_name": "María García", "amount": 15.0, "timestamp": (now - timedelta(hours=30)).isoformat()}, {"id": str(uuid.uuid4()), "user_id": maria_id, "user_name": "María García", "amount": 25.0, "timestamp": (now - timedelta(hours=15)).isoformat()}, {"id": str(uuid.uuid4()), "user_id": maria_id, "user_name": "María García", "amount": 35.0, "timestamp": (now - timedelta(hours=5)).isoformat()}], "bid_count": 3, "status": "active", "created_at": (now - timedelta(days=2)).isoformat()},
        {"id": str(uuid.uuid4()), "title": "Sillón Eames réplica - Como nuevo", "description": "Réplica del famoso sillón Eames Lounge Chair. Piel sintética negra, estructura de nogal. Comprado hace 6 meses.", "images": ["https://images.unsplash.com/photo-1567538096630-e0c55bd6374c?auto=format&fit=crop&q=80&w=600"], "starting_price": 1.0, "current_price": 55.0, "duration": "7d", "end_time": (now + timedelta(days=5, hours=20)).isoformat(), "category": "Hogar", "location": "Málaga", "delivery_type": "pickup", "seller_id": maria_id, "seller_name": "María García", "bids": [{"id": str(uuid.uuid4()), "user_id": demo_id, "user_name": "Carlos López", "amount": 30.0, "timestamp": (now - timedelta(hours=40)).isoformat()}, {"id": str(uuid.uuid4()), "user_id": demo_id, "user_name": "Carlos López", "amount": 55.0, "timestamp": (now - timedelta(hours=10)).isoformat()}], "bid_count": 2, "status": "active", "created_at": (now - timedelta(days=2)).isoformat()},
        {"id": str(uuid.uuid4()), "title": "Patinete eléctrico Xiaomi Pro 2", "description": "Patinete eléctrico Xiaomi Mi Electric Scooter Pro 2. 45km de autonomía, velocidad máx 25km/h.", "images": ["https://images.unsplash.com/photo-1558618666-fcd25c85f82e?auto=format&fit=crop&q=80&w=600"], "starting_price": 1.0, "current_price": 1.0, "duration": "24h", "end_time": (now + timedelta(hours=20)).isoformat(), "category": "Motor", "location": "Tenerife", "delivery_type": "pickup", "seller_id": demo_id, "seller_name": "Carlos López", "bids": [], "bid_count": 0, "status": "active", "created_at": (now - timedelta(hours=4)).isoformat()},
        {"id": str(uuid.uuid4()), "title": "Lote libros ciencia ficción", "description": "Lote de 20 libros de ciencia ficción. Asimov, Clarke, Philip K. Dick. Algunos primeras ediciones.", "images": ["https://images.unsplash.com/photo-1495446815901-a7297e633e8d?auto=format&fit=crop&q=80&w=600"], "starting_price": 5.0, "current_price": 12.50, "duration": "3d", "end_time": (now + timedelta(hours=10)).isoformat(), "category": "Libros", "location": "Gran Canaria", "delivery_type": "both", "seller_id": maria_id, "seller_name": "María García", "bids": [{"id": str(uuid.uuid4()), "user_id": demo_id, "user_name": "Carlos López", "amount": 8.0, "timestamp": (now - timedelta(hours=20)).isoformat()}, {"id": str(uuid.uuid4()), "user_id": demo_id, "user_name": "Carlos López", "amount": 12.50, "timestamp": (now - timedelta(hours=5)).isoformat()}], "bid_count": 2, "status": "active", "created_at": (now - timedelta(days=2, hours=14)).isoformat()},
    ]
    await db.auctions.insert_many(seeds)
    logger.info(f"Seeded {len(seeds)} auctions and 2 demo users")

@app.on_event("shutdown")
async def shutdown():
    client.close()
