#!/usr/bin/env bash
# Render dnsmasq and nginx configs from templates using values in .env
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

if [[ ! -f .env ]]; then
  echo "error: .env not found. Copy .env.example to .env and set SERVER_IP." >&2
  exit 1
fi

# shellcheck disable=SC1091
set -a
# shellcheck source=/dev/null
source .env
set +a

: "${SERVER_IP:?SERVER_IP must be set in .env}"
: "${GUIDE_IP:=$SERVER_IP}"
: "${UPSTREAM_DNS_1:=1.1.1.1}"
: "${UPSTREAM_DNS_2:=8.8.8.8}"

export SERVER_IP GUIDE_IP UPSTREAM_DNS_1 UPSTREAM_DNS_2

# Validate both addresses before writing either generated configuration.
python3 - <<'PY'
import ipaddress, os, sys
for key in ("SERVER_IP", "GUIDE_IP"):
    try:
        ipaddress.IPv4Address(os.environ[key])
    except ValueError:
        print(f"error: {key} must be an IPv4 address (got: {os.environ[key]})", file=sys.stderr)
        sys.exit(1)
PY

render() {
  local src="$1" dst="$2"
  # Substitute only our variables, preserving nginx's $uri etc.
  # Avoids requiring gettext on every host.
  python3 - "$src" "$dst" <<'PY'
import os, sys
src, dst = sys.argv[1], sys.argv[2]
text = open(src, encoding="utf-8").read()
for key in ("SERVER_IP", "GUIDE_IP", "UPSTREAM_DNS_1", "UPSTREAM_DNS_2"):
    text = text.replace("${%s}" % key, os.environ[key])
open(dst, "w", encoding="utf-8").write(text)
print(f"wrote {dst}")
PY
}

render dnsmasq/dnsmasq.conf.template dnsmasq/dnsmasq.conf
render nginx/default.conf.template nginx/default.conf

echo "configs rendered for SERVER_IP=$SERVER_IP, GUIDE_IP=$GUIDE_IP"
