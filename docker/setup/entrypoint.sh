#!/usr/bin/env bash
# Run preparation against the repository bind-mounted at the working directory.
set -euo pipefail

usage() {
  cat <<'HELP'
Usage: docker compose run --rm setup [command]

Commands:
  prepare [--with-ftp]  Render configs, generate certs, install the host page,
                       optionally add FTP, and verify the prepared files.
  render-config        Render DNS and nginx configuration from .env.
  generate-cert        Generate the TLS certificate and key if missing.
  setup-host           Refresh the pinned host page and apply the overlay.
  add-ftpsrv           Download and verify the optional FTP payload.
  verify               Check prepared files (Docker checks run on the host).
  help                 Show this message.

The default command is prepare. Run docker compose up -d on the host afterward.
HELP
}

action="${1:-prepare}"
if (( $# > 0 )); then shift; fi
with_ftp=false

case "$action" in
  help|-h|--help)
    usage
    exit 0
    ;;
  prepare)
    if (( $# == 1 )) && [[ "$1" == "--with-ftp" ]]; then
      with_ftp=true
    elif (( $# > 0 )); then
      usage >&2
      exit 2
    fi
    ;;
  render-config|generate-cert|setup-host|add-ftpsrv|verify)
    if (( $# > 0 )); then
      usage >&2
      exit 2
    fi
    ;;
  *)
    usage >&2
    exit 2
    ;;
esac

if [[ ! -f scripts/render-config.sh || ! -f .env.example ]]; then
  echo "error: run from the repository root with the repository mounted at /work" >&2
  exit 1
fi

if [[ "$action" != "prepare" ]]; then
  exec bash "scripts/$action.sh"
fi

bash scripts/render-config.sh
bash scripts/generate-cert.sh
bash scripts/setup-host.sh
if [[ "$with_ftp" == true ]]; then
  bash scripts/add-ftpsrv.sh
fi
bash scripts/verify.sh

echo "Preparation complete. Start the services with: docker compose up -d"
