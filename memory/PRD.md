# Lapopo - PRD (Product Requirements Document)

## Problem Statement
Plataforma de subastas de segunda mano enfocada en España y Canarias, similar a Wallapop pero con subastas desde 1€.

## Architecture
- **Frontend**: React + Tailwind CSS + Shadcn UI
- **Backend**: FastAPI (Python)
- **Database**: MongoDB (Motor async driver)
- **Auth**: JWT (PyJWT + bcrypt/passlib)
- **Images**: Base64 encoded in MongoDB

## User Personas
1. **Vendedor**: Usuario que publica artículos en subasta
2. **Comprador**: Usuario que busca y puja por artículos
3. **Canarias Local**: Usuario en las Islas Canarias, prefiere recogida en mano

## Core Requirements
- JWT auth (registro/login con email y contraseña)
- CRUD de subastas con fotos (base64)
- Sistema de pujas con validación (mín. precio actual + 0.50€)
- Filtros: categoría, ubicación, Solo Canarias, búsqueda
- Contador regresivo en tiempo real
- Auto-cierre de subastas expiradas
- UI en español, mobile-first, responsive

## What's Been Implemented (2026-03-10)
- ✅ Backend completo: 17 endpoints API
- ✅ Auth JWT (registro, login)
- ✅ CRUD subastas con filtros
- ✅ Sistema de pujas con validación
- ✅ Seed data (12 subastas demo, 2 usuarios demo)
- ✅ Frontend: 5 páginas (Home, Auth, CreateAuction, AuctionDetail, Profile)
- ✅ Componentes: Header, MobileNav, AuctionCard, Countdown
- ✅ Diseño: colores Lapopo (#18b29c, #ffb347), Nunito font, rounded cards, pill buttons
- ✅ Solo Canarias section con badge
- ✅ FAQ con accordion
- ✅ Sell in 3 steps section
- ✅ Profile con edición y tabs (mis subastas, mis pujas)
- ✅ 100% tests backend, 95% frontend, 100% mobile

## Prioritized Backlog
### P0 (Critical - Done)
- [x] Auth, subastas CRUD, pujas, seed data, UI completa

### P1 (Important)
- [ ] Sistema de notificaciones (subasta ganada, superado en puja)
- [ ] Sistema de mensajería vendedor-comprador
- [ ] Favoritos / watchlist de subastas

### P2 (Nice to have)
- [ ] WebSockets para pujas en tiempo real
- [ ] Sistema de valoraciones vendedor/comprador
- [ ] Galería de fotos con zoom
- [ ] Compartir subasta en redes sociales
- [ ] Historial de subastas ganadas/compradas

## Next Tasks
1. Notificaciones cuando una subasta termina
2. Mensajería entre comprador y vendedor
3. Favoritos/watchlist
4. WebSockets para actualización instantánea de pujas
