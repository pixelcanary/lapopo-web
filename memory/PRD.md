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
- Auction Detail (images, bidding, buy now, auto-bid, cancel, contact, messages)
- Profile (tabs: subastas, pujas, ganadas, favoritos, avisos)

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

## Key API Endpoints
- `/api/auth/register`, `/api/auth/login`
- `/api/subastas` (GET, POST)
- `/api/subastas/{id}` (GET)
- `/api/subastas/{id}/pujar` (POST)
- `/api/subastas/{id}/comprar-ya` (POST)
- `/api/subastas/{id}/cancelar` (POST)
- `/api/subastas/{id}/auto-pujar` (POST)
- `/api/notificaciones` (GET)
- `/api/notificaciones/{id}/leer` (PUT)
- `/api/notificaciones/leer-todas` (PUT)
- `/api/mensajes` (POST), `/api/mensajes/{auction_id}` (GET)
- `/api/favoritos/{auction_id}` (POST toggle), `/api/favoritos` (GET)
- `/api/contacto/{auction_id}` (GET)
- `/api/usuarios/{id}` (GET, PUT)
- `/api/categorias`, `/api/ubicaciones`

## DB Collections
- `users`: id, name, email, password_hash, created_at
- `auctions`: id, title, description, images, starting_price, current_price, buy_now_price, duration, end_time, category, location, delivery_type, seller_id, seller_name, bids[], bid_count, status, winner_id, winner_name, created_at
- `notifications`: id, user_id, type, auction_id, auction_title, message, read, created_at
- `messages`: id, auction_id, sender_id, sender_name, receiver_id, content, created_at
- `favorites`: user_id, auction_id, created_at
- `auto_bids`: id, auction_id, user_id, user_name, max_amount, active, created_at

## Test Credentials
- carlos@lapopo.es / demo123 (Carlos Lopez)
- maria@lapopo.es / demo123 (Maria Garcia)

## Testing
- Backend: 33/33 tests passing (pytest at /app/backend/tests/test_lapopo_api.py)
- Frontend: 14/14 features verified via E2E testing
- Test report: /app/test_reports/iteration_2.json

## Completed - March 2026
- [x] MVP (auth, CRUD, bidding, countdown, filters)
- [x] Bug fixes (price input, footer 2026, seed data cleanup)
- [x] Buy It Now feature
- [x] Auction cancellation with rules
- [x] Seller-Winner contact system
- [x] Notification system (outbid, won, cancelled, messages)
- [x] Basic messaging
- [x] Favorites/Watchlist
- [x] Automatic bidding system
- [x] Comprehensive E2E testing (100% pass rate)

## Future/Backlog
- P1: Image upload to cloud storage (currently base64)
- P1: Ratings/reviews for sellers
- P2: Payment integration (Stripe)
- P2: Push notifications (web)
- P2: Search autocomplete
- P3: Admin panel
- P3: Backend route modularization
