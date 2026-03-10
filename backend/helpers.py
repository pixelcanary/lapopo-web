from database import db
from models import CANARY_ISLANDS, PLANS
from auth import pwd_context
from datetime import datetime, timezone
from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail
import uuid
import os
import logging

logger = logging.getLogger(__name__)


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
