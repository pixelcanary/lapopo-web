from fastapi import APIRouter, HTTPException, Depends, Request
from database import db
from models import CheckoutRequest, PLANS, FEATURED_OPTIONS, DISPUTE_REASONS
from auth import get_current_user
from helpers import get_payments_enabled, get_user_plan, count_user_auctions_this_month
from datetime import datetime, timezone
import stripe
import uuid
import os
import logging

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api")

stripe.api_key = os.environ.get("STRIPE_API_KEY")


@router.get("/planes")
async def get_plans():
    payments_on = await get_payments_enabled()
    return {"plans": PLANS, "featured_options": FEATURED_OPTIONS, "payments_enabled": payments_on, "dispute_reasons": DISPUTE_REASONS}


@router.get("/suscripciones/mi-plan")
async def my_plan(user=Depends(get_current_user)):
    u = await db.users.find_one({"id": user["user_id"]}, {"_id": 0, "plan": 1})
    plan = u.get("plan", "free") if u else "free"
    payments_on = await get_payments_enabled()
    auc_count = await count_user_auctions_this_month(user["user_id"])
    plan_info = PLANS.get(plan, PLANS["free"])
    return {"plan": plan, "plan_info": plan_info, "auctions_this_month": auc_count, "payments_enabled": payments_on}


@router.post("/suscripciones/crear-sesion")
async def create_subscription_session(data: CheckoutRequest, request: Request, user=Depends(get_current_user)):
    if data.plan not in ["vendedor", "pro"]:
        raise HTTPException(400, "Plan no valido")
    plan_info = PLANS[data.plan]
    success_url = f"{data.origin_url}/precios?session_id={{CHECKOUT_SESSION_ID}}"
    cancel_url = f"{data.origin_url}/precios"
    session = stripe.checkout.Session.create(
        payment_method_types=["card"],
        line_items=[{
            "price_data": {
                "currency": "eur",
                "product_data": {"name": f"Plan {plan_info['name']}"},
                "unit_amount": int(plan_info["price"] * 100),
            },
            "quantity": 1,
        }],
        mode="payment",
        success_url=success_url,
        cancel_url=cancel_url,
        metadata={"user_id": user["user_id"], "type": "subscription", "plan": data.plan},
    )
    await db.payment_transactions.insert_one({
        "id": str(uuid.uuid4()), "session_id": session.id, "user_id": user["user_id"],
        "type": "subscription", "plan": data.plan, "amount": plan_info["price"], "currency": "eur",
        "payment_status": "pending", "created_at": datetime.now(timezone.utc).isoformat()
    })
    return {"url": session.url, "session_id": session.id}


@router.post("/suscripciones/cancelar")
async def cancel_subscription(user=Depends(get_current_user)):
    await db.users.update_one({"id": user["user_id"]}, {"$set": {"plan": "free"}})
    return {"message": "Plan cancelado. Ahora tienes el plan Gratis."}


@router.post("/destacados/crear-sesion")
async def create_featured_session(data: CheckoutRequest, request: Request, user=Depends(get_current_user)):
    if data.featured_type not in FEATURED_OPTIONS:
        raise HTTPException(400, "Tipo de destacado no valido")
    if not data.auction_id:
        raise HTTPException(400, "auction_id requerido")
    auction = await db.auctions.find_one({"id": data.auction_id, "seller_id": user["user_id"]}, {"_id": 0})
    if not auction:
        raise HTTPException(404, "Subasta no encontrada o no eres el propietario")
    feat_info = FEATURED_OPTIONS[data.featured_type]
    success_url = f"{data.origin_url}/subasta/{data.auction_id}?session_id={{CHECKOUT_SESSION_ID}}"
    cancel_url = f"{data.origin_url}/subasta/{data.auction_id}"
    session = stripe.checkout.Session.create(
        payment_method_types=["card"],
        line_items=[{
            "price_data": {
                "currency": "eur",
                "product_data": {"name": feat_info["name"]},
                "unit_amount": int(feat_info["price"] * 100),
            },
            "quantity": 1,
        }],
        mode="payment",
        success_url=success_url,
        cancel_url=cancel_url,
        metadata={"user_id": user["user_id"], "type": "featured", "featured_type": data.featured_type, "auction_id": data.auction_id},
    )
    await db.payment_transactions.insert_one({
        "id": str(uuid.uuid4()), "session_id": session.id, "user_id": user["user_id"],
        "type": "featured", "featured_type": data.featured_type, "auction_id": data.auction_id,
        "amount": feat_info["price"], "currency": "eur",
        "payment_status": "pending", "created_at": datetime.now(timezone.utc).isoformat()
    })
    return {"url": session.url, "session_id": session.id}


@router.post("/destacados/activar-gratis")
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


@router.get("/pagos/estado/{session_id}")
async def check_payment_status(session_id: str, request: Request, user=Depends(get_current_user)):
    tx = await db.payment_transactions.find_one({"session_id": session_id}, {"_id": 0})
    if not tx:
        raise HTTPException(404, "Transaccion no encontrada")
    if tx.get("payment_status") == "paid":
        return {"status": "paid", "payment_status": "paid", "type": tx.get("type"), "plan": tx.get("plan")}
    try:
        session = stripe.checkout.Session.retrieve(session_id)
        if session.payment_status == "paid":
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
        return {"status": session.status, "payment_status": session.payment_status, "type": tx.get("type"), "plan": tx.get("plan")}
    except Exception as e:
        logger.error(f"Stripe status check error: {e}")
        return {"status": "unknown", "payment_status": tx.get("payment_status", "pending"), "type": tx.get("type"), "plan": tx.get("plan")}


@router.post("/webhook/stripe")
async def stripe_webhook(request: Request):
    body = await request.body()
    try:
        payload = body.decode("utf-8")
        import json
        event_data = json.loads(payload)
        if event_data.get("type") == "checkout.session.completed":
            session = event_data["data"]["object"]
            session_id = session["id"]
            payment_status = session.get("payment_status", "")
            if payment_status == "paid":
                tx = await db.payment_transactions.find_one({"session_id": session_id, "payment_status": {"$ne": "paid"}})
                if tx:
                    await db.payment_transactions.update_one({"session_id": session_id}, {"$set": {"payment_status": "paid"}})
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
