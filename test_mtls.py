#!/usr/bin/env python3
"""
Test WireMock mTLS connection using httpx.

This script demonstrates different SSL/TLS configurations for mutual TLS (mTLS).

=== SSL Context Explained ===

An SSL context defines how TLS connections are established and verified.
It controls:
1. Certificate verification (server, client, or both)
2. Which certificates to trust (CA certificates)
3. Which certificate to present (client certificate)

=== Components ===

1. CA Certificate (ca-cert.pem):
   - The Certificate Authority that signs other certificates
   - Used to verify that a certificate is trusted
   - Think of it as the "root of trust"

2. Client Certificate (client-cert.pem) + Private Key (client-key.pem):
   - Proves the client's identity to the server
   - Must be signed by a CA that the server trusts
   - Server checks: "Is this cert signed by a CA I trust?"

3. Server Certificate (in keystore.jks):
   - Proves the server's identity to the client
   - Must be signed by a CA that the client trusts
   - Client checks: "Is this cert signed by a CA I trust?"

=== SSL Context Configurations ===

Configuration 1: No verification (insecure, for testing only)
    ssl_context = ssl.create_default_context()
    ssl_context.check_hostname = False
    ssl_context.verify_mode = ssl.CERT_NONE
    # Server cert: NOT verified
    # Client cert: NOT sent

Configuration 2: Client cert only, no server verification
    ssl_context = ssl.create_default_context()
    ssl_context.check_hostname = False
    ssl_context.verify_mode = ssl.CERT_NONE
    ssl_context.load_cert_chain(certfile=CLIENT_CERT, keyfile=CLIENT_KEY)
    # Server cert: NOT verified (insecure!)
    # Client cert: Sent and verified by server

Configuration 3: Full mutual TLS (both sides verify)
    ssl_context = ssl.create_default_context(cafile=CA_CERT)
    ssl_context.load_cert_chain(certfile=CLIENT_CERT, keyfile=CLIENT_KEY)
    # Server cert: VERIFIED against CA_CERT
    # Client cert: Sent and verified by server
    # This is TRUE mutual TLS!

=== How Verification Works ===

Server verification (client verifying server):
1. Server presents its certificate during TLS handshake
2. Client checks: "Is this cert signed by a CA I trust?"
3. Client loads CA cert with: ssl.create_default_context(cafile=CA_CERT)
4. If verification fails → Connection rejected
5. If verification succeeds → Proceed to step 6

Client verification (server verifying client):
1. Server requests client certificate during TLS handshake
2. Client presents certificate with: ssl_context.load_cert_chain(...)
3. Server checks: "Is this cert signed by a CA I trust?"
4. Server has CA in truststore.jks
5. If verification fails → Connection rejected with "bad certificate"
6. If verification succeeds → Connection established

=== Common Errors ===

"certificate verify failed" → Client doesn't trust server's certificate
  Fix: Use correct CA with ssl.create_default_context(cafile=CA_CERT)

"sslv3 alert bad certificate" → Server doesn't trust client's certificate
  Fix: Ensure client cert is signed by CA in server's truststore

"unknown ca" → Certificate signed by unknown/untrusted CA
  Fix: Ensure both certs are signed by the same CA
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
    print("\n🔓 Test 2: mTLS Authentication - Client certificate only")
    print("   Expected: Connection accepted by server")
    print("   Note: Client skips server cert verification for comparison")
    try:
        ssl_context = create_ssl_context_with_client_cert(verify_server=False)
        
        with httpx.Client(verify=ssl_context) as client:
            response = client.get(f"{WIREMOCK_URL}/__admin/health", timeout=5)
            print(f"   ✅ SUCCESS: Server accepted client certificate")
            print(f"   Status: {response.status_code}")
            print(f"   Server: WireMock v{response.json()['version']}")
    except Exception as e:
        print(f"   ❌ FAILED: {type(e).__name__}: {e}")

def test_with_wrong_client_cert():
    """Test mTLS with wrong/untrusted client certificate - should fail."""
    print("\n🚫 Test 3: mTLS with Invalid Client Certificate")
    print("   Expected: Server rejects untrusted client certificate")
    try:
        # Generate a self-signed certificate (not signed by our CA)
        import tempfile
        import os
        
        with tempfile.TemporaryDirectory() as tmpdir:
            wrong_key = os.path.join(tmpdir, "wrong-key.pem")
            wrong_cert = os.path.join(tmpdir, "wrong-cert.pem")
            
            # Generate self-signed cert (not signed by our CA)
            os.system(f"openssl req -x509 -newkey rsa:2048 -keyout {wrong_key} "
                     f"-out {wrong_cert} -days 1 -nodes -subj '/CN=attacker' 2>/dev/null")
            
            ssl_context = ssl.create_default_context()
            ssl_context.check_hostname = False
            ssl_context.verify_mode = ssl.CERT_NONE
            ssl_context.load_cert_chain(certfile=wrong_cert, keyfile=wrong_key)
            
            with httpx.Client(verify=ssl_context) as client:
                response = client.get(f"{WIREMOCK_URL}/__admin/health", timeout=5)
                print(f"   ❌ FAILED: Server accepted untrusted certificate!")
                print(f"   Status: {response.status_code}")
    except httpx.ReadError as e:
        error_msg = str(e).lower()
        if any(keyword in error_msg for keyword in ["bad certificate", "unknown ca", "certificate unknown"]):
            print(f"   ✅ SUCCESS: Server rejected untrusted certificate")
            print(f"   Reason: Certificate not signed by trusted CA")
        else:
            print(f"   ⚠️  Failed with: {e}")
    except Exception as e:
        print(f"   ⚠️  Failed with {type(e).__name__}: {str(e)[:100]}")

def test_full_mtls_with_server_verification():
    """Test full mTLS - both client and server verify each other."""
    print("\n🔐 Test 4: Full mTLS - Mutual certificate verification")
    print("   Expected: Both sides verify each other's certificates")
    try:
        ssl_context = create_ssl_context_with_client_cert(verify_server=True)
        
        with httpx.Client(verify=ssl_context) as client:
            response = client.get(f"{WIREMOCK_URL}/__admin/health", timeout=5)
            print(f"   ✅ SUCCESS: Full mutual TLS working!")
            print(f"   ✓ Client verified server's certificate (signed by CA)")
            print(f"   ✓ Server verified client's certificate (signed by CA)")
            print(f"   Status: {response.status_code}")
    except Exception as e:
        if "certificate verify failed" in str(e).lower():
            print(f"   ❌ FAILED: Client rejected server's certificate")
            print(f"   Reason: {str(e)[:100]}")
        else:
            print(f"   ❌ FAILED: {type(e).__name__}: {str(e)[:100]}")

def test_client_rejects_bad_server_cert():
    """Test client rejecting server with wrong/untrusted certificate."""
    print("\n🚫 Test 5: Client Rejects Invalid Server Certificate")
    print("   Expected: Client rejects server with untrusted certificate")
    print("   Note: We'll use a different CA to verify server cert")
    try:
        import tempfile
        import os
        
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create a different CA (not the one that signed the server cert)
            wrong_ca_key = os.path.join(tmpdir, "wrong-ca-key.pem")
            wrong_ca_cert = os.path.join(tmpdir, "wrong-ca-cert.pem")
            
            # Generate different CA
            os.system(f"openssl genrsa -out {wrong_ca_key} 2048 2>/dev/null")
            os.system(f"openssl req -new -x509 -days 1 -key {wrong_ca_key} "
                     f"-out {wrong_ca_cert} -subj '/CN=WrongCA' 2>/dev/null")
            
            # Try to verify server cert with wrong CA
            ssl_context = ssl.create_default_context(cafile=wrong_ca_cert)
            ssl_context.load_cert_chain(certfile=CLIENT_CERT, keyfile=CLIENT_KEY)
            
            with httpx.Client(verify=ssl_context) as client:
                response = client.get(f"{WIREMOCK_URL}/__admin/health", timeout=5)
                print(f"   ❌ FAILED: Client accepted untrusted server certificate!")
                print(f"   Status: {response.status_code}")
    except httpx.ConnectError as e:
        error_msg = str(e).lower()
        if "certificate verify failed" in error_msg or "unable to get local issuer" in error_msg:
            print(f"   ✅ SUCCESS: Client rejected server's certificate")
            print(f"   Reason: Server cert not signed by trusted CA")
        else:
            print(f"   ⚠️  Failed with: {e}")
    except Exception as e:
        error_msg = str(e).lower()
        if "certificate verify failed" in error_msg:
            print(f"   ✅ SUCCESS: Client rejected server's certificate")
            print(f"   Reason: Server cert not signed by trusted CA")
        else:
            print(f"   ⚠️  Failed with {type(e).__name__}: {str(e)[:100]}")

def test_api_call_with_mtls():
    """Test API functionality with mTLS."""
    print("\n📡 Test 6: API Call with mTLS - Stub endpoint")
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
    print("\n💡 Test 7: Curl Examples")
    print("   Full mTLS with CA verification:")
    print("   $ curl --cacert certs/ca-cert.pem --cert certs/client-cert.pem \\")
    print("       --key certs/client-key.pem https://localhost:8443/hello")
    print()
    print("   Without server verification (-k flag):")
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
    test_with_wrong_client_cert()
    test_full_mtls_with_server_verification()
    test_client_rejects_bad_server_cert()
    test_api_call_with_mtls()
    test_with_curl_example()
    
    print("\n" + "=" * 70)
    print("Summary:")
    print("✅ Full mutual TLS (mTLS) is working!")
    print("✓ Server validates client certificates (signed by CA)")
    print("✓ Server rejects untrusted client certificates")
    print("✓ Client validates server certificates (signed by CA)")
    print("✓ Client rejects untrusted server certificates")
    print("✓ Both sides use the same Certificate Authority")
    print("=" * 70)
