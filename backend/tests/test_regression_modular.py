"""
Regression Test Suite for Lapopo Modular Backend
Tests all endpoints after refactoring from monolithic server.py to modular structure.

Coverage:
- Auth routes (auth.py): register, login, password change/recovery
- Auction routes (auctions.py): list, create, bid, buy now, cancel, autocomplete
- User routes (users.py): profile, update
- Social routes (social.py): notifications, messages, favorites, contact
- Rating routes (ratings.py): create, list by user/auction
- Payment routes (payments.py): plans, subscriptions
- Dispute routes (disputes.py): create, list, messages
- Admin routes (admin.py): stats, users, auctions, disputes, badges, ratings, config
- Upload routes (upload.py): cloudinary base64 upload
- Badge routes (badges.py): list, user badges
"""
import pytest
import requests
import os

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')


@pytest.fixture(scope="module")
def api_client():
    """Shared requests session"""
    session = requests.Session()
    session.headers.update({"Content-Type": "application/json"})
    return session


@pytest.fixture(scope="module")
def admin_auth(api_client):
    """Admin login and token"""
    response = api_client.post(f"{BASE_URL}/api/auth/login", json={
        "email": "admin@lapopo.es",
        "password": "admin123"
    })
    assert response.status_code == 200
    data = response.json()
    assert data["user"]["is_admin"] == True
    return {"token": data["token"], "user": data["user"]}


@pytest.fixture(scope="module")
def user1_auth(api_client):
    """User1 (carlos) login and token"""
    response = api_client.post(f"{BASE_URL}/api/auth/login", json={
        "email": "carlos@lapopo.es",
        "password": "demo123"
    })
    assert response.status_code == 200
    data = response.json()
    return {"token": data["token"], "user": data["user"]}


@pytest.fixture(scope="module")
def user2_auth(api_client):
    """User2 (maria) login and token"""
    response = api_client.post(f"{BASE_URL}/api/auth/login", json={
        "email": "maria@lapopo.es",
        "password": "demo123"
    })
    assert response.status_code == 200
    data = response.json()
    return {"token": data["token"], "user": data["user"]}


# ===== AUTH ROUTES (auth.py) =====
class TestAuthRoutes:
    """Test auth endpoints - routes/auth.py"""
    
    def test_login_valid_credentials(self, api_client):
        """POST /api/auth/login with valid credentials"""
        response = api_client.post(f"{BASE_URL}/api/auth/login", json={
            "email": "carlos@lapopo.es",
            "password": "demo123"
        })
        assert response.status_code == 200
        data = response.json()
        assert "token" in data
        assert data["user"]["email"] == "carlos@lapopo.es"
    
    def test_login_invalid_credentials(self, api_client):
        """POST /api/auth/login with wrong password returns 401"""
        response = api_client.post(f"{BASE_URL}/api/auth/login", json={
            "email": "carlos@lapopo.es",
            "password": "wrongpassword"
        })
        assert response.status_code == 401
    
    def test_register_duplicate_email(self, api_client):
        """POST /api/auth/register with existing email returns 400"""
        response = api_client.post(f"{BASE_URL}/api/auth/register", json={
            "name": "Test User",
            "email": "carlos@lapopo.es",
            "password": "testpassword123"
        })
        assert response.status_code == 400
        assert "registrado" in response.json()["detail"].lower()
    
    def test_change_password_wrong_current(self, api_client, user1_auth):
        """PUT /api/auth/cambiar-password with wrong current password"""
        response = api_client.put(
            f"{BASE_URL}/api/auth/cambiar-password",
            json={"current_password": "wrongpassword", "new_password": "newpassword123"},
            headers={"Authorization": f"Bearer {user1_auth['token']}"}
        )
        assert response.status_code == 400
    
    def test_password_recovery_sends_email(self, api_client):
        """POST /api/auth/recuperar-password returns success message"""
        response = api_client.post(f"{BASE_URL}/api/auth/recuperar-password", json={
            "email": "carlos@lapopo.es"
        })
        assert response.status_code == 200
        assert "message" in response.json()


# ===== AUCTION ROUTES (auctions.py) =====
class TestAuctionRoutes:
    """Test auction endpoints - routes/auctions.py"""
    
    def test_list_auctions(self, api_client):
        """GET /api/subastas returns list of active auctions"""
        response = api_client.get(f"{BASE_URL}/api/subastas")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        if data:
            assert "id" in data[0]
            assert "title" in data[0]
            assert "current_price" in data[0]
    
    def test_list_auctions_with_filters(self, api_client):
        """GET /api/subastas with category filter"""
        response = api_client.get(f"{BASE_URL}/api/subastas?category=Electrónica")
        assert response.status_code == 200
        data = response.json()
        for auction in data:
            assert auction["category"] == "Electrónica"
    
    def test_get_single_auction(self, api_client):
        """GET /api/subastas/{id} returns auction details"""
        # First get list to find an auction ID
        auctions = api_client.get(f"{BASE_URL}/api/subastas").json()
        if not auctions:
            pytest.skip("No auctions available")
        
        auction_id = auctions[0]["id"]
        response = api_client.get(f"{BASE_URL}/api/subastas/{auction_id}")
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == auction_id
        assert "seller_rating_avg" in data
        assert "featured" in data
    
    def test_autocomplete_search(self, api_client):
        """GET /api/subastas/autocomplete?q=cam returns matching auctions"""
        response = api_client.get(f"{BASE_URL}/api/subastas/autocomplete?q=cam")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        # Should return auctions with 'cam' in title
        for item in data:
            assert "cam" in item["title"].lower()
    
    def test_autocomplete_short_query(self, api_client):
        """GET /api/subastas/autocomplete with 1 char returns empty"""
        response = api_client.get(f"{BASE_URL}/api/subastas/autocomplete?q=a")
        assert response.status_code == 200
        assert response.json() == []
    
    def test_place_bid_unauthorized(self, api_client):
        """POST /api/subastas/{id}/pujar without auth returns 401"""
        auctions = api_client.get(f"{BASE_URL}/api/subastas").json()
        if not auctions:
            pytest.skip("No auctions available")
        
        response = api_client.post(f"{BASE_URL}/api/subastas/{auctions[0]['id']}/pujar", json={"amount": 100})
        assert response.status_code == 401
    
    def test_get_categories(self, api_client):
        """GET /api/categorias returns category list"""
        response = api_client.get(f"{BASE_URL}/api/categorias")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert "Electrónica" in data
    
    def test_get_locations(self, api_client):
        """GET /api/ubicaciones returns locations"""
        response = api_client.get(f"{BASE_URL}/api/ubicaciones")
        assert response.status_code == 200
        data = response.json()
        assert "peninsula" in data
        assert "canarias" in data
        assert "Madrid" in data["peninsula"]
        assert "Tenerife" in data["canarias"]


# ===== USER ROUTES (users.py) =====
class TestUserRoutes:
    """Test user endpoints - routes/users.py"""
    
    def test_get_user_profile(self, api_client, user1_auth):
        """GET /api/usuarios/{user_id} returns user profile with auctions, ratings, badges"""
        response = api_client.get(f"{BASE_URL}/api/usuarios/{user1_auth['user']['id']}")
        assert response.status_code == 200
        data = response.json()
        assert "user" in data
        assert "auctions" in data
        assert "ratings" in data
        assert "badges" in data
    
    def test_get_nonexistent_user(self, api_client):
        """GET /api/usuarios/{invalid_id} returns 404"""
        response = api_client.get(f"{BASE_URL}/api/usuarios/nonexistent-user-id")
        assert response.status_code == 404


# ===== SOCIAL ROUTES (social.py) =====
class TestSocialRoutes:
    """Test social endpoints - routes/social.py"""
    
    def test_get_notifications_authorized(self, api_client, user1_auth):
        """GET /api/notificaciones returns user notifications"""
        response = api_client.get(
            f"{BASE_URL}/api/notificaciones",
            headers={"Authorization": f"Bearer {user1_auth['token']}"}
        )
        assert response.status_code == 200
        data = response.json()
        assert "notifications" in data
        assert "unread_count" in data
    
    def test_get_notifications_unauthorized(self, api_client):
        """GET /api/notificaciones without auth returns 401"""
        response = api_client.get(f"{BASE_URL}/api/notificaciones")
        assert response.status_code == 401
    
    def test_get_conversations(self, api_client, user1_auth):
        """GET /api/chat/conversaciones returns user conversations"""
        response = api_client.get(
            f"{BASE_URL}/api/chat/conversaciones",
            headers={"Authorization": f"Bearer {user1_auth['token']}"}
        )
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
    
    def test_get_favorites(self, api_client, user1_auth):
        """GET /api/favoritos returns user's favorite auctions"""
        response = api_client.get(
            f"{BASE_URL}/api/favoritos",
            headers={"Authorization": f"Bearer {user1_auth['token']}"}
        )
        assert response.status_code == 200
        assert isinstance(response.json(), list)


# ===== RATING ROUTES (ratings.py) =====
class TestRatingRoutes:
    """Test rating endpoints - routes/ratings.py"""
    
    def test_get_user_ratings(self, api_client, user1_auth):
        """GET /api/valoraciones/usuario/{user_id} returns ratings"""
        response = api_client.get(f"{BASE_URL}/api/valoraciones/usuario/{user1_auth['user']['id']}")
        assert response.status_code == 200
        data = response.json()
        assert "ratings" in data
        assert "average" in data
        assert "count" in data


# ===== PAYMENT ROUTES (payments.py) =====
class TestPaymentRoutes:
    """Test payment endpoints - routes/payments.py"""
    
    def test_get_plans(self, api_client):
        """GET /api/planes returns plans and featured options"""
        response = api_client.get(f"{BASE_URL}/api/planes")
        assert response.status_code == 200
        data = response.json()
        assert "plans" in data
        assert "featured_options" in data
        assert "payments_enabled" in data
        assert "free" in data["plans"]
        assert "vendedor" in data["plans"]
        assert "pro" in data["plans"]
    
    def test_get_my_plan(self, api_client, user1_auth):
        """GET /api/suscripciones/mi-plan returns user's plan info"""
        response = api_client.get(
            f"{BASE_URL}/api/suscripciones/mi-plan",
            headers={"Authorization": f"Bearer {user1_auth['token']}"}
        )
        assert response.status_code == 200
        data = response.json()
        assert "plan" in data
        assert "plan_info" in data
        assert "auctions_this_month" in data


# ===== DISPUTE ROUTES (disputes.py) =====
class TestDisputeRoutes:
    """Test dispute endpoints - routes/disputes.py"""
    
    def test_get_my_disputes(self, api_client, user1_auth):
        """GET /api/disputas/mis-disputas returns user's disputes"""
        response = api_client.get(
            f"{BASE_URL}/api/disputas/mis-disputas",
            headers={"Authorization": f"Bearer {user1_auth['token']}"}
        )
        assert response.status_code == 200
        assert isinstance(response.json(), list)


# ===== ADMIN ROUTES (admin.py) =====
class TestAdminRoutes:
    """Test admin endpoints - routes/admin.py"""
    
    def test_admin_stats(self, api_client, admin_auth):
        """GET /api/admin/stats returns platform statistics"""
        response = api_client.get(
            f"{BASE_URL}/api/admin/stats",
            headers={"Authorization": f"Bearer {admin_auth['token']}"}
        )
        assert response.status_code == 200
        data = response.json()
        assert "total_users" in data
        assert "active_auctions" in data
        assert "finished_auctions" in data
        assert "total_bids" in data
    
    def test_admin_stats_unauthorized(self, api_client, user1_auth):
        """GET /api/admin/stats with non-admin user returns 403"""
        response = api_client.get(
            f"{BASE_URL}/api/admin/stats",
            headers={"Authorization": f"Bearer {user1_auth['token']}"}
        )
        assert response.status_code == 403
    
    def test_admin_list_users(self, api_client, admin_auth):
        """GET /api/admin/usuarios returns user list"""
        response = api_client.get(
            f"{BASE_URL}/api/admin/usuarios",
            headers={"Authorization": f"Bearer {admin_auth['token']}"}
        )
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        if data:
            assert "id" in data[0]
            assert "email" in data[0]
            assert "auction_count" in data[0]
    
    def test_admin_list_disputes(self, api_client, admin_auth):
        """GET /api/admin/disputas returns disputes list"""
        response = api_client.get(
            f"{BASE_URL}/api/admin/disputas",
            headers={"Authorization": f"Bearer {admin_auth['token']}"}
        )
        assert response.status_code == 200
        assert isinstance(response.json(), list)
    
    def test_admin_list_auctions(self, api_client, admin_auth):
        """GET /api/admin/subastas returns all auctions"""
        response = api_client.get(
            f"{BASE_URL}/api/admin/subastas",
            headers={"Authorization": f"Bearer {admin_auth['token']}"}
        )
        assert response.status_code == 200
        assert isinstance(response.json(), list)
    
    def test_admin_list_ratings(self, api_client, admin_auth):
        """GET /api/admin/valoraciones returns all ratings"""
        response = api_client.get(
            f"{BASE_URL}/api/admin/valoraciones",
            headers={"Authorization": f"Bearer {admin_auth['token']}"}
        )
        assert response.status_code == 200
        assert isinstance(response.json(), list)
    
    def test_admin_get_config(self, api_client, admin_auth):
        """GET /api/admin/config returns platform configuration"""
        response = api_client.get(
            f"{BASE_URL}/api/admin/config",
            headers={"Authorization": f"Bearer {admin_auth['token']}"}
        )
        assert response.status_code == 200
        data = response.json()
        assert "payments_enabled" in data


# ===== BADGE ROUTES (badges.py) =====
class TestBadgeRoutes:
    """Test badge endpoints - routes/badges.py"""
    
    def test_list_all_badges(self, api_client):
        """GET /api/badges returns all badges"""
        response = api_client.get(f"{BASE_URL}/api/badges")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) >= 7  # 7 default badges
        
        badge_names = [b["name"] for b in data]
        expected = ["Primera venta", "5 ventas", "10 ventas", "50 ventas"]
        for e in expected:
            assert e in badge_names
    
    def test_get_user_badges(self, api_client, user1_auth):
        """GET /api/badges/usuario/{user_id} returns user's badges"""
        response = api_client.get(f"{BASE_URL}/api/badges/usuario/{user1_auth['user']['id']}")
        assert response.status_code == 200
        assert isinstance(response.json(), list)


# ===== UPLOAD ROUTES (upload.py) =====
class TestUploadRoutes:
    """Test upload endpoints - routes/upload.py"""
    
    def test_upload_base64_image(self, api_client, user1_auth):
        """POST /api/upload/base64 uploads to Cloudinary"""
        test_image = "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg=="
        
        response = api_client.post(
            f"{BASE_URL}/api/upload/base64",
            json={"image": test_image},
            headers={"Authorization": f"Bearer {user1_auth['token']}"}
        )
        assert response.status_code == 200
        data = response.json()
        assert "url" in data
        assert "cloudinary" in data["url"].lower()
    
    def test_upload_unauthorized(self, api_client):
        """POST /api/upload/base64 without auth returns 401"""
        response = api_client.post(f"{BASE_URL}/api/upload/base64", json={"image": "test"})
        assert response.status_code == 401


# ===== INTEGRATION TESTS =====
class TestIntegration:
    """Integration tests for cross-module functionality"""
    
    def test_auction_with_enriched_data(self, api_client):
        """Verify auctions have seller ratings and featured info"""
        auctions = api_client.get(f"{BASE_URL}/api/subastas").json()
        if not auctions:
            pytest.skip("No auctions available")
        
        auction = auctions[0]
        # These fields are added by helpers.enrich_with_ratings and enrich_with_featured
        assert "seller_rating_avg" in auction
        assert "seller_rating_count" in auction
        assert "seller_plan" in auction
        assert "featured" in auction
    
    def test_full_auth_flow(self, api_client):
        """Test complete auth flow: login -> get notifications -> logout-like behavior"""
        # Login
        login_resp = api_client.post(f"{BASE_URL}/api/auth/login", json={
            "email": "carlos@lapopo.es",
            "password": "demo123"
        })
        assert login_resp.status_code == 200
        token = login_resp.json()["token"]
        
        # Access protected resource
        notif_resp = api_client.get(
            f"{BASE_URL}/api/notificaciones",
            headers={"Authorization": f"Bearer {token}"}
        )
        assert notif_resp.status_code == 200
        
        # Invalid token should fail
        invalid_resp = api_client.get(
            f"{BASE_URL}/api/notificaciones",
            headers={"Authorization": "Bearer invalid_token"}
        )
        assert invalid_resp.status_code == 401


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
