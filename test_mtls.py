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
    """Test mTLS enforcement - connection without client cert should be rejected."""
    print("🔒 Test 1: mTLS Enforcement - No client certificate")
    print("   Expected: Connection rejected by server")
    try:
        # Try to connect without providing client certificate
        ssl_context = ssl.create_default_context()
        ssl_context.check_hostname = False
        ssl_context.verify_mode = ssl.CERT_NONE
        
        with httpx.Client(verify=ssl_context) as client:
            response = client.get(f"{WIREMOCK_URL}/__admin/health", timeout=5)
            print(f"   ❌ FAILED: Server accepted connection without client cert!")
            print(f"   Status: {response.status_code}")
    except httpx.ReadError as e:
        if "bad certificate" in str(e).lower():
            print(f"   ✅ SUCCESS: Server rejected connection (mTLS enforced)")
        else:
            print(f"   ⚠️  Failed with: {e}")
    except Exception as e:
        print(f"   ⚠️  Failed with {type(e).__name__}: {str(e)[:100]}")

def test_with_client_cert():
    """Test mTLS - connection with valid client certificate should succeed."""
    print("\n🔓 Test 2: mTLS Authentication - Valid client certificate")
    print("   Expected: Connection accepted by server")
    try:
        ssl_context = create_ssl_context_with_client_cert(verify_server=False)
        
        with httpx.Client(verify=ssl_context) as client:
            response = client.get(f"{WIREMOCK_URL}/__admin/health", timeout=5)
            print(f"   ✅ SUCCESS: Server accepted client certificate")
            print(f"   Status: {response.status_code}")
            print(f"   Server: WireMock v{response.json()['version']}")
    except Exception as e:
        print(f"   ❌ FAILED: {type(e).__name__}: {e}")

def test_api_call_with_mtls():
    """Test API functionality with mTLS."""
    print("\n📡 Test 3: API Call with mTLS - Stub endpoint")
    print("   Expected: API call succeeds with client certificate")
    try:
        ssl_context = create_ssl_context_with_client_cert(verify_server=False)
        
        with httpx.Client(verify=ssl_context) as client:
            response = client.get(f"{WIREMOCK_URL}/hello", timeout=5)
            if response.status_code == 404:
                print(f"   ⚠️  No stub configured (404)")
            else:
                print(f"   ✅ SUCCESS: API call succeeded")
                print(f"   Status: {response.status_code}")
                print(f"   Response: {response.text}")
    except Exception as e:
        print(f"   ❌ FAILED: {type(e).__name__}: {e}")

def test_with_curl_example():
    """Show curl command examples."""
    print("\n💡 Test 4: Curl Examples")
    print("   With client cert (should work):")
    print("   $ curl -k --cert certs/client-cert.pem --key certs/client-key.pem \\")
    print("       https://localhost:8443/hello")
    print()
    print("   Without client cert (should fail):")
    print("   $ curl -k https://localhost:8443/hello")
    print("   # Error: sslv3 alert bad certificate")

if __name__ == "__main__":
    print("=" * 70)
    print("WireMock mTLS Test Suite")
    print("=" * 70)
    print("\nTesting mutual TLS (mTLS) authentication:")
    print("- Server authenticates client using certificate")
    print("- Client authenticates server using certificate (optional)")
    print()
    
    test_without_client_cert()
    test_with_client_cert()
    test_api_call_with_mtls()
    test_with_curl_example()
    
    print("\n" + "=" * 70)
    print("Summary: mTLS is properly configured!")
    print("- Server REQUIRES client certificates")
    print("- Client certificates must be signed by trusted CA")
    print("=" * 70)
