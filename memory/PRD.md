# Lapopo - Plataforma de Subastas de Segunda Mano

## Problem Statement
Full-stack auction web application for Spain and the Canary Islands, similar to Wallapop but with auctions starting from 1 euro.

## Tech Stack
- **Frontend:** React, TailwindCSS, Shadcn UI
- **Backend:** FastAPI (Python) - Modular architecture with APIRouter
- **Database:** MongoDB
- **Auth:** JWT (bcrypt)
- **Payments:** Stripe (via emergentintegrations)
- **Image Storage:** Cloudinary
- **Email:** SendGrid

## Design
- Colors: #18b29c (primary), #ffb347 (accent), #f5f7fa (background)
- Font: Nunito (headings), system-ui

## Pages
- Home, Auth, Create Auction, Auction Detail, Profile, Pricing (/precios), Admin (/admin)

## Backend Architecture (Modular)
```
/app/backend/
  server.py          # Entry point (~60 lines) - imports routers, CORS, startup
  database.py        # MongoDB connection (db export)
  models.py          # Pydantic models + constants (PLANS, CATEGORIES, etc.)
  auth.py            # JWT helpers (create_token, verify_token, get_current_user, require_admin)
  helpers.py         # Business logic (notifications, badges, auto-bids, SendGrid, etc.)
  seed.py            # Initial data seeding (3 users, 11 auctions, 7 badges)
  routes/
    auth.py          # register, login, password change/recovery
    auctions.py      # list, create, bid, buy now, cancel, auto-bid, autocomplete
    users.py         # profile, update
    social.py        # notifications, messages/chat, favorites, contact
    ratings.py       # create, list by user/auction
    payments.py      # plans, subscriptions, featured, Stripe webhook
    disputes.py      # create, list, messages
    admin.py         # stats, users, auctions, disputes, badges, ratings, config
    upload.py        # Cloudinary upload (base64 + multipart)
    badges.py        # list all, user badges
```

## ALL Implemented Features
1. User registration/login (JWT)
2. Auction CRUD with image upload (Cloudinary)
3. Manual bidding (min +0.50 euro)
4. Real-time countdown
5. Auction filtering (category, location, canarias, search, price, sort)
6. Buy It Now
7. Auction cancellation
8. Seller-Winner contact system
9. Notifications (outbid, won, cancelled, messages, disputes)
10. Private chat with image attachments
11. Favorites/Watchlist
12. Automatic bidding
13. Rating system (1-5 stars + comment)
14. Admin panel (stats, users, auctions management)
15. Monetization: Subscription plans (free/vendedor 2.99/pro 6.99)
16. Monetization: Featured listings (destacada 0.49/home 0.99/urgente 0.29)
17. Monetization: Admin payment toggle (on/off globally)
18. Monetization: Stripe integration (checkout sessions)
19. Monetization: Plan limits (free: 5/month, paid: unlimited)
20. Monetization: Badges (Destacada, Home, Urgente, Vendedor Verificado)
21. Dispute system (open, review, resolve, close)
22. Dispute notifications & messaging with images
23. Search autocomplete with dropdown
24. Gamified reputation badges (7 default + custom)
25. Admin badge management (CRUD + assign/remove)
26. Admin rating management (list/filter/delete)
27. Password change (authenticated)
28. Password recovery via SendGrid email

## Key API Endpoints
### Auth
- POST /api/auth/register, POST /api/auth/login
- PUT /api/auth/cambiar-password
- POST /api/auth/recuperar-password, POST /api/auth/resetear-password
### Auctions
- GET/POST /api/subastas, GET /api/subastas/{id}
- GET /api/subastas/autocomplete?q=
- POST /api/subastas/{id}/pujar, /comprar-ya, /cancelar, /auto-pujar
### Social
- GET/POST /api/notificaciones/*, POST/GET /api/mensajes/*
- POST/GET /api/favoritos/*, GET /api/contacto/{id}
- GET /api/chat/conversaciones
### Ratings
- POST /api/valoraciones, GET /api/valoraciones/usuario/{id}, GET /api/valoraciones/subasta/{id}
### Badges
- GET /api/badges, GET /api/badges/usuario/{user_id}
### Upload
- POST /api/upload (multipart), POST /api/upload/base64
### Plans & Payments
- GET /api/planes, GET /api/suscripciones/mi-plan
- POST /api/suscripciones/crear-sesion, POST /api/suscripciones/cancelar
- POST /api/destacados/crear-sesion, POST /api/destacados/activar-gratis
- GET /api/pagos/estado/{session_id}, POST /api/webhook/stripe
### Disputes
- POST /api/disputas, GET /api/disputas/mis-disputas, GET /api/disputas/{id}
- POST /api/disputas/{id}/mensaje
### Admin
- GET/PUT /api/admin/config, GET /api/admin/stats
- GET /api/admin/usuarios, DELETE /api/admin/usuarios/{id}
- GET /api/admin/subastas, DELETE /api/admin/subastas/{id}
- GET /api/admin/disputas, PUT /api/admin/disputas/{id}/estado
- POST/PUT/DELETE /api/admin/badges, POST /api/admin/badges/{id}/asignar|retirar
- GET /api/admin/valoraciones, DELETE /api/admin/valoraciones/{id}

## DB Collections
- users, auctions, notifications, messages, favorites, auto_bids, ratings
- settings (payments_enabled toggle)
- featured_listings (auction_id, type, active)
- disputes (auction_id, reporter, reported, reason, status, messages)
- payment_transactions (session_id, type, status)
- badges (name, emoji, condition_type, condition_value, auto)
- user_badges (user_id, badge_id, badge_name, awarded_at)
- password_resets (email, token, expires_at, used)

## Credentials
- Admin: admin@lapopo.es / admin123
- Demo: carlos@lapopo.es / demo123, maria@lapopo.es / demo123

## Completed
- [x] MVP (auth, CRUD, bidding, countdown, filters)
- [x] Bug fixes + Buy It Now + Cancellation + Contact
- [x] Notifications, Messaging, Favorites, Auto-bidding
- [x] Rating system + Admin panel
- [x] Monetization system (plans, Stripe, featured, badges)
- [x] Dispute system (open, review, resolve, notifications)
- [x] 8-feature mega release (chat, Cloudinary, badges, autocomplete, password mgmt, admin enhancements)
- [x] Backend modularization (server.py -> 10 route modules + helpers)

## Future/Backlog
- P2: Push notifications (web)
- P3: Auction categories management from admin
- P3: WebSocket real-time updates for bids/chat
