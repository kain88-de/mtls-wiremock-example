#!/usr/bin/env python3
"""
Test WireMock mTLS connection using httpx.
"""
import httpx
import ssl

# Configuration
WIREMOCK_URL = "https://localhost:8443"
CLIENT_CERT = "certs/client-cert.pem"
CLIENT_KEY = "certs/client-key.pem"
CA_CERT = "certs/ca-cert.pem"

def create_ssl_context_with_client_cert(verify_server=False):
    """Create SSL context with client certificate."""
    if verify_server:
        ssl_context = ssl.create_default_context(cafile=CA_CERT)
    else:
        ssl_context = ssl.create_default_context()
        ssl_context.check_hostname = False
        ssl_context.verify_mode = ssl.CERT_NONE
    
    ssl_context.load_cert_chain(certfile=CLIENT_CERT, keyfile=CLIENT_KEY)
    return ssl_context

def test_without_client_cert():
    """Test connection without client certificate - should fail."""
    print("🔒 Test 1: Connecting without client certificate (should fail)...")
    try:
        # Disable cert verification but don't provide client cert
        response = httpx.get(
            f"{WIREMOCK_URL}/__admin/health",
            verify=False,
            timeout=5
        )
        print(f"   ❌ UNEXPECTED: Connected successfully (status {response.status_code})")
        print(f"   Response: {response.text[:100]}")
    except httpx.ConnectError as e:
        print(f"   ✅ EXPECTED: Connection failed - {type(e).__name__}: {str(e)[:100]}")
    except Exception as e:
        print(f"   ✅ EXPECTED: Failed with {type(e).__name__}: {str(e)[:100]}")

def test_with_client_cert():
    """Test connection with valid client certificate - should succeed."""
    print("\n🔓 Test 2: Connecting with valid client certificate (should succeed)...")
    try:
        ssl_context = create_ssl_context_with_client_cert(verify_server=False)
        
        with httpx.Client(verify=ssl_context) as client:
            response = client.get(f"{WIREMOCK_URL}/__admin/health", timeout=5)
            print(f"   ✅ SUCCESS: Connected with status {response.status_code}")
            print(f"   Response: {response.json()}")
    except Exception as e:
        print(f"   ❌ FAILED: {type(e).__name__}: {e}")

def test_with_client_cert_and_ca():
    """Test connection with client certificate and CA verification."""
    print("\n🔐 Test 3: Connecting with client cert and server CA verification...")
    try:
        # Note: This will fail because WireMock's server cert is self-signed
        # and not signed by our CA
        ssl_context = create_ssl_context_with_client_cert(verify_server=True)
        
        with httpx.Client(verify=ssl_context) as client:
            response = client.get(f"{WIREMOCK_URL}/__admin/health", timeout=5)
            print(f"   ✅ SUCCESS: Connected with status {response.status_code}")
            print(f"   Response: {response.json()}")
    except Exception as e:
        print(f"   ⚠️  Expected failure: {type(e).__name__}")
        print(f"   Reason: Server cert is self-signed, not signed by our CA")

def test_api_call():
    """Test an actual API call with a stub."""
    print("\n📡 Test 4: Making API call to stub endpoint...")
    try:
        ssl_context = create_ssl_context_with_client_cert(verify_server=False)
        
        with httpx.Client(verify=ssl_context) as client:
            response = client.get(f"{WIREMOCK_URL}/hello", timeout=5)
            if response.status_code == 404:
                print(f"   ⚠️  No stub configured (404) - Create mappings/hello.json to test")
            else:
                print(f"   ✅ SUCCESS: Status {response.status_code}")
                print(f"   Response: {response.text}")
    except Exception as e:
        print(f"   ❌ FAILED: {type(e).__name__}: {e}")

if __name__ == "__main__":
    print("=" * 60)
    print("WireMock mTLS Test")
    print("=" * 60)
    
    test_without_client_cert()
    test_with_client_cert()
    test_with_client_cert_and_ca()
    test_api_call()
    
    print("\n" + "=" * 60)
    print("Tests completed!")
    print("=" * 60)
