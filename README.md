# WireMock with Full Mutual TLS (mTLS)

This setup runs WireMock with **full mutual TLS authentication** where both client and server verify each other's certificates using a shared Certificate Authority.

## Features

- ✅ HTTPS support on port 8443
- ✅ HTTP support on port 8088
- ✅ **Full mutual TLS (mTLS)** - both sides verify certificates
- ✅ Single CA signs both client and server certificates
- ✅ Python test script with httpx demonstrating full mTLS
- ✅ Proper certificate chain validation

## Quick Start

1. **Generate certificates** (already done if certs exist):
```bash
cd certs
./generate-certs.sh  # Or use the manual commands below
```

2. **Start WireMock**:
```bash
docker-compose up -d
```

3. **Test with Python**:
```bash
pip install httpx
python3 test_mtls.py
```

## Manual Certificate Setup

If you need to regenerate certificates:

### 1. Generate Server Certificate (for WireMock)
```bash
keytool -genkey -keyalg RSA -alias wiremock -keystore certs/keystore.jks \
  -storepass password -validity 365 -keysize 2048 \
  -dname "CN=localhost, OU=IT, O=Example, L=City, ST=State, C=US"
```

### 2. Generate CA and Client Certificates (for mTLS)
```bash
cd certs

# Create CA
openssl genrsa -out ca-key.pem 2048
openssl req -new -x509 -days 365 -key ca-key.pem -out ca-cert.pem \
  -subj "/C=US/ST=State/L=City/O=Example/OU=IT/CN=TestCA"

# Create client key and certificate
openssl genrsa -out client-key.pem 2048
openssl req -new -key client-key.pem -out client-cert.csr -config client-cert.conf
openssl x509 -req -in client-cert.csr -CA ca-cert.pem -CAkey ca-key.pem \
  -CAcreateserial -out client-cert.pem -days 365 -extensions v3_req \
  -extfile client-cert.conf

# Create PKCS12 bundle (for some clients)
openssl pkcs12 -export -out client-cert.p12 -inkey client-key.pem \
  -in client-cert.pem -passout pass:clientpass

# Create truststore for WireMock
keytool -importcert -file ca-cert.pem -alias ca -keystore truststore.jks \
  -storepass trustpass -noprompt
```

## Access Points

- **HTTP**: http://localhost:8088
- **HTTPS**: https://localhost:8443

## Testing

### Without Client Certificate (will fail)
```bash
curl --cacert certs/ca-cert.pem https://localhost:8443/__admin/health
# Error: sslv3 alert bad certificate
```

### With Client Certificate - Full mTLS (will succeed)
```bash
# Full mutual TLS with CA verification
curl --cacert certs/ca-cert.pem \
     --cert certs/client-cert.pem \
     --key certs/client-key.pem \
     https://localhost:8443/__admin/health
```

### Skip Server Verification (not recommended)
```bash
# Works but doesn't verify server certificate
curl -k --cert certs/client-cert.pem --key certs/client-key.pem \
  https://localhost:8443/__admin/health
```

### Using Python httpx
```bash
python3 test_mtls.py
```

The test script demonstrates:
1. ❌ Connection fails without client certificate (mTLS enforced)
2. ✅ Connection succeeds with client cert (server verification skipped)
3. ✅ **Full mutual TLS** - both sides verify each other's certificates
4. ✅ API calls work with mTLS enabled

## Directory Structure

- `mappings/` - WireMock stub mappings (JSON files)
- `files/` - Response body files
- `certs/` - SSL/TLS certificates
  - `keystore.jks` - Server certificate for WireMock
  - `truststore.jks` - CA certificate to validate client certs
  - `ca-cert.pem` - CA certificate
  - `client-cert.pem` - Client certificate
  - `client-key.pem` - Client private key
  - `client-cert.p12` - Client cert in PKCS12 format

## Example Stub

Create `mappings/hello.json`:
```json
{
  "request": {
    "method": "GET",
    "url": "/hello"
  },
  "response": {
    "status": 200,
    "body": "Hello, World!",
    "headers": {
      "Content-Type": "text/plain"
    }
  }
}
```

Test with:
```bash
# Full mTLS with CA verification
curl --cacert certs/ca-cert.pem \
     --cert certs/client-cert.pem \
     --key certs/client-key.pem \
     https://localhost:8443/hello
```

## How Full mTLS Works

1. **Certificate Authority (CA)**: A trusted CA signs both server and client certificates
2. **Server Authentication**: 
   - WireMock presents its certificate (signed by CA) from `keystore.jks`
   - Client verifies server certificate against CA in `ca-cert.pem`
3. **Client Authentication**: 
   - Client presents its certificate (signed by CA)
   - WireMock verifies client certificate against CA in `truststore.jks`
4. **Mutual Trust**: Both parties verify each other's certificates using the shared CA before establishing the connection

This is **true mutual TLS** - both endpoints authenticate each other.

## Configuration

WireMock is configured with these options in `docker-compose.yml`:
- `--https-port=8443` - Enable HTTPS on port 8443
- `--https-keystore=/home/wiremock/certs/keystore.jks` - Server certificate
- `--https-require-client-cert` - Require client certificates
- `--https-truststore=/home/wiremock/certs/truststore.jks` - Trusted CA certificates
- `--truststore-password=trustpass` - Truststore password

## Troubleshooting

**"sslv3 alert bad certificate"**: Client didn't provide a valid certificate. Make sure:
- Client certificate is signed by the CA in the truststore
- Certificate includes Subject Alternative Names (required by Jetty)
- Certificate is not expired

**"certificate verify failed"**: Server certificate validation failed. Use `-k` with curl or set `verify=False` in Python to skip server cert validation (for testing with self-signed certs).

