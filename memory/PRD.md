# Lapopo - Plataforma de Subastas de Segunda Mano

## Problem Statement
Build a full-stack auction web application called "Lapopo", a second-hand auction platform for Spain and the Canary Islands, similar to Wallapop but with auctions starting from 1 euro.

## Tech Stack
- **Frontend:** React, TailwindCSS, Shadcn UI
- **Backend:** FastAPI (Python)
- **Database:** MongoDB
- **Auth:** JWT

## Design
- Colors: #18b29c (primary), #ffb347 (accent), #f5f7fa (background)
- Font: Nunito (headings), system-ui
- Clean/modern style with rounded cards

## Pages
- Home (hero, search, filters, auction grid, Canarias section, FAQ, footer)
- Auth (login/register)
- Create Auction (3-step wizard)
- Auction Detail (images, bidding, buy now, auto-bid, cancel, contact, messages, ratings)
- Profile (tabs: subastas, pujas, ganadas, favoritos, valoraciones, avisos)
- Admin Panel (/admin - protected, admin-only)

## Core Features - ALL IMPLEMENTED
1. User registration/login (JWT)
2. Auction CRUD with image upload (base64 compressed)
3. Manual bidding (min +0.50 euro)
4. Real-time countdown
5. Auction filtering (category, location, canarias, search, price, sort)
6. Buy It Now (optional instant purchase price)
7. Auction cancellation (with bid/time rules)
8. Seller-Winner contact system
9. Notifications (outbid, won, cancelled, messages)
10. Basic messaging between seller/winner
11. Favorites/Watchlist
12. Automatic bidding system
13. **Rating system** (1-5 stars + comment, buyer/seller mutual, shown on cards/detail/profile)
14. **Admin panel** (stats, user management, auction management, protected route)

## Key API Endpoints
- `/api/auth/register`, `/api/auth/login`
- `/api/subastas` (GET, POST)
- `/api/subastas/{id}` (GET)
- `/api/subastas/{id}/pujar` (POST)
- `/api/subastas/{id}/comprar-ya` (POST)
- `/api/subastas/{id}/cancelar` (POST)
- `/api/subastas/{id}/auto-pujar` (POST)
- `/api/notificaciones` (GET), `/api/notificaciones/{id}/leer` (PUT), `/api/notificaciones/leer-todas` (PUT)
- `/api/mensajes` (POST), `/api/mensajes/{auction_id}` (GET)
- `/api/favoritos/{auction_id}` (POST toggle), `/api/favoritos` (GET)
- `/api/contacto/{auction_id}` (GET)
- `/api/usuarios/{id}` (GET, PUT)
- `/api/valoraciones` (POST), `/api/valoraciones/usuario/{id}` (GET), `/api/valoraciones/subasta/{id}` (GET)
- `/api/admin/stats` (GET), `/api/admin/usuarios` (GET), `/api/admin/subastas` (GET)
- `/api/admin/usuarios/{id}` (DELETE), `/api/admin/subastas/{id}` (DELETE)

## DB Collections
- `users`: id, name, email, password_hash, is_admin, rating_avg, rating_count, created_at
- `auctions`: id, title, description, images, starting_price, current_price, buy_now_price, duration, end_time, category, location, delivery_type, seller_id, seller_name, bids[], bid_count, status, winner_id, winner_name, created_at
- `notifications`: id, user_id, type, auction_id, auction_title, message, read, created_at
- `messages`: id, auction_id, sender_id, sender_name, receiver_id, content, created_at
- `favorites`: user_id, auction_id, created_at
- `auto_bids`: id, auction_id, user_id, user_name, max_amount, active, created_at
- `ratings`: id, auction_id, rater_id, rater_name, rated_id, rating (1-5), comment, created_at

## Credentials
- Admin: admin@lapopo.es / admin123 (is_admin=true)
- Demo: carlos@lapopo.es / demo123
- Demo: maria@lapopo.es / demo123

## Testing
- Iteration 1: Initial MVP - passed
- Iteration 2: All features (33/33 backend, 14/14 frontend)
- Iteration 3: Ratings + Admin (22/22 backend, 16/16 frontend)
- Test files: /app/backend/tests/test_lapopo_api.py, /app/backend/tests/test_admin_ratings.py

## Completed
- [x] MVP (auth, CRUD, bidding, countdown, filters) - March 2026
- [x] Bug fixes (price input, footer 2026, seed data) - March 2026
- [x] Buy It Now, Cancellation, Contact system - March 2026
- [x] Notifications, Messaging, Favorites, Auto-bidding - March 2026
- [x] Rating system (1-5 stars, comments, profile display) - March 2026
- [x] Admin panel (stats, user/auction management) - March 2026

## Future/Backlog
- P1: Image upload to cloud storage (currently base64)
- P2: Payment integration (Stripe)
- P2: Push notifications (web)
- P2: Search autocomplete
- P3: Auction categories management from admin
- P3: Backend route modularization
