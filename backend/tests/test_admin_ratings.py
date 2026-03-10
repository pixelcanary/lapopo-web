"""
Backend API tests for Lapopo - Admin Panel and Rating System
Tests: Admin authentication, Admin stats, Users management, Auctions management, Rating CRUD
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
def admin_login(api_client):
    """Login as Admin user"""
    response = api_client.post(f"{BASE_URL}/api/auth/login", json={
        "email": "admin@lapopo.es",
        "password": "admin123"
    })
    assert response.status_code == 200, f"Admin login failed: {response.text}"
    return response.json()

@pytest.fixture(scope="session")
def carlos_login(api_client):
    """Login as Carlos (normal user)"""
    response = api_client.post(f"{BASE_URL}/api/auth/login", json={
        "email": "carlos@lapopo.es",
        "password": "demo123"
    })
    assert response.status_code == 200, f"Carlos login failed: {response.text}"
    return response.json()

@pytest.fixture(scope="session")
def maria_login(api_client):
    """Login as Maria (normal user)"""
    response = api_client.post(f"{BASE_URL}/api/auth/login", json={
        "email": "maria@lapopo.es",
        "password": "demo123"
    })
    assert response.status_code == 200, f"Maria login failed: {response.text}"
    return response.json()

@pytest.fixture
def admin_client(admin_login):
    """Session authenticated as Admin"""
    client = requests.Session()
    client.headers.update({
        "Content-Type": "application/json",
        "Authorization": f"Bearer {admin_login['token']}"
    })
    return client

@pytest.fixture
def carlos_client(carlos_login):
    """Session authenticated as Carlos"""
    client = requests.Session()
    client.headers.update({
        "Content-Type": "application/json",
        "Authorization": f"Bearer {carlos_login['token']}"
    })
    return client

@pytest.fixture
def maria_client(maria_login):
    """Session authenticated as Maria"""
    client = requests.Session()
    client.headers.update({
        "Content-Type": "application/json",
        "Authorization": f"Bearer {maria_login['token']}"
    })
    return client


# ============== ADMIN LOGIN TEST ==============
class TestAdminLogin:
    """Admin authentication tests"""
    
    def test_admin_login_returns_is_admin_flag(self, api_client):
        """1. Admin login returns is_admin=true in response"""
        response = api_client.post(f"{BASE_URL}/api/auth/login", json={
            "email": "admin@lapopo.es",
            "password": "admin123"
        })
        assert response.status_code == 200
        data = response.json()
        assert "token" in data
        assert "user" in data
        assert data["user"]["is_admin"] == True
        assert data["user"]["email"] == "admin@lapopo.es"
        assert data["user"]["name"] == "Admin Lapopo"
        print(f"✓ Admin login successful, is_admin={data['user']['is_admin']}")
    
    def test_normal_user_login_has_is_admin_false(self, api_client):
        """Normal user login returns is_admin=false"""
        response = api_client.post(f"{BASE_URL}/api/auth/login", json={
            "email": "carlos@lapopo.es",
            "password": "demo123"
        })
        assert response.status_code == 200
        data = response.json()
        assert data["user"]["is_admin"] == False
        print(f"✓ Normal user login has is_admin=false")


# ============== ADMIN STATS ENDPOINT ==============
class TestAdminStats:
    """Admin statistics endpoint tests"""
    
    def test_admin_stats_returns_all_counts(self, admin_client):
        """2. Admin panel stats - users, active, finished, cancelled, bids, ratings"""
        response = admin_client.get(f"{BASE_URL}/api/admin/stats")
        assert response.status_code == 200
        stats = response.json()
        
        required_fields = ["total_users", "active_auctions", "finished_auctions", 
                          "cancelled_auctions", "total_bids", "total_ratings"]
        for field in required_fields:
            assert field in stats, f"Missing stats field: {field}"
            assert isinstance(stats[field], int), f"{field} should be integer"
        
        print(f"✓ Admin stats loaded:")
        print(f"  - Users: {stats['total_users']}")
        print(f"  - Active auctions: {stats['active_auctions']}")
        print(f"  - Finished auctions: {stats['finished_auctions']}")
        print(f"  - Cancelled auctions: {stats['cancelled_auctions']}")
        print(f"  - Total bids: {stats['total_bids']}")
        print(f"  - Total ratings: {stats['total_ratings']}")
    
    def test_normal_user_cannot_access_stats(self, carlos_client):
        """7. Normal user cannot access admin stats (403)"""
        response = carlos_client.get(f"{BASE_URL}/api/admin/stats")
        assert response.status_code == 403
        print("✓ Normal user correctly blocked from admin stats")


# ============== ADMIN USERS MANAGEMENT ==============
class TestAdminUsersManagement:
    """Admin users management tests"""
    
    def test_admin_list_users(self, admin_client):
        """3. Admin panel - Users tab shows all users with details"""
        response = admin_client.get(f"{BASE_URL}/api/admin/usuarios")
        assert response.status_code == 200
        users = response.json()
        
        assert isinstance(users, list)
        assert len(users) >= 3, "Should have at least 3 users (admin, carlos, maria)"
        
        # Verify user structure
        for user in users[:3]:
            assert "id" in user
            assert "name" in user
            assert "email" in user
            assert "auction_count" in user, "Missing auction_count field"
            # Rating fields may exist
            print(f"  User: {user['name']} ({user['email']}) - Auctions: {user.get('auction_count', 0)}, Rating: {user.get('rating_avg', 0)}")
        
        # Check for admin user with is_admin flag
        admin_user = next((u for u in users if u["email"] == "admin@lapopo.es"), None)
        assert admin_user is not None
        assert admin_user.get("is_admin") == True
        
        print(f"✓ Admin users list: {len(users)} users")
    
    def test_normal_user_cannot_access_users_list(self, carlos_client):
        """Normal user cannot access admin users list"""
        response = carlos_client.get(f"{BASE_URL}/api/admin/usuarios")
        assert response.status_code == 403
        print("✓ Normal user correctly blocked from admin users list")
    
    def test_admin_delete_user(self, admin_client, api_client):
        """6. Admin can delete a non-admin user"""
        # First create a test user to delete
        unique_email = f"TEST_todelete_{int(time.time())}@test.com"
        response = api_client.post(f"{BASE_URL}/api/auth/register", json={
            "name": "Test To Delete",
            "email": unique_email,
            "password": "testpass123"
        })
        assert response.status_code == 200
        test_user_id = response.json()["user"]["id"]
        
        # Admin deletes the user
        response = admin_client.delete(f"{BASE_URL}/api/admin/usuarios/{test_user_id}")
        assert response.status_code == 200
        assert "eliminado" in response.json().get("message", "").lower()
        
        # Verify user is gone
        response = admin_client.get(f"{BASE_URL}/api/admin/usuarios")
        users = response.json()
        deleted_user = next((u for u in users if u["id"] == test_user_id), None)
        assert deleted_user is None
        
        print(f"✓ Admin deleted user: {unique_email}")
    
    def test_admin_cannot_delete_admin_user(self, admin_client, admin_login):
        """Admin cannot delete another admin user"""
        admin_id = admin_login["user"]["id"]
        response = admin_client.delete(f"{BASE_URL}/api/admin/usuarios/{admin_id}")
        assert response.status_code == 400
        assert "administrador" in response.json().get("detail", "").lower()
        print("✓ Admin cannot delete admin users")


# ============== ADMIN AUCTIONS MANAGEMENT ==============
class TestAdminAuctionsManagement:
    """Admin auctions management tests"""
    
    def test_admin_list_auctions(self, admin_client):
        """4. Admin panel - Subastas tab shows all auctions"""
        response = admin_client.get(f"{BASE_URL}/api/admin/subastas")
        assert response.status_code == 200
        auctions = response.json()
        
        assert isinstance(auctions, list)
        assert len(auctions) > 0
        
        # Verify auction structure
        auction = auctions[0]
        required_fields = ["id", "title", "seller_name", "current_price", "bid_count", "status"]
        for field in required_fields:
            assert field in auction, f"Missing auction field: {field}"
        
        print(f"✓ Admin auctions list: {len(auctions)} auctions")
        for a in auctions[:3]:
            print(f"  - {a['title']} by {a['seller_name']} - {a['current_price']}€ ({a['status']})")
    
    def test_normal_user_cannot_access_auctions_list(self, carlos_client):
        """Normal user cannot access admin auctions list"""
        response = carlos_client.get(f"{BASE_URL}/api/admin/subastas")
        assert response.status_code == 403
        print("✓ Normal user correctly blocked from admin auctions list")
    
    def test_admin_delete_auction(self, admin_client, carlos_client):
        """5. Admin can delete any auction"""
        # Create a test auction to delete
        response = carlos_client.post(f"{BASE_URL}/api/subastas", json={
            "title": "TEST_Admin_Delete_Me",
            "description": "Test auction for admin deletion",
            "starting_price": 5.0,
            "duration": "7d",
            "category": "Otros",
            "location": "Madrid",
            "delivery_type": "pickup",
            "images": ["https://example.com/img.jpg"]
        })
        assert response.status_code == 200
        test_auction_id = response.json()["id"]
        
        # Admin deletes the auction
        response = admin_client.delete(f"{BASE_URL}/api/admin/subastas/{test_auction_id}")
        assert response.status_code == 200
        assert "eliminada" in response.json().get("message", "").lower()
        
        # Verify auction is gone
        response = admin_client.get(f"{BASE_URL}/api/subastas/{test_auction_id}")
        assert response.status_code == 404
        
        print(f"✓ Admin deleted auction: TEST_Admin_Delete_Me")


# ============== RATING SYSTEM TESTS ==============
class TestRatingSystem:
    """Rating system endpoint tests"""
    
    def test_buy_now_to_create_finished_auction(self, carlos_client, carlos_login, maria_client, maria_login):
        """Setup: Use Buy Now to finish an auction for rating tests"""
        # Find Maria's auction with buy_now_price that Carlos can buy
        response = carlos_client.get(f"{BASE_URL}/api/subastas")
        auctions = response.json()
        
        carlos_id = carlos_login["user"]["id"]
        maria_id = maria_login["user"]["id"]
        
        maria_buy_now_auction = None
        for a in auctions:
            if a["seller_id"] == maria_id and a.get("buy_now_price") and a["status"] == "active":
                maria_buy_now_auction = a
                break
        
        if not maria_buy_now_auction:
            pytest.skip("No Maria auction with buy_now available")
        
        # Carlos buys the auction
        response = carlos_client.post(f"{BASE_URL}/api/subastas/{maria_buy_now_auction['id']}/comprar-ya")
        assert response.status_code == 200
        finished_auction = response.json()
        assert finished_auction["status"] == "finished"
        assert finished_auction["winner_id"] == carlos_id
        
        print(f"✓ Carlos bought '{maria_buy_now_auction['title']}' for {maria_buy_now_auction['buy_now_price']}€")
        print(f"  Auction ID: {finished_auction['id']}")
        return finished_auction
    
    def test_create_rating_as_buyer(self, carlos_client, maria_login, api_client):
        """8. POST /api/valoraciones creates a rating (buyer rates seller)"""
        # First find a finished auction where Carlos is the winner
        response = carlos_client.get(f"{BASE_URL}/api/subastas?status=finished")
        auctions = response.json()
        
        maria_id = maria_login["user"]["id"]
        finished_auction = None
        for a in auctions:
            if a.get("winner_id") and a["seller_id"] == maria_id:
                finished_auction = a
                break
        
        if not finished_auction:
            # Use Buy Now to create one
            response = carlos_client.get(f"{BASE_URL}/api/subastas")
            active_auctions = response.json()
            for a in active_auctions:
                if a["seller_id"] == maria_id and a.get("buy_now_price") and a["status"] == "active":
                    response = carlos_client.post(f"{BASE_URL}/api/subastas/{a['id']}/comprar-ya")
                    if response.status_code == 200:
                        finished_auction = response.json()
                        break
        
        if not finished_auction:
            pytest.skip("No finished auction available for rating test")
        
        # Carlos (buyer/winner) rates Maria (seller)
        response = carlos_client.post(f"{BASE_URL}/api/valoraciones", json={
            "auction_id": finished_auction["id"],
            "rated_user_id": finished_auction["seller_id"],
            "rating": 5,
            "comment": "Excellent seller! Fast shipping."
        })
        
        # May get 400 if already rated
        if response.status_code == 400 and "ya has valorado" in response.json().get("detail", "").lower():
            print("✓ Rating already exists (duplicate prevention working)")
            return
        
        assert response.status_code == 200, f"Rating creation failed: {response.text}"
        rating = response.json()
        assert rating["rating"] == 5
        assert "id" in rating
        print(f"✓ Rating created: 5 stars for seller on auction '{finished_auction['title']}'")
    
    def test_get_user_ratings(self, api_client, maria_login):
        """9. GET /api/valoraciones/usuario/{id} returns user ratings"""
        maria_id = maria_login["user"]["id"]
        response = api_client.get(f"{BASE_URL}/api/valoraciones/usuario/{maria_id}")
        assert response.status_code == 200
        data = response.json()
        
        assert "ratings" in data
        assert "average" in data
        assert "count" in data
        assert isinstance(data["ratings"], list)
        
        print(f"✓ User ratings endpoint works - Maria: {data['count']} ratings, avg: {data['average']}")
    
    def test_get_auction_ratings(self, carlos_client, maria_login, api_client):
        """10. GET /api/valoraciones/subasta/{id} returns auction ratings"""
        # Find a finished auction
        response = carlos_client.get(f"{BASE_URL}/api/subastas?status=finished")
        auctions = response.json()
        
        if not auctions:
            pytest.skip("No finished auctions for rating test")
        
        auction_id = auctions[0]["id"]
        response = carlos_client.get(f"{BASE_URL}/api/valoraciones/subasta/{auction_id}")
        assert response.status_code == 200
        data = response.json()
        
        assert "ratings" in data
        assert "my_ratings" in data
        assert isinstance(data["ratings"], list)
        
        print(f"✓ Auction ratings endpoint works - {len(data['ratings'])} ratings")
    
    def test_duplicate_rating_prevention(self, carlos_client, maria_login):
        """11. Duplicate rating prevention (same rater+auction)"""
        # Find a finished auction Carlos can rate
        response = carlos_client.get(f"{BASE_URL}/api/subastas?status=finished")
        auctions = response.json()
        
        maria_id = maria_login["user"]["id"]
        finished_auction = None
        for a in auctions:
            if a.get("winner_id") and a["seller_id"] == maria_id:
                finished_auction = a
                break
        
        if not finished_auction:
            pytest.skip("No finished auction for duplicate rating test")
        
        # Try to rate same auction twice
        rating_data = {
            "auction_id": finished_auction["id"],
            "rated_user_id": finished_auction["seller_id"],
            "rating": 4,
            "comment": "Duplicate attempt"
        }
        
        # First attempt
        response = carlos_client.post(f"{BASE_URL}/api/valoraciones", json=rating_data)
        
        # Second attempt (should fail with 400)
        response2 = carlos_client.post(f"{BASE_URL}/api/valoraciones", json=rating_data)
        assert response2.status_code == 400
        assert "ya has valorado" in response2.json().get("detail", "").lower()
        
        print("✓ Duplicate rating correctly prevented")
    
    def test_only_buyer_seller_can_rate(self, api_client, carlos_login, maria_login):
        """12. Only buyer/seller can rate on their transaction"""
        # Create a new user who is not involved in any transaction
        unique_email = f"TEST_outsider_{int(time.time())}@test.com"
        response = api_client.post(f"{BASE_URL}/api/auth/register", json={
            "name": "Test Outsider",
            "email": unique_email,
            "password": "testpass123"
        })
        assert response.status_code == 200
        outsider_token = response.json()["token"]
        
        outsider_client = requests.Session()
        outsider_client.headers.update({
            "Content-Type": "application/json",
            "Authorization": f"Bearer {outsider_token}"
        })
        
        # Find a finished auction
        response = api_client.get(f"{BASE_URL}/api/subastas?status=finished")
        auctions = response.json()
        
        if not auctions:
            pytest.skip("No finished auctions")
        
        finished_auction = auctions[0]
        
        # Outsider tries to rate
        response = outsider_client.post(f"{BASE_URL}/api/valoraciones", json={
            "auction_id": finished_auction["id"],
            "rated_user_id": finished_auction["seller_id"],
            "rating": 1,
            "comment": "I shouldn't be able to rate this"
        })
        assert response.status_code == 403
        
        print("✓ Only buyer/seller can rate - outsiders correctly blocked")
    
    def test_cannot_rate_self(self, carlos_client, carlos_login):
        """Cannot rate yourself"""
        carlos_id = carlos_login["user"]["id"]
        
        # Find any finished auction
        response = carlos_client.get(f"{BASE_URL}/api/subastas?status=finished")
        auctions = response.json()
        
        if not auctions:
            pytest.skip("No finished auctions")
        
        response = carlos_client.post(f"{BASE_URL}/api/valoraciones", json={
            "auction_id": auctions[0]["id"],
            "rated_user_id": carlos_id,  # Trying to rate self
            "rating": 5,
            "comment": "Self rating attempt"
        })
        # Should fail with 400 or 403
        assert response.status_code in [400, 403]
        print("✓ Self-rating correctly prevented")
    
    def test_rating_must_be_1_to_5(self, carlos_client, maria_login):
        """Rating value must be between 1 and 5"""
        # Find a finished auction
        response = carlos_client.get(f"{BASE_URL}/api/subastas?status=finished")
        auctions = response.json()
        
        maria_id = maria_login["user"]["id"]
        finished_auction = None
        for a in auctions:
            if a.get("winner_id") and a["seller_id"] == maria_id:
                finished_auction = a
                break
        
        if not finished_auction:
            pytest.skip("No suitable auction for rating validation test")
        
        # Try invalid ratings
        for invalid_rating in [0, 6, -1]:
            response = carlos_client.post(f"{BASE_URL}/api/valoraciones", json={
                "auction_id": finished_auction["id"],
                "rated_user_id": finished_auction["seller_id"],
                "rating": invalid_rating,
                "comment": "Invalid rating test"
            })
            assert response.status_code == 400, f"Should reject rating {invalid_rating}"
        
        print("✓ Invalid rating values (0, 6, -1) correctly rejected")


# ============== SELLER RATING ON AUCTION CARDS ==============
class TestSellerRatingDisplay:
    """Test that seller rating is included in auction responses"""
    
    def test_auction_list_includes_seller_rating(self, api_client):
        """13/15. Auction cards show seller rating if > 0"""
        response = api_client.get(f"{BASE_URL}/api/subastas")
        assert response.status_code == 200
        auctions = response.json()
        
        # Check that seller_rating fields exist
        for auction in auctions[:5]:
            assert "seller_rating_avg" in auction, "Missing seller_rating_avg"
            assert "seller_rating_count" in auction, "Missing seller_rating_count"
        
        print("✓ Auction list includes seller_rating_avg and seller_rating_count")
    
    def test_auction_detail_includes_seller_rating(self, api_client):
        """13. AuctionDetailPage - seller rating in sidebar"""
        response = api_client.get(f"{BASE_URL}/api/subastas")
        auctions = response.json()
        auction_id = auctions[0]["id"]
        
        response = api_client.get(f"{BASE_URL}/api/subastas/{auction_id}")
        assert response.status_code == 200
        auction = response.json()
        
        assert "seller_rating_avg" in auction
        assert "seller_rating_count" in auction
        
        print(f"✓ Auction detail includes seller rating: {auction['seller_rating_avg']} ({auction['seller_rating_count']} ratings)")


# ============== PROFILE RATING DISPLAY ==============
class TestProfileRatingDisplay:
    """Test that profile shows rating information"""
    
    def test_profile_includes_rating(self, carlos_client, carlos_login):
        """14. ProfilePage - rating display in header and Valoraciones tab"""
        carlos_id = carlos_login["user"]["id"]
        response = carlos_client.get(f"{BASE_URL}/api/usuarios/{carlos_id}")
        assert response.status_code == 200
        profile = response.json()
        
        assert "rating_avg" in profile, "Missing rating_avg in profile"
        assert "rating_count" in profile, "Missing rating_count in profile"
        assert "ratings" in profile, "Missing ratings list in profile"
        assert isinstance(profile["ratings"], list)
        
        print(f"✓ Profile includes rating: {profile['rating_avg']} ({profile['rating_count']} ratings)")
        print(f"  - Ratings list has {len(profile['ratings'])} items")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
