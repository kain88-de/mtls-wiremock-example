# WireMock with HTTPS

This setup runs WireMock with HTTPS enabled.

## Setup

1. Generate a self-signed certificate (for testing):
```bash
keytool -genkey -keyalg RSA -alias wiremock -keystore certs/keystore.jks -storepass password -validity 365 -keysize 2048 -dname "CN=localhost, OU=IT, O=Example, L=City, ST=State, C=US"
```

2. Start WireMock:
```bash
docker-compose up -d
```

3. Access WireMock:
   - HTTP: http://localhost:8088
   - HTTPS: https://localhost:8443

## Directory Structure

- `mappings/` - WireMock stub mappings (JSON files)
- `files/` - Response body files
- `certs/` - SSL certificates (keystore.jks)

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
curl -k https://localhost:8443/hello
```
