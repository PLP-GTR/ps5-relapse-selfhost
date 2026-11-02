#!/usr/bin/env bash
# Download ftpsrv-ps5.elf from the official ps5-payload-dev release and register
# it in payloads.json exactly as used in a working host setup.
# Never vendors the ELF into git — downloads into www/payloads/ only.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

if [[ -f .env ]]; then
  # shellcheck disable=SC1091
  set -a
  # shellcheck source=/dev/null
  source .env
  set +a
fi

WWW="${WWW_DIR:-www}"
OVERLAY="${OVERLAY_DIR:-overlay}"
FTPSRV_VERSION="${FTPSRV_VERSION:-v0.21.1}"
FTPSRV_URL="${FTPSRV_URL:-https://github.com/ps5-payload-dev/ftpsrv/releases/download/${FTPSRV_VERSION}/ftpsrv-ps5.elf}"
# SHA-256 of the v0.21.1 release asset (must match before install).
FTPSRV_SHA256="${FTPSRV_SHA256:-7d4b31c83eae4e056580482a3a074e1db25922efc74ac1e439473b45d71a5938}"

PAYLOAD_DIR="$WWW/payloads"
ELF="$PAYLOAD_DIR/ftpsrv-ps5.elf"
JSON_TEMPLATE="$OVERLAY/payloads.json"

if [[ ! -d "$PAYLOAD_DIR" ]]; then
  echo "error: $PAYLOAD_DIR missing — run ./scripts/setup-host.sh first" >&2
  exit 1
fi
if [[ ! -f "$JSON_TEMPLATE" ]]; then
  echo "error: $JSON_TEMPLATE missing (expected overlay with FTP payloads.json)" >&2
  exit 1
fi

tmpdir="$(mktemp -d)"
trap 'rm -rf "$tmpdir"' EXIT
tmpelf="$tmpdir/ftpsrv-ps5.elf"

echo "downloading $FTPSRV_URL ..."
if command -v curl >/dev/null 2>&1; then
  curl -fsSL -o "$tmpelf" "$FTPSRV_URL"
elif command -v wget >/dev/null 2>&1; then
  wget -q -O "$tmpelf" "$FTPSRV_URL"
else
  echo "error: need curl or wget to download ftpsrv" >&2
  exit 1
fi

if command -v sha256sum >/dev/null 2>&1; then
  got="$(sha256sum "$tmpelf" | awk '{print $1}')"
elif command -v shasum >/dev/null 2>&1; then
  got="$(shasum -a 256 "$tmpelf" | awk '{print $1}')"
else
  echo "error: need sha256sum or shasum to verify ftpsrv" >&2
  exit 1
fi
if [[ "$got" != "$FTPSRV_SHA256" ]]; then
  echo "error: SHA-256 mismatch for ftpsrv-ps5.elf" >&2
  echo "  expected: $FTPSRV_SHA256" >&2
  echo "  got:      $got" >&2
  exit 1
fi

cp -f "$tmpelf" "$ELF"
chmod 644 "$ELF"
cp -f "$JSON_TEMPLATE" "$PAYLOAD_DIR/payloads.json"

echo "installed $ELF"
echo "updated $PAYLOAD_DIR/payloads.json (FTP Server · $FTPSRV_VERSION · port 2121)"
echo "sha256 $got"
