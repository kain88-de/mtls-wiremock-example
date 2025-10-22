#!/bin/bash
set -e

echo "🔐 Generating certificates for WireMock mTLS..."

# Create certs directory if it doesn't exist
mkdir -p certs
cd certs

# 1. Generate server certificate for WireMock
echo "📜 1. Generating server certificate..."
keytool -genkey -keyalg RSA -alias wiremock -keystore keystore.jks \
  -storepass password -validity 365 -keysize 2048 \
  -dname "CN=localhost, OU=IT, O=Example, L=City, ST=State, C=US" 2>/dev/null || true

# 2. Create CA certificate
echo "🏛️  2. Creating CA certificate..."
openssl genrsa -out ca-key.pem 2048 2>/dev/null
openssl req -new -x509 -days 365 -key ca-key.pem -out ca-cert.pem \
  -subj "/C=US/ST=State/L=City/O=Example/OU=IT/CN=TestCA" 2>/dev/null

# 3. Create client certificate config
echo "📝 3. Creating client certificate config..."
cat > client-cert.conf << 'EOF'
[req]
distinguished_name = req_distinguished_name
req_extensions = v3_req
prompt = no

[req_distinguished_name]
C = US
ST = State
L = City
O = Example
OU = IT
CN = client

[v3_req]
keyUsage = keyEncipherment, dataEncipherment, digitalSignature
extendedKeyUsage = clientAuth
subjectAltName = @alt_names

[alt_names]
DNS.1 = client
DNS.2 = localhost
IP.1 = 127.0.0.1
EOF

# 4. Generate client certificate
echo "👤 4. Generating client certificate..."
openssl genrsa -out client-key.pem 2048 2>/dev/null
openssl req -new -key client-key.pem -out client-cert.csr \
  -config client-cert.conf 2>/dev/null
openssl x509 -req -in client-cert.csr -CA ca-cert.pem -CAkey ca-key.pem \
  -CAcreateserial -out client-cert.pem -days 365 -extensions v3_req \
  -extfile client-cert.conf 2>/dev/null

# 5. Create PKCS12 bundle
echo "📦 5. Creating PKCS12 bundle..."
openssl pkcs12 -export -out client-cert.p12 -inkey client-key.pem \
  -in client-cert.pem -passout pass:clientpass 2>/dev/null

# 6. Create truststore
echo "🔒 6. Creating truststore..."
keytool -importcert -file ca-cert.pem -alias ca -keystore truststore.jks \
  -storepass trustpass -noprompt 2>/dev/null || true

# Clean up intermediate files
rm -f client-cert.csr ca-cert.srl

echo "✅ Certificate generation complete!"
echo ""
echo "Generated files:"
echo "  - keystore.jks (server certificate)"
echo "  - truststore.jks (CA certificate for client validation)"
echo "  - ca-cert.pem (CA certificate)"
echo "  - client-cert.pem (client certificate)"
echo "  - client-key.pem (client private key)"
echo "  - client-cert.p12 (client cert bundle)"
