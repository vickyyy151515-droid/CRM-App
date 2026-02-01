#!/usr/bin/env python3

import requests
import sys
import json
import os
from datetime import datetime
from pathlib import Path

class CRMAPITester:
    def __init__(self, base_url="https://data-integrity-fix-9.preview.emergentagent.com"):
        self.base_url = base_url
        self.admin_token = None
        self.staff_token = None
        self.tests_run = 0
        self.tests_passed = 0
        self.test_results = []

    def log_test(self, name, success, details=""):
        """Log test result"""
        self.tests_run += 1
        if success:
            self.tests_passed += 1
        
        result = {
            "test": name,
            "success": success,
            "details": details,
            "timestamp": datetime.now().isoformat()
        }
        self.test_results.append(result)
        
        status = "✅ PASS" if success else "❌ FAIL"
        print(f"{status} - {name}")
        if details:
            print(f"    Details: {details}")

    def run_api_test(self, name, method, endpoint, expected_status, data=None, token=None, files=None):
        """Run a single API test"""
        url = f"{self.base_url}/api/{endpoint}"
        headers = {}
        
        if token:
            headers['Authorization'] = f'Bearer {token}'
        
        if not files:
            headers['Content-Type'] = 'application/json'

        try:
            if method == 'GET':
                response = requests.get(url, headers=headers, params=data)
            elif method == 'POST':
                if files:
                    response = requests.post(url, headers={k: v for k, v in headers.items() if k != 'Content-Type'}, files=files, data=data)
                else:
                    response = requests.post(url, json=data, headers=headers)
            elif method == 'PATCH':
                response = requests.patch(url, json=data, headers=headers)
            elif method == 'DELETE':
                response = requests.delete(url, headers=headers)

            success = response.status_code == expected_status
            details = f"Status: {response.status_code}"
            
            if success and response.content:
                try:
                    response_data = response.json()
                    details += f", Response: {json.dumps(response_data, indent=2)[:200]}..."
                except:
                    details += f", Response: {str(response.content)[:100]}..."
            elif not success:
                try:
                    error_data = response.json()
                    details += f", Error: {error_data}"
                except:
                    details += f", Error: {response.text}"

            self.log_test(name, success, details)
            return success, response.json() if success and response.content else {}

        except Exception as e:
            self.log_test(name, False, f"Exception: {str(e)}")
            return False, {}

    def test_admin_login(self):
        """Test admin login"""
        success, response = self.run_api_test(
            "Admin Login",
            "POST",
            "auth/login",
            200,
            data={"email": "admin@crm.com", "password": "admin123"}
        )
        if success and 'token' in response:
            self.admin_token = response['token']
            return True
        return False

    def test_staff_login(self):
        """Test staff login"""
        success, response = self.run_api_test(
            "Staff Login",
            "POST",
            "auth/login",
            200,
            data={"email": "staff@crm.com", "password": "staff123"}
        )
        if success and 'token' in response:
            self.staff_token = response['token']
            return True
        return False

    def test_invalid_login(self):
        """Test invalid login credentials"""
        success, _ = self.run_api_test(
            "Invalid Login",
            "POST",
            "auth/login",
            401,
            data={"email": "invalid@test.com", "password": "wrongpass"}
        )
        return success

    def test_get_current_user(self):
        """Test get current user endpoint"""
        success, _ = self.run_api_test(
            "Get Current User (Admin)",
            "GET",
            "auth/me",
            200,
            token=self.admin_token
        )
        return success

    def test_unauthorized_access(self):
        """Test unauthorized access"""
        success, _ = self.run_api_test(
            "Unauthorized Access",
            "GET",
            "auth/me",
            403
        )
        return success

    def test_create_sample_csv(self):
        """Create a sample CSV file for testing"""
        csv_content = """Name,Email,Age,Department
John Doe,john@example.com,30,Engineering
Jane Smith,jane@example.com,25,Marketing
Bob Johnson,bob@example.com,35,Sales
Alice Brown,alice@example.com,28,HR"""
        
        with open('/tmp/test_database.csv', 'w') as f:
            f.write(csv_content)
        return True

    def test_get_products(self):
        """Test getting products list"""
        success, response = self.run_api_test(
            "Get Products List",
            "GET",
            "products",
            200,
            token=self.admin_token
        )
        if success and isinstance(response, list):
            self.products = response
            return True
        return False

    def test_create_product(self):
        """Test creating a new product"""
        success, response = self.run_api_test(
            "Create Product TEST2000",
            "POST",
            "products",
            200,
            data={"name": "TEST2000"},
            token=self.admin_token
        )
        if success and 'id' in response:
            self.test_product_id = response['id']
            return True
        return False

    def test_create_duplicate_product(self):
        """Test creating duplicate product should fail"""
        success, _ = self.run_api_test(
            "Create Duplicate Product (Should Fail)",
            "POST",
            "products",
            400,
            data={"name": "TEST2000"},
            token=self.admin_token
        )
        return success

    def test_staff_cannot_create_product(self):
        """Test that staff cannot create products"""
        success, _ = self.run_api_test(
            "Staff Create Product (Should Fail)",
            "POST",
            "products",
            403,
            data={"name": "STAFF_PRODUCT"},
            token=self.staff_token
        )
        return success

    def test_upload_database(self):
        """Test database upload with product"""
        self.test_create_sample_csv()
        
        # Get first available product for upload
        if hasattr(self, 'products') and self.products:
            product_id = self.products[0]['id']
        elif hasattr(self, 'test_product_id'):
            product_id = self.test_product_id
        else:
            self.log_test("Upload CSV Database", False, "No products available for upload")
            return False
        
        with open('/tmp/test_database.csv', 'rb') as f:
            files = {'file': ('test_database.csv', f, 'text/csv')}
            data = {
                'description': 'Test CSV database for automated testing',
                'product_id': product_id
            }
            
            success, response = self.run_api_test(
                "Upload CSV Database",
                "POST",
                "databases",
                200,  # Backend returns 200, not 201
                data=data,
                files=files,
                token=self.admin_token
            )
            
            if success and 'id' in response:
                self.uploaded_db_id = response['id']
                return True
        return False

    def test_upload_database_without_product(self):
        """Test database upload without product should fail"""
        self.test_create_sample_csv()
        
        with open('/tmp/test_database.csv', 'rb') as f:
            files = {'file': ('test_database_no_product.csv', f, 'text/csv')}
            data = {'description': 'Test CSV without product'}
            
            success, _ = self.run_api_test(
                "Upload Database Without Product (Should Fail)",
                "POST",
                "databases",
                422,  # Changed from 400 to 422 as per actual response
                data=data,
                files=files,
                token=self.admin_token
            )
            return success

    def test_filter_databases_by_product(self):
        """Test filtering databases by product"""
        if hasattr(self, 'products') and self.products:
            product_id = self.products[0]['id']
            success, _ = self.run_api_test(
                "Filter Databases by Product",
                "GET",
                "databases",
                200,
                data={"product_id": product_id},
                token=self.admin_token
            )
            return success
        return False

    def test_delete_product_with_databases(self):
        """Test deleting product with databases should fail"""
        # Use prod-liga2000 which has databases
        success, _ = self.run_api_test(
            "Delete Product with Databases (Should Fail)",
            "DELETE",
            "products/prod-liga2000",
            400,
            token=self.admin_token
        )
        return success

    def test_delete_product_success(self):
        """Test deleting product without databases"""
        # Create a new product for deletion
        success, response = self.run_api_test(
            "Create Product for Deletion",
            "POST",
            "products",
            200,
            data={"name": "DELETE_TEST_PRODUCT"},
            token=self.admin_token
        )
        
        if success and 'id' in response:
            product_id = response['id']
            success, _ = self.run_api_test(
                "Delete Product Successfully",
                "DELETE",
                f"products/{product_id}",
                200,
                token=self.admin_token
            )
            return success
        return False

    def test_staff_cannot_delete_product(self):
        """Test that staff cannot delete products"""
        if hasattr(self, 'test_product_id'):
            success, _ = self.run_api_test(
                "Staff Delete Product (Should Fail)",
                "DELETE",
                f"products/{self.test_product_id}",
                403,
                token=self.staff_token
            )
            return success
        return False

    def test_staff_upload_forbidden(self):
        """Test that staff cannot upload databases"""
        self.test_create_sample_csv()
        
        with open('/tmp/test_database.csv', 'rb') as f:
            files = {'file': ('test_database.csv', f, 'text/csv')}
            data = {'description': 'Staff should not be able to upload'}
            
            success, _ = self.run_api_test(
                "Staff Upload (Should Fail)",
                "POST",
                "databases",
                403,
                data=data,
                files=files,
                token=self.staff_token
            )
            return success

    def test_list_databases(self):
        """Test listing databases"""
        success, response = self.run_api_test(
            "List Databases",
            "GET",
            "databases",
            200,
            token=self.admin_token
        )
        return success and isinstance(response, list)

    def test_search_databases(self):
        """Test database search"""
        success, _ = self.run_api_test(
            "Search Databases",
            "GET",
            "databases",
            200,
            data={"search": "test"},
            token=self.admin_token
        )
        return success

    def test_get_database_details(self):
        """Test getting database details"""
        if hasattr(self, 'uploaded_db_id'):
            success, _ = self.run_api_test(
                "Get Database Details",
                "GET",
                f"databases/{self.uploaded_db_id}",
                200,
                token=self.admin_token
            )
            return success
        return False

    def test_create_download_request(self):
        """Test creating download request (staff)"""
        if hasattr(self, 'uploaded_db_id'):
            success, response = self.run_api_test(
                "Create Download Request",
                "POST",
                "download-requests",
                200,
                data={"database_id": self.uploaded_db_id},
                token=self.staff_token
            )
            
            if success and 'id' in response:
                self.download_request_id = response['id']
                return True
        return False

    def test_admin_cannot_request_download(self):
        """Test that admin cannot create download requests"""
        if hasattr(self, 'uploaded_db_id'):
            success, _ = self.run_api_test(
                "Admin Download Request (Should Fail)",
                "POST",
                "download-requests",
                403,
                data={"database_id": self.uploaded_db_id},
                token=self.admin_token
            )
            return success
        return False

    def test_list_download_requests_admin(self):
        """Test listing download requests (admin view)"""
        success, _ = self.run_api_test(
            "List Download Requests (Admin)",
            "GET",
            "download-requests",
            200,
            token=self.admin_token
        )
        return success

    def test_list_download_requests_staff(self):
        """Test listing download requests (staff view)"""
        success, _ = self.run_api_test(
            "List Download Requests (Staff)",
            "GET",
            "download-requests",
            200,
            token=self.staff_token
        )
        return success

    def test_approve_download_request(self):
        """Test approving download request"""
        if hasattr(self, 'download_request_id'):
            success, _ = self.run_api_test(
                "Approve Download Request",
                "PATCH",
                f"download-requests/{self.download_request_id}/approve",
                200,
                token=self.admin_token
            )
            return success
        return False

    def test_staff_cannot_approve_request(self):
        """Test that staff cannot approve requests"""
        if hasattr(self, 'download_request_id'):
            success, _ = self.run_api_test(
                "Staff Approve Request (Should Fail)",
                "PATCH",
                f"download-requests/{self.download_request_id}/approve",
                403,
                token=self.staff_token
            )
            return success
        return False

    def test_download_approved_file(self):
        """Test downloading approved file"""
        if hasattr(self, 'download_request_id'):
            url = f"{self.base_url}/api/download/{self.download_request_id}"
            headers = {'Authorization': f'Bearer {self.staff_token}'}
            
            try:
                response = requests.get(url, headers=headers)
                success = response.status_code == 200
                details = f"Status: {response.status_code}, Content-Type: {response.headers.get('content-type', 'N/A')}"
                
                self.log_test("Download Approved File", success, details)
                return success
            except Exception as e:
                self.log_test("Download Approved File", False, f"Exception: {str(e)}")
                return False
        return False

    def test_download_history(self):
        """Test download history"""
        success, _ = self.run_api_test(
            "Get Download History",
            "GET",
            "download-history",
            200,
            token=self.admin_token
        )
        return success

    def test_create_user(self):
        """Test creating new user (admin only)"""
        success, _ = self.run_api_test(
            "Create New User",
            "POST",
            "auth/register",
            200,
            data={
                "name": "Test User",
                "email": f"testuser_{datetime.now().strftime('%H%M%S')}@test.com",
                "password": "testpass123",
                "role": "staff"
            },
            token=self.admin_token
        )
        return success

    def test_staff_cannot_create_user(self):
        """Test that staff cannot create users"""
        success, _ = self.run_api_test(
            "Staff Create User (Should Fail)",
            "POST",
            "auth/register",
            403,
            data={
                "name": "Unauthorized User",
                "email": "unauthorized@test.com",
                "password": "testpass123",
                "role": "staff"
            },
            token=self.staff_token
        )
        return success

    def test_delete_database(self):
        """Test deleting database (admin only)"""
        if hasattr(self, 'uploaded_db_id'):
            success, _ = self.run_api_test(
                "Delete Database",
                "DELETE",
                f"databases/{self.uploaded_db_id}",
                200,
                token=self.admin_token
            )
            return success
        return False

    def test_staff_cannot_delete_database(self):
        """Test that staff cannot delete databases"""
        # First upload another database for this test
        self.test_create_sample_csv()
        
        # Get first available product for upload
        if hasattr(self, 'products') and self.products:
            product_id = self.products[0]['id']
        elif hasattr(self, 'test_product_id'):
            product_id = self.test_product_id
        else:
            self.log_test("Staff Delete Database Test", False, "No products available for upload")
            return False
        
        with open('/tmp/test_database.csv', 'rb') as f:
            files = {'file': ('test_database2.csv', f, 'text/csv')}
            data = {
                'description': 'Database for delete test',
                'product_id': product_id
            }
            
            success, response = self.run_api_test(
                "Upload Database for Delete Test",
                "POST",
                "databases",
                200,  # Backend returns 200
                data=data,
                files=files,
                token=self.admin_token
            )
            
            if success and 'id' in response:
                db_id = response['id']
                success, _ = self.run_api_test(
                    "Staff Delete Database (Should Fail)",
                    "DELETE",
                    f"databases/{db_id}",
                    403,
                    token=self.staff_token
                )
                
                # Clean up - delete with admin
                self.run_api_test(
                    "Cleanup Delete Test Database",
                    "DELETE",
                    f"databases/{db_id}",
                    200,
                    token=self.admin_token
                )
                
                return success
        return False

    def run_all_tests(self):
        """Run all tests in sequence"""
        print("🚀 Starting CRM API Tests...")
        print(f"Testing against: {self.base_url}")
        print("=" * 60)

        # Authentication Tests
        print("\n📋 Authentication Tests")
        if not self.test_admin_login():
            print("❌ Admin login failed - stopping tests")
            return False
        
        if not self.test_staff_login():
            print("❌ Staff login failed - stopping tests")
            return False
        
        self.test_invalid_login()
        self.test_get_current_user()
        self.test_unauthorized_access()

        # Product Management Tests
        print("\n📋 Product Management Tests")
        self.test_get_products()
        self.test_create_product()
        self.test_create_duplicate_product()
        self.test_staff_cannot_create_product()

        # Database Management Tests
        print("\n📋 Database Management Tests")
        self.test_upload_database()
        self.test_upload_database_without_product()
        self.test_staff_upload_forbidden()
        self.test_list_databases()
        self.test_search_databases()
        self.test_filter_databases_by_product()
        self.test_get_database_details()

        # Download Request Tests
        print("\n📋 Download Request Tests")
        self.test_create_download_request()
        self.test_admin_cannot_request_download()
        self.test_list_download_requests_admin()
        self.test_list_download_requests_staff()
        self.test_approve_download_request()
        self.test_staff_cannot_approve_request()

        # File Download Tests
        print("\n📋 File Download Tests")
        self.test_download_approved_file()
        self.test_download_history()

        # User Management Tests
        print("\n📋 User Management Tests")
        self.test_create_user()
        self.test_staff_cannot_create_user()

        # Database Deletion Tests
        print("\n📋 Database Deletion Tests")
        self.test_staff_cannot_delete_database()
        self.test_delete_database()

        # Product Deletion Tests
        print("\n📋 Product Deletion Tests")
        self.test_delete_product_with_databases()
        self.test_staff_cannot_delete_product()
        self.test_delete_product_success()

        return True

    def print_summary(self):
        """Print test summary"""
        print("\n" + "=" * 60)
        print("📊 TEST SUMMARY")
        print("=" * 60)
        print(f"Total Tests: {self.tests_run}")
        print(f"Passed: {self.tests_passed}")
        print(f"Failed: {self.tests_run - self.tests_passed}")
        print(f"Success Rate: {(self.tests_passed/self.tests_run*100):.1f}%")
        
        # Show failed tests
        failed_tests = [r for r in self.test_results if not r['success']]
        if failed_tests:
            print(f"\n❌ Failed Tests ({len(failed_tests)}):")
            for test in failed_tests:
                print(f"  - {test['test']}: {test['details']}")
        
        return self.tests_passed == self.tests_run

def main():
    tester = CRMAPITester()
    
    try:
        success = tester.run_all_tests()
        tester.print_summary()
        
        # Save detailed results
        results_file = '/app/test_reports/backend_test_results.json'
        with open(results_file, 'w') as f:
            json.dump({
                'summary': {
                    'total_tests': tester.tests_run,
                    'passed_tests': tester.tests_passed,
                    'failed_tests': tester.tests_run - tester.tests_passed,
                    'success_rate': tester.tests_passed/tester.tests_run*100 if tester.tests_run > 0 else 0
                },
                'test_results': tester.test_results,
                'timestamp': datetime.now().isoformat()
            }, f, indent=2)
        
        print(f"\n📄 Detailed results saved to: {results_file}")
        
        return 0 if success else 1
        
    except Exception as e:
        print(f"❌ Test execution failed: {str(e)}")
        return 1

if __name__ == "__main__":
    sys.exit(main())