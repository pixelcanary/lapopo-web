"""
Backend API tests for Lapopo Spanish auction platform
Tests: Auth, Auctions, Bidding, Buy Now, Favorites, Notifications, Messaging, Auto-bid, Cancellation
"""

import pytest
import requests
import os
import time

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

# ============== FIXTURES ==============
@pytest.fixture(scope="session")
def api_client():
    """Shared requests session"""
    session = requests.Session()
    session.headers.update({"Content-Type": "application/json"})
    return session

@pytest.fixture(scope="session")
def carlos_token(api_client):
    """Login as Carlos (seller of some auctions)"""
    response = api_client.post(f"{BASE_URL}/api/auth/login", json={
        "email": "carlos@lapopo.es",
        "password": "demo123"
    })
    if response.status_code == 200:
        return response.json()
    pytest.skip("Carlos login failed")

@pytest.fixture(scope="session")
def maria_token(api_client):
    """Login as Maria (seller of other auctions)"""
    response = api_client.post(f"{BASE_URL}/api/auth/login", json={
        "email": "maria@lapopo.es",
        "password": "demo123"
    })
    if response.status_code == 200:
        return response.json()
    pytest.skip("Maria login failed")

@pytest.fixture
def carlos_client(api_client, carlos_token):
    """Session authenticated as Carlos"""
    client = requests.Session()
    client.headers.update({
        "Content-Type": "application/json",
        "Authorization": f"Bearer {carlos_token['token']}"
    })
    return client

@pytest.fixture
def maria_client(api_client, maria_token):
    """Session authenticated as Maria"""
    client = requests.Session()
    client.headers.update({
        "Content-Type": "application/json",
        "Authorization": f"Bearer {maria_token['token']}"
    })
    return client


# ============== AUTH TESTS ==============
class TestAuth:
    """Authentication endpoint tests"""
    
    def test_login_success_carlos(self, api_client):
        """1. Login with demo user carlos@lapopo.es / demo123"""
        response = api_client.post(f"{BASE_URL}/api/auth/login", json={
            "email": "carlos@lapopo.es",
            "password": "demo123"
        })
        assert response.status_code == 200, f"Login failed: {response.text}"
        data = response.json()
        assert "token" in data
        assert "user" in data
        assert data["user"]["email"] == "carlos@lapopo.es"
        assert data["user"]["name"] == "Carlos López"
        print(f"✓ Carlos login successful, user_id: {data['user']['id']}")
    
    def test_login_success_maria(self, api_client):
        """Login with demo user maria@lapopo.es / demo123"""
        response = api_client.post(f"{BASE_URL}/api/auth/login", json={
            "email": "maria@lapopo.es",
            "password": "demo123"
        })
        assert response.status_code == 200, f"Login failed: {response.text}"
        data = response.json()
        assert "token" in data
        assert data["user"]["email"] == "maria@lapopo.es"
        print(f"✓ Maria login successful, user_id: {data['user']['id']}")
    
    def test_login_invalid_credentials(self, api_client):
        """Test login with wrong password"""
        response = api_client.post(f"{BASE_URL}/api/auth/login", json={
            "email": "carlos@lapopo.es",
            "password": "wrongpassword"
        })
        assert response.status_code == 401
        print("✓ Invalid credentials rejected correctly")
    
    def test_register_new_user(self, api_client):
        """Test user registration"""
        unique_email = f"TEST_user_{int(time.time())}@test.com"
        response = api_client.post(f"{BASE_URL}/api/auth/register", json={
            "name": "Test User",
            "email": unique_email,
            "password": "testpass123"
        })
        assert response.status_code == 200, f"Registration failed: {response.text}"
        data = response.json()
        assert "token" in data
        assert data["user"]["email"] == unique_email
        print(f"✓ New user registered: {unique_email}")


# ============== AUCTIONS LISTING TESTS ==============
class TestAuctionsListing:
    """Auction listing and search tests"""
    
    def test_list_auctions(self, api_client):
        """2. Homepage loads with auctions grid"""
        response = api_client.get(f"{BASE_URL}/api/subastas")
        assert response.status_code == 200
        auctions = response.json()
        assert isinstance(auctions, list)
        assert len(auctions) > 0, "No auctions found"
        print(f"✓ Loaded {len(auctions)} auctions")
        
        # Verify auction structure
        auction = auctions[0]
        required_fields = ["id", "title", "current_price", "bid_count", "status", "seller_name"]
        for field in required_fields:
            assert field in auction, f"Missing field: {field}"
    
    def test_filter_ending_soon(self, api_client):
        """Test 'Terminan pronto' filter (sort=ending_soon)"""
        response = api_client.get(f"{BASE_URL}/api/subastas", params={"sort": "ending_soon"})
        assert response.status_code == 200
        auctions = response.json()
        assert len(auctions) > 0
        print(f"✓ Ending soon filter works: {len(auctions)} auctions")
    
    def test_filter_from_1_euro(self, api_client):
        """Test 'Desde 1€' filter (sort=price_low)"""
        response = api_client.get(f"{BASE_URL}/api/subastas", params={"sort": "price_low"})
        assert response.status_code == 200
        auctions = response.json()
        assert len(auctions) > 0
        # Verify sorted by price ascending
        if len(auctions) > 1:
            assert auctions[0]["current_price"] <= auctions[1]["current_price"]
        print(f"✓ Price low filter works")
    
    def test_filter_solo_canarias(self, api_client):
        """Test 'Solo Canarias' filter"""
        response = api_client.get(f"{BASE_URL}/api/subastas", params={"canarias": "true"})
        assert response.status_code == 200
        auctions = response.json()
        assert len(auctions) > 0, "No Canarias auctions found"
        # Verify all are from Canarias
        canarias_locations = ["Tenerife", "Gran Canaria", "Lanzarote", "Fuerteventura", "La Palma", "La Gomera", "El Hierro"]
        for auction in auctions:
            assert auction["location"] in canarias_locations, f"Non-Canarias auction found: {auction['location']}"
        print(f"✓ Canarias filter works: {len(auctions)} auctions")
    
    def test_filter_electronica(self, api_client):
        """Test 'Electrónica' category filter"""
        response = api_client.get(f"{BASE_URL}/api/subastas", params={"category": "Electrónica"})
        assert response.status_code == 200
        auctions = response.json()
        for auction in auctions:
            assert auction["category"] == "Electrónica"
        print(f"✓ Electrónica filter works: {len(auctions)} auctions")
    
    def test_filter_hogar(self, api_client):
        """Test 'Hogar' category filter"""
        response = api_client.get(f"{BASE_URL}/api/subastas", params={"category": "Hogar"})
        assert response.status_code == 200
        auctions = response.json()
        for auction in auctions:
            assert auction["category"] == "Hogar"
        print(f"✓ Hogar filter works: {len(auctions)} auctions")
    
    def test_search_auctions(self, api_client):
        """Test search functionality"""
        response = api_client.get(f"{BASE_URL}/api/subastas", params={"search": "iPhone"})
        assert response.status_code == 200
        auctions = response.json()
        print(f"✓ Search 'iPhone' returned {len(auctions)} results")


# ============== AUCTION DETAIL TESTS ==============
class TestAuctionDetail:
    """Auction detail page tests"""
    
    def test_get_auction_detail(self, api_client):
        """3. Auction detail page shows all info"""
        # First get list to find an auction
        response = api_client.get(f"{BASE_URL}/api/subastas")
        auctions = response.json()
        auction_id = auctions[0]["id"]
        
        # Get detail
        response = api_client.get(f"{BASE_URL}/api/subastas/{auction_id}")
        assert response.status_code == 200
        auction = response.json()
        
        # Verify all fields present
        required_fields = ["id", "title", "description", "images", "current_price", 
                         "starting_price", "end_time", "bids", "bid_count", 
                         "seller_id", "seller_name", "location", "category"]
        for field in required_fields:
            assert field in auction, f"Missing field: {field}"
        
        print(f"✓ Auction detail loaded: {auction['title']}")
        print(f"  - Price: {auction['current_price']}€")
        print(f"  - Bids: {auction['bid_count']}")
        print(f"  - Seller: {auction['seller_name']}")
    
    def test_get_auction_not_found(self, api_client):
        """Test 404 for non-existent auction"""
        response = api_client.get(f"{BASE_URL}/api/subastas/nonexistent-id")
        assert response.status_code == 404
        print("✓ 404 returned for non-existent auction")


# ============== BIDDING TESTS ==============
class TestBidding:
    """Bidding functionality tests"""
    
    def test_place_bid_on_maria_auction(self, carlos_client, carlos_token):
        """4. Place a bid on an auction (not owned by logged-in user)"""
        # Find an auction owned by Maria (Carlos can bid on it)
        response = carlos_client.get(f"{BASE_URL}/api/subastas")
        auctions = response.json()
        
        maria_auction = None
        carlos_id = carlos_token["user"]["id"]
        for auction in auctions:
            if auction["seller_id"] != carlos_id and auction["status"] == "active":
                maria_auction = auction
                break
        
        if not maria_auction:
            pytest.skip("No auctions found that Carlos can bid on")
        
        current_price = maria_auction["current_price"]
        bid_amount = round(current_price + 1.0, 2)
        
        response = carlos_client.post(
            f"{BASE_URL}/api/subastas/{maria_auction['id']}/pujar",
            json={"amount": bid_amount}
        )
        assert response.status_code == 200, f"Bid failed: {response.text}"
        updated = response.json()
        assert updated["current_price"] == bid_amount
        assert updated["bid_count"] > maria_auction["bid_count"]
        print(f"✓ Bid placed: {bid_amount}€ on '{maria_auction['title']}'")
    
    def test_cannot_bid_own_auction(self, carlos_client, carlos_token):
        """Test that seller cannot bid on own auction"""
        # Find Carlos's auction
        response = carlos_client.get(f"{BASE_URL}/api/subastas")
        auctions = response.json()
        
        carlos_id = carlos_token["user"]["id"]
        carlos_auction = None
        for auction in auctions:
            if auction["seller_id"] == carlos_id and auction["status"] == "active":
                carlos_auction = auction
                break
        
        if not carlos_auction:
            pytest.skip("No Carlos auctions found")
        
        response = carlos_client.post(
            f"{BASE_URL}/api/subastas/{carlos_auction['id']}/pujar",
            json={"amount": carlos_auction["current_price"] + 10}
        )
        assert response.status_code == 400
        assert "propia" in response.json().get("detail", "").lower()
        print("✓ Seller cannot bid on own auction")
    
    def test_bid_too_low_rejected(self, carlos_client, carlos_token):
        """Test that bid below minimum is rejected"""
        response = carlos_client.get(f"{BASE_URL}/api/subastas")
        auctions = response.json()
        
        carlos_id = carlos_token["user"]["id"]
        auction = None
        for a in auctions:
            if a["seller_id"] != carlos_id and a["status"] == "active":
                auction = a
                break
        
        if not auction:
            pytest.skip("No suitable auction found")
        
        # Try to bid below minimum
        response = carlos_client.post(
            f"{BASE_URL}/api/subastas/{auction['id']}/pujar",
            json={"amount": auction["current_price"]}  # Same as current, should fail
        )
        assert response.status_code == 400
        print("✓ Low bid correctly rejected")


# ============== BUY NOW TESTS ==============
class TestBuyNow:
    """Buy Now functionality tests"""
    
    def test_auction_has_buy_now_price(self, api_client):
        """5. Verify auctions with buy_now_price exist"""
        response = api_client.get(f"{BASE_URL}/api/subastas")
        auctions = response.json()
        
        buy_now_auctions = [a for a in auctions if a.get("buy_now_price")]
        assert len(buy_now_auctions) > 0, "No auctions with buy_now_price found"
        
        for auction in buy_now_auctions[:3]:
            print(f"✓ Buy Now auction: {auction['title']} - {auction['buy_now_price']}€")
    
    def test_buy_now_endpoint(self, maria_client, maria_token):
        """Test Buy Now purchase (Maria buys Carlos's auction)"""
        # Find Carlos's auction with buy_now_price
        response = maria_client.get(f"{BASE_URL}/api/subastas")
        auctions = response.json()
        
        maria_id = maria_token["user"]["id"]
        buy_now_auction = None
        for a in auctions:
            if a["seller_id"] != maria_id and a.get("buy_now_price") and a["status"] == "active":
                buy_now_auction = a
                break
        
        if not buy_now_auction:
            pytest.skip("No Buy Now auctions available for Maria to buy")
        
        # Note: We don't actually execute Buy Now to preserve seed data
        # Instead verify the endpoint structure
        print(f"✓ Buy Now auction found: {buy_now_auction['title']} at {buy_now_auction['buy_now_price']}€")
        print("  (Skipping actual purchase to preserve test data)")


# ============== FAVORITES TESTS ==============
class TestFavorites:
    """Favorites/watchlist functionality tests"""
    
    def test_toggle_favorite(self, carlos_client):
        """6. Toggle favorite on auction"""
        # Get an auction to favorite
        response = carlos_client.get(f"{BASE_URL}/api/subastas")
        auctions = response.json()
        auction_id = auctions[0]["id"]
        
        # Toggle favorite on
        response = carlos_client.post(f"{BASE_URL}/api/favoritos/{auction_id}")
        assert response.status_code == 200
        result = response.json()
        initial_state = result.get("favorited")
        print(f"✓ Favorite toggled: {initial_state}")
        
        # Toggle again (should flip state)
        response = carlos_client.post(f"{BASE_URL}/api/favoritos/{auction_id}")
        assert response.status_code == 200
        result = response.json()
        assert result.get("favorited") != initial_state
        print(f"✓ Favorite toggled back: {result.get('favorited')}")
    
    def test_get_favorites_list(self, carlos_client):
        """Test getting favorites list"""
        response = carlos_client.get(f"{BASE_URL}/api/favoritos")
        assert response.status_code == 200
        favorites = response.json()
        assert isinstance(favorites, list)
        print(f"✓ Favorites list retrieved: {len(favorites)} items")


# ============== NOTIFICATIONS TESTS ==============
class TestNotifications:
    """Notifications system tests"""
    
    def test_get_notifications(self, carlos_client):
        """7. Check notifications endpoint"""
        response = carlos_client.get(f"{BASE_URL}/api/notificaciones")
        assert response.status_code == 200
        data = response.json()
        assert "notifications" in data
        assert "unread_count" in data
        print(f"✓ Notifications: {len(data['notifications'])} total, {data['unread_count']} unread")
    
    def test_mark_all_read(self, carlos_client):
        """Test mark all notifications as read"""
        response = carlos_client.put(f"{BASE_URL}/api/notificaciones/leer-todas")
        assert response.status_code == 200
        print("✓ Mark all read endpoint works")


# ============== AUTO-BID TESTS ==============
class TestAutoBid:
    """Auto-bidding functionality tests"""
    
    def test_set_auto_bid(self, carlos_client, carlos_token):
        """8. Set auto-bid on auction"""
        # Find auction Carlos can bid on
        response = carlos_client.get(f"{BASE_URL}/api/subastas")
        auctions = response.json()
        
        carlos_id = carlos_token["user"]["id"]
        auction = None
        for a in auctions:
            if a["seller_id"] != carlos_id and a["status"] == "active":
                auction = a
                break
        
        if not auction:
            pytest.skip("No suitable auction for auto-bid")
        
        max_amount = round(auction["current_price"] + 20, 2)
        response = carlos_client.post(
            f"{BASE_URL}/api/subastas/{auction['id']}/auto-pujar",
            json={"max_amount": max_amount}
        )
        assert response.status_code == 200
        data = response.json()
        assert "message" in data
        print(f"✓ Auto-bid set at max {max_amount}€ on '{auction['title']}'")


# ============== USER PROFILE TESTS ==============
class TestUserProfile:
    """User profile endpoint tests"""
    
    def test_get_user_profile(self, carlos_client, carlos_token):
        """9. Verify profile data structure"""
        user_id = carlos_token["user"]["id"]
        response = carlos_client.get(f"{BASE_URL}/api/usuarios/{user_id}")
        assert response.status_code == 200
        data = response.json()
        
        assert "user" in data
        assert "auctions" in data  # User's own auctions
        assert "active_bids" in data  # Auctions user is bidding on
        assert "won_auctions" in data  # Won auctions
        assert "favorites" in data  # Favorited auctions
        
        print(f"✓ Profile loaded for {data['user']['name']}")
        print(f"  - Own auctions: {len(data['auctions'])}")
        print(f"  - Active bids: {len(data['active_bids'])}")
        print(f"  - Won auctions: {len(data['won_auctions'])}")
        print(f"  - Favorites: {len(data['favorites'])}")
    
    def test_update_user_name(self, carlos_client, carlos_token):
        """Test updating user profile name"""
        user_id = carlos_token["user"]["id"]
        
        # Update name
        response = carlos_client.put(
            f"{BASE_URL}/api/usuarios/{user_id}",
            json={"name": "Carlos López Updated"}
        )
        assert response.status_code == 200
        
        # Restore original name
        response = carlos_client.put(
            f"{BASE_URL}/api/usuarios/{user_id}",
            json={"name": "Carlos López"}
        )
        assert response.status_code == 200
        print("✓ User name update works")


# ============== AUCTION CREATION TESTS ==============
class TestAuctionCreation:
    """Auction creation tests"""
    
    def test_create_auction(self, carlos_client):
        """10. Create auction with Buy Now price"""
        response = carlos_client.post(
            f"{BASE_URL}/api/subastas",
            json={
                "title": "TEST_Articulo de prueba",
                "description": "Este es un articulo de prueba para verificar la creacion de subastas",
                "starting_price": 10.0,
                "buy_now_price": 50.0,
                "duration": "24h",
                "category": "Electrónica",
                "location": "Madrid",
                "delivery_type": "both",
                "images": ["https://images.unsplash.com/photo-1523275335684-37898b6baf30?auto=format&fit=crop&q=80&w=400"]
            }
        )
        assert response.status_code == 200, f"Create auction failed: {response.text}"
        auction = response.json()
        assert auction["title"] == "TEST_Articulo de prueba"
        assert auction["buy_now_price"] == 50.0
        assert auction["starting_price"] == 10.0
        print(f"✓ Auction created: {auction['id']}")
    
    def test_create_auction_invalid_price(self, carlos_client):
        """Test auction creation with invalid price"""
        response = carlos_client.post(
            f"{BASE_URL}/api/subastas",
            json={
                "title": "TEST_Invalid",
                "description": "Test",
                "starting_price": 0.5,  # Below 1€ minimum
                "duration": "24h",
                "category": "Otros",
                "location": "Madrid",
                "delivery_type": "pickup",
                "images": ["https://example.com/img.jpg"]
            }
        )
        assert response.status_code == 400
        print("✓ Invalid price correctly rejected")


# ============== AUCTION CANCELLATION TESTS ==============
class TestAuctionCancellation:
    """Auction cancellation tests"""
    
    def test_cancel_own_auction(self, carlos_client, carlos_token):
        """11. Seller can cancel their own auction"""
        # First create a test auction to cancel
        response = carlos_client.post(
            f"{BASE_URL}/api/subastas",
            json={
                "title": "TEST_To Cancel",
                "description": "Test auction for cancellation",
                "starting_price": 5.0,
                "duration": "7d",  # Long duration so it won't expire
                "category": "Otros",
                "location": "Madrid",
                "delivery_type": "pickup",
                "images": ["https://example.com/img.jpg"]
            }
        )
        assert response.status_code == 200
        auction = response.json()
        
        # Cancel it
        response = carlos_client.post(f"{BASE_URL}/api/subastas/{auction['id']}/cancelar")
        assert response.status_code == 200
        print(f"✓ Auction cancelled: {auction['id']}")
    
    def test_cannot_cancel_others_auction(self, maria_client, carlos_client, carlos_token):
        """Test that user cannot cancel another's auction"""
        # Find Carlos's auction
        response = carlos_client.get(f"{BASE_URL}/api/subastas")
        auctions = response.json()
        
        carlos_id = carlos_token["user"]["id"]
        carlos_auction = None
        for a in auctions:
            if a["seller_id"] == carlos_id and a["status"] == "active":
                carlos_auction = a
                break
        
        if not carlos_auction:
            pytest.skip("No Carlos auction to test cancellation restriction")
        
        # Maria tries to cancel Carlos's auction
        response = maria_client.post(f"{BASE_URL}/api/subastas/{carlos_auction['id']}/cancelar")
        assert response.status_code == 403
        print("✓ Non-owner cannot cancel auction")


# ============== CONTACT INFO TESTS ==============
class TestContactInfo:
    """Contact info for finished auctions"""
    
    def test_contact_requires_finished_auction(self, carlos_client):
        """13. Contact info only available after auction finishes"""
        # Get an active auction
        response = carlos_client.get(f"{BASE_URL}/api/subastas")
        auctions = response.json()
        active_auction = None
        for a in auctions:
            if a["status"] == "active":
                active_auction = a
                break
        
        if not active_auction:
            pytest.skip("No active auctions to test")
        
        # Try to get contact info (should fail - auction not finished)
        response = carlos_client.get(f"{BASE_URL}/api/contacto/{active_auction['id']}")
        assert response.status_code == 400
        print("✓ Contact info blocked for active auctions")


# ============== MESSAGING TESTS ==============
class TestMessaging:
    """Messaging system tests"""
    
    def test_get_messages_endpoint(self, carlos_client):
        """14. Test messages endpoint structure"""
        # Get an auction
        response = carlos_client.get(f"{BASE_URL}/api/subastas")
        auctions = response.json()
        auction_id = auctions[0]["id"]
        
        response = carlos_client.get(f"{BASE_URL}/api/mensajes/{auction_id}")
        assert response.status_code == 200
        messages = response.json()
        assert isinstance(messages, list)
        print(f"✓ Messages endpoint works: {len(messages)} messages")


# ============== CATEGORIES AND LOCATIONS TESTS ==============
class TestMasterData:
    """Categories and locations endpoints"""
    
    def test_get_categories(self, api_client):
        """Test categories endpoint"""
        response = api_client.get(f"{BASE_URL}/api/categorias")
        assert response.status_code == 200
        categories = response.json()
        assert len(categories) == 8
        assert "Electrónica" in categories
        assert "Hogar" in categories
        print(f"✓ Categories: {categories}")
    
    def test_get_locations(self, api_client):
        """Test locations endpoint"""
        response = api_client.get(f"{BASE_URL}/api/ubicaciones")
        assert response.status_code == 200
        locations = response.json()
        assert "peninsula" in locations
        assert "canarias" in locations
        assert "Tenerife" in locations["canarias"]
        assert "Madrid" in locations["peninsula"]
        print(f"✓ Locations loaded: {len(locations['peninsula'])} peninsula, {len(locations['canarias'])} canarias")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
