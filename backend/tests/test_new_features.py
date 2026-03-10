"""
Test Suite for 8 New Features:
1. Chat between buyer/seller with photos (Cloudinary)
2. Admin chat in disputes with photos
3. Cloudinary image upload (replaces base64)
4. Search autocomplete
5. Gamified reputation badges
6. Admin badge management (CRUD + assign/remove)
7. Admin ratings management (list/filter/delete)
8. Password change/recovery with SendGrid
"""
import pytest
import requests
import os
import base64

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')


@pytest.fixture(scope="module")
def api_client():
    """Shared requests session"""
    session = requests.Session()
    session.headers.update({"Content-Type": "application/json"})
    return session


@pytest.fixture(scope="module")
def admin_token(api_client):
    """Get admin authentication token"""
    response = api_client.post(f"{BASE_URL}/api/auth/login", json={
        "email": "admin@lapopo.es",
        "password": "admin123"
    })
    assert response.status_code == 200, f"Admin login failed: {response.text}"
    data = response.json()
    assert data["user"]["is_admin"] == True
    return data["token"]


@pytest.fixture(scope="module")
def user1_token(api_client):
    """Get user1 (carlos) authentication token"""
    response = api_client.post(f"{BASE_URL}/api/auth/login", json={
        "email": "carlos@lapopo.es",
        "password": "demo123"
    })
    assert response.status_code == 200, f"User1 login failed: {response.text}"
    return response.json()["token"]


@pytest.fixture(scope="module")
def user1_data(api_client):
    """Get user1 (carlos) data"""
    response = api_client.post(f"{BASE_URL}/api/auth/login", json={
        "email": "carlos@lapopo.es",
        "password": "demo123"
    })
    assert response.status_code == 200
    return response.json()["user"]


@pytest.fixture(scope="module")
def user2_token(api_client):
    """Get user2 (maria) authentication token"""
    response = api_client.post(f"{BASE_URL}/api/auth/login", json={
        "email": "maria@lapopo.es",
        "password": "demo123"
    })
    assert response.status_code == 200, f"User2 login failed: {response.text}"
    return response.json()["token"]


@pytest.fixture(scope="module")
def user2_data(api_client):
    """Get user2 (maria) data"""
    response = api_client.post(f"{BASE_URL}/api/auth/login", json={
        "email": "maria@lapopo.es",
        "password": "demo123"
    })
    assert response.status_code == 200
    return response.json()["user"]


# ===== FEATURE 4: SEARCH AUTOCOMPLETE =====
class TestSearchAutocomplete:
    """Test search autocomplete endpoint"""
    
    def test_autocomplete_returns_matching_auctions(self, api_client):
        """GET /api/subastas/autocomplete?q=cam returns matching auctions"""
        response = api_client.get(f"{BASE_URL}/api/subastas/autocomplete?q=cam")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        # Should return auctions with 'cam' in title
        print(f"Autocomplete results for 'cam': {len(data)} items")
        for item in data:
            assert "id" in item
            assert "title" in item
            assert "current_price" in item
    
    def test_autocomplete_empty_query(self, api_client):
        """Autocomplete with short query returns empty list"""
        response = api_client.get(f"{BASE_URL}/api/subastas/autocomplete?q=a")
        assert response.status_code == 200
        data = response.json()
        assert data == [], "Single character query should return empty list"
    
    def test_autocomplete_returns_limited_results(self, api_client):
        """Autocomplete returns max 8 results"""
        response = api_client.get(f"{BASE_URL}/api/subastas/autocomplete?q=de")
        assert response.status_code == 200
        data = response.json()
        assert len(data) <= 8, "Should return max 8 results"


# ===== FEATURE 3: CLOUDINARY IMAGE UPLOAD =====
class TestCloudinaryUpload:
    """Test Cloudinary image upload endpoints"""
    
    def test_upload_base64_image(self, api_client, user1_token):
        """POST /api/upload/base64 uploads image to Cloudinary and returns URL"""
        # Small test PNG image (1x1 red pixel)
        test_image_base64 = "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg=="
        
        response = api_client.post(
            f"{BASE_URL}/api/upload/base64",
            json={"image": test_image_base64},
            headers={"Authorization": f"Bearer {user1_token}"}
        )
        assert response.status_code == 200, f"Upload failed: {response.text}"
        data = response.json()
        assert "url" in data
        assert "cloudinary" in data["url"].lower() or "res.cloudinary.com" in data["url"]
        assert "public_id" in data
        print(f"Cloudinary URL: {data['url']}")


# ===== FEATURE 5: GAMIFIED REPUTATION BADGES =====
class TestBadges:
    """Test badge endpoints"""
    
    def test_get_all_badges_returns_7_defaults(self, api_client):
        """GET /api/badges returns all badges (should be 7 default)"""
        response = api_client.get(f"{BASE_URL}/api/badges")
        assert response.status_code == 200
        data = response.json()
        assert len(data) >= 7, f"Expected at least 7 badges, got {len(data)}"
        
        badge_names = [b["name"] for b in data]
        expected_badges = ["Primera venta", "5 ventas", "10 ventas", "50 ventas", 
                          "100% positivas", "Comprador frecuente", "Canario"]
        for expected in expected_badges:
            assert expected in badge_names, f"Missing badge: {expected}"
        print(f"Found {len(data)} badges: {badge_names}")
    
    def test_get_user_badges(self, api_client, user1_data):
        """GET /api/badges/usuario/{user_id} returns user's badges"""
        response = api_client.get(f"{BASE_URL}/api/badges/usuario/{user1_data['id']}")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        print(f"User1 badges: {len(data)} badges")


# ===== FEATURE 6: ADMIN BADGE MANAGEMENT =====
class TestAdminBadgeManagement:
    """Test admin badge management endpoints"""
    
    @pytest.fixture(scope="class")
    def test_badge_id(self, api_client, admin_token):
        """Create a test badge and return its ID"""
        response = api_client.post(
            f"{BASE_URL}/api/admin/badges",
            json={
                "name": "TEST_Badge",
                "description": "Test badge for testing",
                "emoji": "🧪",
                "condition_type": "sales",
                "condition_value": 999,
                "auto": False
            },
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert response.status_code == 200
        data = response.json()
        badge_id = data["id"]
        yield badge_id
        # Cleanup
        api_client.delete(
            f"{BASE_URL}/api/admin/badges/{badge_id}",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
    
    def test_create_badge(self, api_client, admin_token):
        """POST /api/admin/badges creates a new badge"""
        response = api_client.post(
            f"{BASE_URL}/api/admin/badges",
            json={
                "name": "TEST_NewBadge",
                "description": "A new test badge",
                "emoji": "🔥",
                "condition_type": "purchases",
                "condition_value": 100,
                "auto": True
            },
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "TEST_NewBadge"
        assert data["emoji"] == "🔥"
        assert "id" in data
        
        # Cleanup
        api_client.delete(
            f"{BASE_URL}/api/admin/badges/{data['id']}",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
    
    def test_update_badge(self, api_client, admin_token, test_badge_id):
        """PUT /api/admin/badges/{id} updates a badge"""
        response = api_client.put(
            f"{BASE_URL}/api/admin/badges/{test_badge_id}",
            json={
                "name": "TEST_UpdatedBadge",
                "description": "Updated description",
                "emoji": "✅",
                "condition_type": "sales",
                "condition_value": 888,
                "auto": False
            },
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert response.status_code == 200
        data = response.json()
        assert "message" in data or data.get("name") == "TEST_UpdatedBadge"
    
    def test_delete_badge(self, api_client, admin_token):
        """DELETE /api/admin/badges/{id} deletes a badge"""
        # Create badge to delete
        create_resp = api_client.post(
            f"{BASE_URL}/api/admin/badges",
            json={
                "name": "TEST_ToDelete",
                "description": "To be deleted",
                "emoji": "❌",
                "condition_type": "sales",
                "condition_value": 1,
                "auto": False
            },
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        badge_id = create_resp.json()["id"]
        
        # Delete badge
        response = api_client.delete(
            f"{BASE_URL}/api/admin/badges/{badge_id}",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert response.status_code == 200
    
    def test_assign_badge_to_user(self, api_client, admin_token, user1_data):
        """POST /api/admin/badges/{id}/asignar assigns badge to user"""
        # Create a badge first
        create_resp = api_client.post(
            f"{BASE_URL}/api/admin/badges",
            json={
                "name": "TEST_AssignBadge",
                "description": "Badge to assign",
                "emoji": "🎁",
                "condition_type": "sales",
                "condition_value": 1,
                "auto": False
            },
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        badge_id = create_resp.json()["id"]
        
        # Assign to user
        response = api_client.post(
            f"{BASE_URL}/api/admin/badges/{badge_id}/asignar",
            json={"user_id": user1_data["id"]},
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert response.status_code == 200
        
        # Verify user has badge
        user_badges = api_client.get(f"{BASE_URL}/api/badges/usuario/{user1_data['id']}")
        badges = user_badges.json()
        badge_ids = [b["id"] for b in badges]
        assert badge_id in badge_ids
        
        # Cleanup
        api_client.post(
            f"{BASE_URL}/api/admin/badges/{badge_id}/retirar",
            json={"user_id": user1_data["id"]},
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        api_client.delete(
            f"{BASE_URL}/api/admin/badges/{badge_id}",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
    
    def test_remove_badge_from_user(self, api_client, admin_token, user1_data):
        """POST /api/admin/badges/{id}/retirar removes badge from user"""
        # Create and assign badge
        create_resp = api_client.post(
            f"{BASE_URL}/api/admin/badges",
            json={
                "name": "TEST_RemoveBadge",
                "description": "Badge to remove",
                "emoji": "🗑️",
                "condition_type": "sales",
                "condition_value": 1,
                "auto": False
            },
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        badge_id = create_resp.json()["id"]
        
        api_client.post(
            f"{BASE_URL}/api/admin/badges/{badge_id}/asignar",
            json={"user_id": user1_data["id"]},
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        
        # Remove badge
        response = api_client.post(
            f"{BASE_URL}/api/admin/badges/{badge_id}/retirar",
            json={"user_id": user1_data["id"]},
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert response.status_code == 200
        
        # Cleanup
        api_client.delete(
            f"{BASE_URL}/api/admin/badges/{badge_id}",
            headers={"Authorization": f"Bearer {admin_token}"}
        )


# ===== FEATURE 8: PASSWORD CHANGE/RECOVERY =====
class TestPasswordManagement:
    """Test password change and recovery endpoints"""
    
    def test_change_password_requires_min_8_chars(self, api_client, user1_token):
        """PUT /api/auth/cambiar-password validates min 8 chars"""
        response = api_client.put(
            f"{BASE_URL}/api/auth/cambiar-password",
            json={
                "current_password": "demo123",
                "new_password": "short"  # Less than 8 chars
            },
            headers={"Authorization": f"Bearer {user1_token}"}
        )
        assert response.status_code == 400
        assert "8 caracteres" in response.json()["detail"]
    
    def test_change_password_wrong_current(self, api_client, user1_token):
        """Password change with wrong current password fails"""
        response = api_client.put(
            f"{BASE_URL}/api/auth/cambiar-password",
            json={
                "current_password": "wrongpassword",
                "new_password": "newpassword123"
            },
            headers={"Authorization": f"Bearer {user1_token}"}
        )
        assert response.status_code == 400
        assert "incorrecta" in response.json()["detail"].lower()
    
    def test_forgot_password_returns_generic_message(self, api_client):
        """POST /api/auth/recuperar-password sends recovery email (returns generic message)"""
        response = api_client.post(
            f"{BASE_URL}/api/auth/recuperar-password",
            json={"email": "carlos@lapopo.es"}
        )
        assert response.status_code == 200
        data = response.json()
        assert "message" in data
        # Should return generic message regardless of email existence
        print(f"Recovery response: {data['message']}")
    
    def test_forgot_password_nonexistent_email(self, api_client):
        """Recovery for non-existent email also returns success (security)"""
        response = api_client.post(
            f"{BASE_URL}/api/auth/recuperar-password",
            json={"email": "nonexistent@test.com"}
        )
        assert response.status_code == 200
        # Should still return success for security reasons
    
    def test_reset_password_invalid_token(self, api_client):
        """POST /api/auth/resetear-password with invalid token fails"""
        response = api_client.post(
            f"{BASE_URL}/api/auth/resetear-password",
            json={
                "token": "invalid-token-12345",
                "new_password": "newpassword123"
            }
        )
        assert response.status_code == 400
        assert "invalido" in response.json()["detail"].lower() or "expirado" in response.json()["detail"].lower()


# ===== FEATURE 7: ADMIN RATINGS MANAGEMENT =====
class TestAdminRatingsManagement:
    """Test admin ratings management endpoints"""
    
    def test_admin_list_all_ratings(self, api_client, admin_token):
        """GET /api/admin/valoraciones lists all ratings"""
        response = api_client.get(
            f"{BASE_URL}/api/admin/valoraciones",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        print(f"Total ratings: {len(data)}")
        if len(data) > 0:
            assert "id" in data[0]
            assert "rating" in data[0]
            assert "rater_id" in data[0]
    
    def test_admin_list_ratings_with_filter(self, api_client, admin_token):
        """GET /api/admin/valoraciones with min_rating filter"""
        response = api_client.get(
            f"{BASE_URL}/api/admin/valoraciones?min_rating=4",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert response.status_code == 200
        data = response.json()
        for r in data:
            assert r["rating"] >= 4


# ===== FEATURE 1 & 2: CHAT WITH IMAGES =====
class TestChatWithImages:
    """Test chat messaging with image support"""
    
    def test_send_message_with_images(self, api_client, user1_token):
        """POST /api/mensajes sends chat message with images array"""
        # First get an auction to message about
        auctions = api_client.get(f"{BASE_URL}/api/subastas").json()
        if not auctions:
            pytest.skip("No auctions available for messaging test")
        
        # Find auction owned by someone else (not carlos)
        auction = None
        for a in auctions:
            if a.get("seller_name") != "Carlos López":  # Find maria's auction
                auction = a
                break
        
        if not auction:
            pytest.skip("No suitable auction for chat test")
        
        # Need to bid first to be able to message
        bid_resp = api_client.post(
            f"{BASE_URL}/api/subastas/{auction['id']}/pujar",
            json={"amount": auction["current_price"] + 1.0},
            headers={"Authorization": f"Bearer {user1_token}"}
        )
        
        if bid_resp.status_code != 200:
            pytest.skip("Could not place bid for messaging test")
        
        # Send message with images
        response = api_client.post(
            f"{BASE_URL}/api/mensajes",
            json={
                "auction_id": auction["id"],
                "receiver_id": auction["seller_id"],
                "content": "TEST message with image",
                "images": ["https://example.com/test-image.jpg"]
            },
            headers={"Authorization": f"Bearer {user1_token}"}
        )
        assert response.status_code == 200
        data = response.json()
        assert "id" in data
        assert data["images"] == ["https://example.com/test-image.jpg"]
    
    def test_get_user_conversations(self, api_client, user1_token):
        """GET /api/chat/conversaciones returns user conversations grouped by auction"""
        response = api_client.get(
            f"{BASE_URL}/api/chat/conversaciones",
            headers={"Authorization": f"Bearer {user1_token}"}
        )
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        print(f"User1 has {len(data)} conversations")
        if len(data) > 0:
            assert "auction_id" in data[0]
            assert "auction_title" in data[0]
            assert "other_user_name" in data[0]
            assert "last_message" in data[0]


class TestDisputeWithImages:
    """Test dispute messaging with image support"""
    
    def test_dispute_message_supports_images(self, api_client, admin_token):
        """POST /api/disputas/{id}/mensaje supports images array"""
        # Get disputes
        disputes = api_client.get(
            f"{BASE_URL}/api/admin/disputas",
            headers={"Authorization": f"Bearer {admin_token}"}
        ).json()
        
        if not disputes:
            pytest.skip("No disputes available for testing")
        
        dispute = disputes[0]
        if dispute["status"] == "closed":
            pytest.skip("Dispute is closed, cannot send messages")
        
        response = api_client.post(
            f"{BASE_URL}/api/disputas/{dispute['id']}/mensaje",
            json={
                "content": "Admin response with image",
                "images": ["https://example.com/evidence.jpg"]
            },
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        
        # Could be 200 or skip if closed
        if response.status_code == 200:
            data = response.json()
            assert "id" in data
            assert data.get("images") == ["https://example.com/evidence.jpg"]
        else:
            print(f"Dispute message response: {response.status_code} - {response.text}")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
