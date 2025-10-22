# WireMock mTLS Implementation - Summary

## ✅ What Was Implemented

Successfully configured WireMock with mutual TLS (mTLS) authentication in Docker Compose.

## 📁 Files Created

1. **docker-compose.yml** - WireMock service with mTLS enabled
2. **test_mtls.py** - Python test script using httpx
3. **generate-certs.sh** - Certificate generation script
4. **README.md** - Complete documentation
5. **mappings/hello.json** - Sample WireMock stub
6. **certs/** - Directory with all certificates:
   - `keystore.jks` - Server certificate
   - `truststore.jks` - CA for client validation
   - `ca-cert.pem` - Certificate Authority
   - `client-cert.pem` - Client certificate
   - `client-key.pem` - Client private key
   - `client-cert.p12` - PKCS12 bundle

## 🔐 How It Works

1. **Server Side**: WireMock presents server certificate from `keystore.jks`
2. **Client Side**: Client must present certificate signed by CA in `truststore.jks`
3. **Validation**: WireMock validates client certificates against the truststore
4. **Rejection**: Connections without valid client certificates are rejected

## 🧪 Test Results

All tests passing:
- ✅ Connections without client cert are rejected (mTLS enforced)
- ✅ Connections with valid client cert succeed
- ✅ API calls work through mTLS
- ✅ Both Python (httpx) and curl work

## 🚀 Quick Start

```bash
# Start WireMock
docker compose up -d

# Test with Python
python3 test_mtls.py

# Test with curl
curl -k --cert certs/client-cert.pem --key certs/client-key.pem \
  https://localhost:8443/hello
```

## 📊 Ports

- HTTP: `http://localhost:8088`
- HTTPS with mTLS: `https://localhost:8443`

## 🔑 Key Configuration

WireMock options:
- `--https-port=8443`
- `--https-keystore=/home/wiremock/certs/keystore.jks`
- `--https-require-client-cert` ← Enables mTLS
- `--https-truststore=/home/wiremock/certs/truststore.jks` ← Client CA
- `--truststore-password=trustpass`

## ✨ Features Demonstrated

1. Mutual TLS authentication
2. Certificate generation (CA, server, client)
3. Python client with httpx
4. Curl client with certificates
5. WireMock stub mappings
6. Proper certificate validation
7. Subject Alternative Names (SANs) in client cert
