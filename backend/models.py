from pydantic import BaseModel
from typing import List, Optional
from datetime import timedelta

# Pydantic Models
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


# Constants
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

DEFAULT_BADGES = [
    {"name": "Primera venta", "description": "Completaste tu primera venta", "emoji": "🏷️", "condition_type": "sales", "condition_value": 1, "auto": True},
    {"name": "5 ventas", "description": "5 subastas vendidas", "emoji": "🎯", "condition_type": "sales", "condition_value": 5, "auto": True},
    {"name": "10 ventas", "description": "10 subastas vendidas", "emoji": "🏆", "condition_type": "sales", "condition_value": 10, "auto": True},
    {"name": "50 ventas", "description": "50 subastas vendidas", "emoji": "💎", "condition_type": "sales", "condition_value": 50, "auto": True},
    {"name": "100% positivas", "description": "Todas tus valoraciones son positivas (min 3)", "emoji": "⭐", "condition_type": "positive_ratings", "condition_value": 100, "auto": True},
    {"name": "Comprador frecuente", "description": "Has ganado 5 subastas", "emoji": "🛒", "condition_type": "purchases", "condition_value": 5, "auto": True},
    {"name": "Canario", "description": "Has vendido en las Islas Canarias", "emoji": "🌴", "condition_type": "canarias_sales", "condition_value": 1, "auto": True},
]
