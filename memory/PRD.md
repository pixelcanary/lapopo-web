# Lapopo - Plataforma de Subastas de Segunda Mano

## Problem Statement
Full-stack auction web application for Spain and the Canary Islands, similar to Wallapop but with auctions starting from 1 euro.

## Tech Stack
- **Frontend:** React, TailwindCSS, Shadcn UI
- **Backend:** FastAPI (Python)
- **Database:** MongoDB
- **Auth:** JWT
- **Payments:** Stripe (via emergentintegrations)

## Design
- Colors: #18b29c (primary), #ffb347 (accent), #f5f7fa (background)
- Font: Nunito (headings), system-ui

## Pages
- Home, Auth, Create Auction, Auction Detail, Profile, Pricing (/precios), Admin (/admin)

## ALL Implemented Features
1. User registration/login (JWT)
2. Auction CRUD with image upload
3. Manual bidding (min +0.50 euro)
4. Real-time countdown
5. Auction filtering (category, location, canarias, search, price, sort)
6. Buy It Now
7. Auction cancellation
8. Seller-Winner contact system
9. Notifications (outbid, won, cancelled, messages, disputes)
10. Basic messaging
11. Favorites/Watchlist
12. Automatic bidding
13. Rating system (1-5 stars + comment)
14. Admin panel (stats, users, auctions management)
15. **Monetization: Subscription plans** (free/vendedor 2.99/pro 6.99)
16. **Monetization: Featured listings** (destacada 0.49/home 0.99/urgente 0.29)
17. **Monetization: Admin payment toggle** (on/off globally)
18. **Monetization: Stripe integration** (checkout sessions for subscriptions + featured)
19. **Monetization: Plan limits** (free: 5 auctions/month, paid: unlimited)
20. **Monetization: Badges** (Destacada, Home, Urgente, Vendedor Verificado)
21. **Dispute system** (open, review, resolve, close)
22. **Dispute notifications** (status change alerts to both parties)
23. **Dispute messaging** (buyer/seller/admin can add messages)

## Key API Endpoints
### Auth
- POST /api/auth/register, POST /api/auth/login
### Auctions
- GET/POST /api/subastas, GET /api/subastas/{id}
- POST /api/subastas/{id}/pujar, /comprar-ya, /cancelar, /auto-pujar
### Social
- GET/POST /api/notificaciones/*, POST/GET /api/mensajes/*
- POST/GET /api/favoritos/*, GET /api/contacto/{id}
### Ratings
- POST /api/valoraciones, GET /api/valoraciones/usuario/{id}, GET /api/valoraciones/subasta/{id}
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

## DB Collections
- users, auctions, notifications, messages, favorites, auto_bids, ratings
- settings (payments_enabled toggle)
- featured_listings (auction_id, type, active)
- disputes (auction_id, reporter, reported, reason, status, messages)
- payment_transactions (session_id, type, status)

## Credentials
- Admin: admin@lapopo.es / admin123
- Demo: carlos@lapopo.es / demo123, maria@lapopo.es / demo123

## Completed - March 2026
- [x] MVP (auth, CRUD, bidding, countdown, filters)
- [x] Bug fixes + Buy It Now + Cancellation + Contact
- [x] Notifications, Messaging, Favorites, Auto-bidding
- [x] Rating system + Admin panel
- [x] Monetization system (plans, Stripe, featured, badges)
- [x] Dispute system (open, review, resolve, notifications)

## Future/Backlog
- P1: Image upload to cloud storage
- P2: Push notifications (web)
- P2: Search autocomplete
- P3: Auction categories management from admin
- P3: Backend route modularization
