#!/bin/bash
# Generates a self-signed SSL certificate for local development.
# For production, replace with Let's Encrypt or your CA-issued cert.

CERT_DIR="config/nginx/certs"
mkdir -p "$CERT_DIR"

openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
  -keyout "$CERT_DIR/neurotrap.key" \
  -out "$CERT_DIR/neurotrap.crt" \
  -subj "/C=US/ST=State/L=City/O=NeuroTrap/OU=Security/CN=neurotrap.local"

echo "Self-signed certificate created at $CERT_DIR/"
echo "Add 'neurotrap.local' to /etc/hosts pointing to your server IP."
