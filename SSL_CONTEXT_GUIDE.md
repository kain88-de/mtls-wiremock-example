# SSL/TLS Context Configuration Guide

This guide explains how SSL/TLS contexts work in Python for mutual TLS (mTLS) authentication.

## Table of Contents
- [Components](#components)
- [SSL Context Configurations](#ssl-context-configurations)
- [How Verification Works](#how-verification-works)
- [Common Errors](#common-errors)
- [Examples](#examples)

## Components

### 1. Certificate Authority (CA)
**File**: `ca-cert.pem`

The CA is the "root of trust" that signs other certificates.

```python
# Load CA for verification
ssl_context = ssl.create_default_context(cafile="certs/ca-cert.pem")
```

**Purpose**:
- Signs both client and server certificates
- Used to verify that a presented certificate is trusted
- Think of it as a digital notary

### 2. Client Certificate & Key
**Files**: `client-cert.pem` + `client-key.pem`

Proves the client's identity to the server.

```python
# Present client certificate
ssl_context.load_cert_chain(
    certfile="certs/client-cert.pem",
    keyfile="certs/client-key.pem"
)
```

**Purpose**:
- Client authenticates itself to the server
- Must be signed by a CA the server trusts
- Server validates: "Is this signed by my trusted CA?"

### 3. Server Certificate & Key
**Files**: Inside `keystore.jks`

Proves the server's identity to the client.

**Purpose**:
- Server authenticates itself to the client
- Must be signed by a CA the client trusts
- Client validates: "Is this signed by my trusted CA?"

## SSL Context Configurations

### Configuration 1: No Verification (Insecure!)
⚠️ **For testing only - DO NOT use in production!**

```python
import ssl

ssl_context = ssl.create_default_context()
ssl_context.check_hostname = False
ssl_context.verify_mode = ssl.CERT_NONE
```

**What happens**:
- ❌ Server certificate: NOT verified
- ❌ Client certificate: NOT sent
- ⚠️ Vulnerable to man-in-the-middle attacks

**Use case**: Quick testing when certificates don't matter

---

### Configuration 2: Client Authentication Only
One-way verification - only server validates client.

```python
import ssl

ssl_context = ssl.create_default_context()
ssl_context.check_hostname = False
ssl_context.verify_mode = ssl.CERT_NONE
ssl_context.load_cert_chain(
    certfile="certs/client-cert.pem",
    keyfile="certs/client-key.pem"
)
```

**What happens**:
- ❌ Server certificate: NOT verified (client trusts blindly)
- ✅ Client certificate: Sent and verified by server
- ⚠️ Still vulnerable to server impersonation

**Use case**: When you trust the server's identity implicitly (e.g., localhost testing)

---

### Configuration 3: Full Mutual TLS (Recommended!)
✅ **True mutual authentication - both sides verify each other**

```python
import ssl

ssl_context = ssl.create_default_context(cafile="certs/ca-cert.pem")
ssl_context.load_cert_chain(
    certfile="certs/client-cert.pem",
    keyfile="certs/client-key.pem"
)
```

**What happens**:
- ✅ Server certificate: VERIFIED against CA
- ✅ Client certificate: Sent and verified by server
- ✅ Both sides authenticate each other
- ✅ Secure against man-in-the-middle attacks

**Use case**: Production environments, security-critical applications

## How Verification Works

### Server Verification (Client → Server)
Client verifies the server's identity.

```
┌─────────┐                                    ┌─────────┐
│ Client  │                                    │ Server  │
└────┬────┘                                    └────┬────┘
     │                                              │
     │ 1. TLS Handshake                             │
     │─────────────────────────────────────────────>│
     │                                              │
     │ 2. Server presents certificate               │
     │<─────────────────────────────────────────────│
     │    (signed by TestCA)                        │
     │                                              │
     │ 3. Client checks:                            │
     │    "Is this cert signed by CA I trust?"      │
     │    (using ca-cert.pem)                       │
     │                                              │
     │ 4a. If YES → Continue                        │
     │ 4b. If NO → Reject ("certificate verify      │
     │             failed")                         │
```

**Code**:
```python
# Client loads CA to verify server
ssl_context = ssl.create_default_context(cafile="certs/ca-cert.pem")
```

**Server must**:
- Present a certificate signed by the CA in `ca-cert.pem`
- Certificate must not be expired
- Certificate hostname must match (unless `check_hostname=False`)

---

### Client Verification (Server → Client)
Server verifies the client's identity.

```
┌─────────┐                                    ┌─────────┐
│ Client  │                                    │ Server  │
└────┬────┘                                    └────┬────┘
     │                                              │
     │ 5. Server requests client certificate        │
     │<─────────────────────────────────────────────│
     │                                              │
     │ 6. Client presents certificate               │
     │─────────────────────────────────────────────>│
     │    (signed by TestCA)                        │
     │                                              │
     │                                              │ 7. Server checks:
     │                                              │    "Is this cert signed
     │                                              │     by CA I trust?"
     │                                              │    (using truststore.jks)
     │                                              │
     │ 8a. If YES → Connection established          │
     │<─────────────────────────────────────────────│
     │ 8b. If NO → Reject ("bad certificate")       │
```

**Code**:
```python
# Client loads certificate to present
ssl_context.load_cert_chain(
    certfile="certs/client-cert.pem",
    keyfile="certs/client-key.pem"
)
```

**Client must**:
- Present a certificate signed by the CA in server's `truststore.jks`
- Certificate must not be expired
- Certificate must have proper Subject Alternative Names (SANs)

## Common Errors

### Error: "certificate verify failed"
**Cause**: Client doesn't trust the server's certificate.

**Fix**:
```python
# Make sure you're using the correct CA
ssl_context = ssl.create_default_context(cafile="certs/ca-cert.pem")
```

**Check**:
- Is server certificate signed by the CA in `ca-cert.pem`?
- Is the CA certificate file path correct?
- Is the certificate expired?

---

### Error: "sslv3 alert bad certificate"
**Cause**: Server doesn't trust the client's certificate.

**Fix**:
```python
# Make sure client certificate is signed by trusted CA
ssl_context.load_cert_chain(
    certfile="certs/client-cert.pem",  # Must be signed by CA in truststore.jks
    keyfile="certs/client-key.pem"
)
```

**Check**:
- Is client certificate signed by the CA in server's `truststore.jks`?
- Are you presenting the correct client certificate?
- Is the certificate expired?

---

### Error: "unknown ca"
**Cause**: Certificate is signed by an unknown or untrusted CA.

**Fix**: Ensure both client and server certificates are signed by the **same CA**.

```bash
# Verify certificate chain
openssl verify -CAfile certs/ca-cert.pem certs/client-cert.pem
openssl verify -CAfile certs/ca-cert.pem certs/server-cert.pem
```

---

### Error: "certificate has expired"
**Cause**: Certificate validity period has passed.

**Fix**: Regenerate certificates:
```bash
./generate-certs.sh
```

## Examples

### Example 1: Basic HTTPS (no client cert)
```python
import httpx
import ssl

# Server verification only
ssl_context = ssl.create_default_context(cafile="certs/ca-cert.pem")

with httpx.Client(verify=ssl_context) as client:
    response = client.get("https://localhost:8443/__admin/health")
    # This will FAIL - server requires client certificate
```

---

### Example 2: Client Certificate without Server Verification
```python
import httpx
import ssl

# Skip server verification (not recommended)
ssl_context = ssl.create_default_context()
ssl_context.check_hostname = False
ssl_context.verify_mode = ssl.CERT_NONE

# But present client certificate
ssl_context.load_cert_chain(
    certfile="certs/client-cert.pem",
    keyfile="certs/client-key.pem"
)

with httpx.Client(verify=ssl_context) as client:
    response = client.get("https://localhost:8443/__admin/health")
    # This WORKS - but doesn't verify server identity
```

---

### Example 3: Full Mutual TLS (Recommended)
```python
import httpx
import ssl

# Verify server certificate using CA
ssl_context = ssl.create_default_context(cafile="certs/ca-cert.pem")

# Present client certificate
ssl_context.load_cert_chain(
    certfile="certs/client-cert.pem",
    keyfile="certs/client-key.pem"
)

with httpx.Client(verify=ssl_context) as client:
    response = client.get("https://localhost:8443/__admin/health")
    # This WORKS - both sides verify each other
    # ✓ Client verifies server (using CA)
    # ✓ Server verifies client (using CA)
```

---

### Example 4: Wrong Certificate (Will Fail)
```python
import httpx
import ssl
import tempfile
import os

# Generate a self-signed certificate (not signed by our CA)
with tempfile.TemporaryDirectory() as tmpdir:
    wrong_key = os.path.join(tmpdir, "wrong-key.pem")
    wrong_cert = os.path.join(tmpdir, "wrong-cert.pem")
    
    os.system(f"openssl req -x509 -newkey rsa:2048 -keyout {wrong_key} "
             f"-out {wrong_cert} -days 1 -nodes -subj '/CN=attacker' 2>/dev/null")
    
    ssl_context = ssl.create_default_context()
    ssl_context.check_hostname = False
    ssl_context.verify_mode = ssl.CERT_NONE
    ssl_context.load_cert_chain(certfile=wrong_cert, keyfile=wrong_key)
    
    with httpx.Client(verify=ssl_context) as client:
        response = client.get("https://localhost:8443/__admin/health")
        # This FAILS - server rejects certificate
        # Error: "sslv3 alert certificate unknown"
```

## Summary

| Configuration | Server Verifies Client | Client Verifies Server | Security Level |
|--------------|------------------------|------------------------|----------------|
| No verification | ❌ | ❌ | 🔴 Insecure |
| Client cert only | ✅ | ❌ | 🟡 Partial |
| **Full mTLS** | ✅ | ✅ | 🟢 **Secure** |

**Key Takeaway**: For production, always use **Configuration 3 (Full mTLS)** where both client and server verify each other using the same CA.
