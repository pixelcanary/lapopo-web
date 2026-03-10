import requests
import sys
import json
from datetime import datetime

class LapopoAPITester:
    def __init__(self, base_url="https://bidding-marketplace-6.preview.emergentagent.com"):
        self.base_url = base_url
        self.token = None
        self.user_id = None
        self.tests_run = 0
        self.tests_passed = 0
        
    def run_test(self, name, method, endpoint, expected_status, data=None, params=None):
        """Run a single API test"""
        url = f"{self.base_url}/api/{endpoint}"
        headers = {'Content-Type': 'application/json'}
        if self.token:
            headers['Authorization'] = f'Bearer {self.token}'

        self.tests_run += 1
        print(f"\n🔍 Testing {name}...")
        print(f"   URL: {method} {url}")
        if params:
            print(f"   Params: {params}")
        if data:
            print(f"   Data: {json.dumps(data, indent=2)}")
        
        try:
            if method == 'GET':
                response = requests.get(url, headers=headers, params=params, timeout=10)
            elif method == 'POST':
                response = requests.post(url, json=data, headers=headers, timeout=10)
            elif method == 'PUT':
                response = requests.put(url, json=data, headers=headers, timeout=10)

            print(f"   Response Status: {response.status_code}")
            
            success = response.status_code == expected_status
            if success:
                self.tests_passed += 1
                print(f"✅ PASSED - Status: {response.status_code}")
            else:
                print(f"❌ FAILED - Expected {expected_status}, got {response.status_code}")
                if response.text:
                    print(f"   Response: {response.text[:200]}...")

            return success, response.json() if response.headers.get('content-type', '').startswith('application/json') else {"text": response.text}

        except Exception as e:
            print(f"❌ FAILED - Error: {str(e)}")
            return False, {"error": str(e)}

    def test_login(self, email, password):
        """Test login with demo credentials"""
        success, response = self.run_test(
            "Login with demo credentials",
            "POST", 
            "auth/login",
            200,
            data={"email": email, "password": password}
        )
        if success and 'token' in response:
            self.token = response['token']
            self.user_id = response['user']['id']
            print(f"   🎫 Token obtained for user: {response['user']['name']}")
            return True
        return False

    def test_register(self):
        """Test user registration"""
        timestamp = datetime.now().strftime('%H%M%S')
        test_user = {
            "name": f"Test User {timestamp}",
            "email": f"test{timestamp}@lapopo.es",
            "password": "testpass123"
        }
        success, response = self.run_test(
            "Register new user",
            "POST",
            "auth/register", 
            200,
            data=test_user
        )
        if success and 'token' in response:
            print(f"   👤 New user created: {response['user']['name']}")
        return success

    def test_get_auctions(self):
        """Test GET /api/subastas - list all auctions"""
        success, response = self.run_test(
            "Get all auctions",
            "GET",
            "subastas",
            200
        )
        if success and isinstance(response, list):
            print(f"   📦 Found {len(response)} auctions")
            if len(response) >= 12:
                print(f"   ✅ Expected 12+ seed auctions, found {len(response)}")
            else:
                print(f"   ⚠️  Expected 12+ auctions, only found {len(response)}")
            return len(response) >= 10  # Allow some flexibility
        return success

    def test_search_auctions(self):
        """Test search functionality"""
        success, response = self.run_test(
            "Search auctions (electrónica)",
            "GET",
            "subastas",
            200,
            params={"search": "iPhone"}
        )
        if success and isinstance(response, list):
            print(f"   🔍 Search returned {len(response)} results")
        return success

    def test_filter_auctions(self):
        """Test filtering by category and canarias"""
        # Test category filter
        success1, response1 = self.run_test(
            "Filter by Electrónica category",
            "GET",
            "subastas", 
            200,
            params={"category": "Electrónica"}
        )
        
        # Test Canarias filter
        success2, response2 = self.run_test(
            "Filter Canarias auctions",
            "GET",
            "subastas",
            200, 
            params={"canarias": True}
        )
        
        if success1 and isinstance(response1, list):
            print(f"   📱 Electronics: {len(response1)} items")
        if success2 and isinstance(response2, list):
            print(f"   🏝️  Canarias: {len(response2)} items")
            
        return success1 and success2

    def test_auction_detail(self):
        """Test getting auction details"""
        # First get auctions list to get an ID
        _, auctions = self.run_test("Get auctions for detail test", "GET", "subastas", 200)
        if isinstance(auctions, list) and len(auctions) > 0:
            auction_id = auctions[0]['id']
            success, response = self.run_test(
                f"Get auction detail",
                "GET",
                f"subastas/{auction_id}",
                200
            )
            if success and 'id' in response:
                print(f"   📄 Auction: {response.get('title', 'N/A')}")
                print(f"   💰 Price: €{response.get('current_price', 0)}")
                print(f"   🔨 Bids: {response.get('bid_count', 0)}")
            return success
        return False

    def test_create_auction(self):
        """Test creating an auction (requires auth)"""
        if not self.token:
            print("⚠️  Skipping auction creation - no auth token")
            return False
            
        auction_data = {
            "title": "Test Auction - MacBook Pro",
            "description": "Test auction created by automated testing. MacBook Pro 13 inch in excellent condition.",
            "starting_price": 500.0,
            "duration": "24h",
            "category": "Electrónica", 
            "location": "Madrid",
            "delivery_type": "both",
            "images": ["https://images.unsplash.com/photo-1517336714731-489689fd1ca8?auto=format&fit=crop&q=80&w=600"]
        }
        
        success, response = self.run_test(
            "Create new auction",
            "POST",
            "subastas",
            200,
            data=auction_data
        )
        
        if success and 'id' in response:
            print(f"   🎯 Created auction: {response['id']}")
            print(f"   📝 Title: {response['title']}")
            return response['id']  # Return auction ID for bidding test
        return False

    def test_bidding(self, auction_id=None):
        """Test placing a bid"""
        if not self.token:
            print("⚠️  Skipping bidding test - no auth token")
            return False
            
        # Get an auction to bid on if none provided
        if not auction_id:
            _, auctions = self.run_test("Get auctions for bidding test", "GET", "subastas", 200)
            if isinstance(auctions, list) and len(auctions) > 0:
                # Find an auction not owned by current user
                for auction in auctions:
                    if auction.get('seller_id') != self.user_id and auction.get('status') == 'active':
                        auction_id = auction['id']
                        current_price = auction.get('current_price', 1.0)
                        break
                        
        if not auction_id:
            print("⚠️  No suitable auction found for bidding test")
            return False
            
        # Get current price 
        _, auction_detail = self.run_test("Get auction for bid amount", "GET", f"subastas/{auction_id}", 200)
        if 'current_price' in auction_detail:
            min_bid = auction_detail['current_price'] + 0.50
            
            success, response = self.run_test(
                f"Place bid on auction {auction_id[:8]}...",
                "POST",
                f"subastas/{auction_id}/pujar",
                200,
                data={"amount": min_bid}
            )
            
            if success and 'current_price' in response:
                print(f"   💰 New price: €{response['current_price']}")
                print(f"   🔨 Total bids: {response.get('bid_count', 0)}")
            return success
            
        return False

    def test_profile_endpoints(self):
        """Test user profile endpoints"""
        if not self.token or not self.user_id:
            print("⚠️  Skipping profile test - no auth")
            return False
            
        # Get user profile
        success1, response1 = self.run_test(
            "Get user profile",
            "GET",
            f"usuarios/{self.user_id}",
            200
        )
        
        # Update user profile
        success2, response2 = self.run_test(
            "Update user name",
            "PUT", 
            f"usuarios/{self.user_id}",
            200,
            data={"name": "Carlos López Updated"}
        )
        
        if success1 and 'user' in response1:
            print(f"   👤 Profile: {response1['user'].get('name', 'N/A')}")
            print(f"   📧 Email: {response1['user'].get('email', 'N/A')}")
            print(f"   🏺 User auctions: {len(response1.get('auctions', []))}")
            print(f"   🔨 Active bids: {len(response1.get('active_bids', []))}")
            
        return success1 and success2

    def test_categories_and_locations(self):
        """Test helper endpoints"""
        success1, response1 = self.run_test(
            "Get categories",
            "GET",
            "categorias", 
            200
        )
        
        success2, response2 = self.run_test(
            "Get locations",
            "GET",
            "ubicaciones",
            200
        )
        
        if success1 and isinstance(response1, list):
            print(f"   📂 Categories: {len(response1)} found")
        if success2 and isinstance(response2, dict):
            peninsula_count = len(response2.get('peninsula', []))
            canarias_count = len(response2.get('canarias', []))
            print(f"   🗺️  Locations - Peninsula: {peninsula_count}, Canarias: {canarias_count}")
            
        return success1 and success2

    def run_full_test_suite(self):
        """Run comprehensive test suite"""
        print("🚀 Starting Lapopo API Test Suite")
        print("=" * 50)
        
        # Test 1: Demo user login
        print("\n📝 Testing Authentication...")
        login_success = self.test_login("carlos@lapopo.es", "demo123")
        
        # Test 2: Registration
        if login_success:
            # Logout first to test registration
            self.token = None
            self.user_id = None
        self.test_register()
        
        # Re-login for subsequent tests
        if not self.token:
            self.test_login("carlos@lapopo.es", "demo123")
        
        # Test 3: Basic auction operations
        print("\n🏺 Testing Auction Operations...")
        self.test_get_auctions()
        self.test_search_auctions()
        self.test_filter_auctions()
        self.test_auction_detail()
        
        # Test 4: Create auction (authenticated)
        print("\n🎯 Testing Auction Creation...")
        created_auction_id = self.test_create_auction()
        
        # Test 5: Bidding system
        print("\n💰 Testing Bidding System...")
        # Login as different user for bidding
        original_token = self.token
        original_user_id = self.user_id
        if self.test_login("maria@lapopo.es", "demo123"):
            self.test_bidding(created_auction_id if created_auction_id else None)
        # Restore original user
        self.token = original_token
        self.user_id = original_user_id
        
        # Test 6: Profile management
        print("\n👤 Testing Profile Management...")
        self.test_profile_endpoints()
        
        # Test 7: Helper endpoints
        print("\n🔧 Testing Helper Endpoints...")
        self.test_categories_and_locations()
        
        # Print final results
        print("\n" + "=" * 50)
        print("📊 TEST RESULTS")
        print(f"Tests Run: {self.tests_run}")
        print(f"Tests Passed: {self.tests_passed}")
        print(f"Success Rate: {(self.tests_passed/self.tests_run*100):.1f}%")
        
        if self.tests_passed == self.tests_run:
            print("🎉 ALL TESTS PASSED!")
            return 0
        else:
            failed = self.tests_run - self.tests_passed
            print(f"❌ {failed} TESTS FAILED")
            return 1

def main():
    tester = LapopoAPITester()
    return tester.run_full_test_suite()

if __name__ == "__main__":
    sys.exit(main())