#!/bin/bash
set -e

echo "🔐 Generating certificates for WireMock mTLS..."

# Create certs directory if it doesn't exist
mkdir -p certs
cd certs

# 1. Create CA certificate config
echo "📝 1. Creating CA config..."
cat > ca.conf << 'CAEOF'
[req]
distinguished_name = req_distinguished_name
x509_extensions = v3_ca
prompt = no

[req_distinguished_name]
C = US
ST = State
L = City
O = Example
OU = IT
CN = TestCA

[v3_ca]
basicConstraints = critical,CA:TRUE
keyUsage = critical,keyCertSign,cRLSign
subjectKeyIdentifier = hash
authorityKeyIdentifier = keyid:always,issuer
CAEOF

# 2. Generate CA certificate with proper extensions
echo "🏛️  2. Creating CA certificate..."
openssl genrsa -out ca-key.pem 2048 2>/dev/null
openssl req -new -x509 -days 365 -key ca-key.pem -out ca-cert.pem -config ca.conf 2>/dev/null

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

# 4. Generate client certificate signed by CA
echo "👤 4. Generating client certificate..."
openssl genrsa -out client-key.pem 2048 2>/dev/null
openssl req -new -key client-key.pem -out client-cert.csr \
  -config client-cert.conf 2>/dev/null
openssl x509 -req -in client-cert.csr -CA ca-cert.pem -CAkey ca-key.pem \
  -CAcreateserial -out client-cert.pem -days 365 -extensions v3_req \
  -extfile client-cert.conf 2>/dev/null

# 5. Create server certificate config
echo "📝 5. Creating server certificate config..."
cat > server-cert.conf << 'EOF'
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
CN = localhost

[v3_req]
keyUsage = keyEncipherment, dataEncipherment, digitalSignature
extendedKeyUsage = serverAuth
subjectAltName = @alt_names

[alt_names]
DNS.1 = localhost
DNS.2 = wiremock
IP.1 = 127.0.0.1
EOF

# 6. Generate server certificate signed by CA
echo "🖥️  6. Generating server certificate..."
openssl genrsa -out server-key.pem 2048 2>/dev/null
openssl req -new -key server-key.pem -out server-cert.csr \
  -config server-cert.conf 2>/dev/null
openssl x509 -req -in server-cert.csr -CA ca-cert.pem -CAkey ca-key.pem \
  -CAcreateserial -out server-cert.pem -days 365 -extensions v3_req \
  -extfile server-cert.conf 2>/dev/null

# 7. Create PKCS12 bundles
echo "📦 7. Creating PKCS12 bundles..."
openssl pkcs12 -export -out client-cert.p12 -inkey client-key.pem \
  -in client-cert.pem -passout pass:clientpass 2>/dev/null
openssl pkcs12 -export -out server.p12 -inkey server-key.pem \
  -in server-cert.pem -certfile ca-cert.pem -name wiremock \
  -passout pass:password 2>/dev/null

# 8. Create Java keystores
echo "🔒 8. Creating Java keystores..."
keytool -importkeystore -srckeystore server.p12 -srcstoretype PKCS12 \
  -destkeystore keystore.jks -deststoretype JKS \
  -srcstorepass password -deststorepass password -noprompt 2>/dev/null || true
keytool -importcert -file ca-cert.pem -alias ca -keystore truststore.jks \
  -storepass trustpass -noprompt 2>/dev/null || true

# Clean up intermediate files
rm -f client-cert.csr server-cert.csr server.p12

echo "✅ Certificate generation complete!"
echo ""
echo "Generated files:"
echo "  - ca-cert.pem (CA certificate - use for verification)"
echo "  - keystore.jks (server certificate signed by CA)"
echo "  - truststore.jks (CA certificate for client validation)"
echo "  - client-cert.pem (client certificate signed by CA)"
echo "  - client-key.pem (client private key)"
echo "  - client-cert.p12 (client cert bundle)"
echo ""
echo "✨ Full mutual TLS (mTLS) ready!"
echo "   Both client and server certificates signed by same CA"
