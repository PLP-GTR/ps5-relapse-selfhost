# PS5 Relapse self-host

Package a home-server DNS + HTTPS host for the **PS5 Relapse** exploit chain (firmware **7.00–13.60**), so the console’s **User’s Guide** loads your page instead of Sony’s manual.

This repository **does not** vendor exploit code, payloads, certificates, or keys. It clones an upstream host page at setup time and applies a small overlay that matches a known-good working page.

Upstream projects:

- [ntfargo/Relapse-Exploit](https://github.com/ntfargo/Relapse-Exploit) — exploit chain
- [arg0WAK/WAK1360-Relapse](https://github.com/arg0WAK/WAK1360-Relapse) — UI host page (default clone target, pinned commit)
- [ps5-payload-dev/ftpsrv](https://github.com/ps5-payload-dev/ftpsrv) — optional FTP payload (`ftpsrv-ps5.elf`)

> **Disclaimer.** Educational / security-research use on devices you own. Jailbreaking can brick hardware, void warranties, and violate terms of service. You assume the risk.

---

## How it works

```
PS5 ──DNS──► dnsmasq on your server
               │
               ├─ manuals.playstation.net  →  SERVER_IP
               ├─ manual.playstation.net   →  SERVER_IP
               ├─ doc.dl.playstation.net   →  SERVER_IP
               └─ update / patch hosts     →  0.0.0.0  (blocked)

PS5 opens User’s Guide (HTTPS)
  → nginx on SERVER_IP:443 serves the host page
  → START runs the exploit → PAYLOADS (OnionHEN, ShadowMount+, FTP, …)
```

1. **dnsmasq** answers authoritative A records for the User’s Guide hostnames and black-holes Sony update domains so the console stays on its current firmware.
2. **nginx** serves the host page directly on **80 and 443** by default, using the generated self-signed cert for `manuals.playstation.net`.
3. An **overlay** on top of pinned WAK1360 makes the page survive deep User’s Guide paths, aggressive caching, and UA quirks.

---

## Requirements

- Linux host with Docker + Compose v2 (dnsmasq uses `network_mode: host`)
- Free **UDP/TCP 53**, **TCP 80**, **TCP 443** on that host for the default standalone setup
- Ability to set the PS5’s DNS to `SERVER_IP`
- `git` to clone this repository; the setup container supplies Bash, Python, Git, OpenSSL, curl, and checksum tools

macOS / Docker Desktop can build and validate configs, but host-network DNS will not behave the same; run the stack on a Linux box on your LAN.

For a temporary PS5 test using Docker Desktop on Windows, see the [Windows guide](docs/windows.md). It provides an optional Compose override that publishes DNS on the PC's LAN address.

---

## Quick start

```bash
git clone https://github.com/ThatRetiredDude/ps5-relapse-selfhost.git
cd ps5-relapse-selfhost

cp .env.example .env
# edit .env → set SERVER_IP to this machine’s LAN IPv4

docker compose run --rm --build setup
# optional: docker compose run --rm setup add-ftpsrv

docker compose config -q
docker compose up -d
```

### Setup container

The one-off `setup` service renders configuration, generates the TLS certificate, clones the pinned host page, applies the overlay, and runs the file checks. It writes generated files into the bind-mounted repository, so they persist after the helper exits. A normal `docker compose up -d` starts only DNS and web; their mounts remain read-only.

To include the optional FTP payload in the preparation run:

```bash
docker compose run --rm --build setup prepare --with-ftp
```

Individual commands are also available:

| Command after `docker compose run --rm setup` | Script |
|---------------------------------------------|--------|
| `render-config` | `scripts/render-config.sh` |
| `generate-cert` | `scripts/generate-cert.sh` |
| `setup-host` | `scripts/setup-host.sh` |
| `add-ftpsrv` | `scripts/add-ftpsrv.sh` |
| `verify` | `scripts/verify.sh` |
| `help` | Show helper usage |

The helper has no Docker socket or published ports. Its `verify` command checks prepared files; run `docker compose config -q` on the host to validate Compose. Build dependencies are installed in the helper image, while downloads and certificates are created when the helper runs. The build context contains only `docker/setup/`.

For existing Windows checkouts, the helper converts CRLF line endings to LF in `scripts/*.sh` and `.env` before running Bash. This updates those bind-mounted files in place while preserving their permissions. `.gitattributes` keeps shell scripts and `.env.example` in LF format for future checkouts.

The helper runs as root by default. To preserve ownership when the repository belongs to a non-root Linux user, run preparation and subsequent helper commands with that user's UID/GID:

```bash
docker compose run --rm --build --user "$(id -u):$(id -g)" setup
```

Host-side preparation remains supported if Bash, Python 3, Git, OpenSSL, curl/wget, and a checksum utility are installed:

```bash
./scripts/render-config.sh
./scripts/generate-cert.sh
./scripts/setup-host.sh
# optional: ./scripts/add-ftpsrv.sh
./scripts/verify.sh
```

### Standalone hosting (default)

The quick start serves the page directly on `SERVER_IP:80` and `SERVER_IP:443`. The default settings are `WEB_HTTP_PORT=80` and `WEB_HTTPS_PORT=443`; those host ports must be free. No reverse proxy is required. Continue with the PS5 DNS settings below.

For Unraid deployments, including Nginx Proxy Manager on the same or a separate LAN IP, see the [Unraid guide](docs/unraid.md). The optional `GUIDE_IP` setting redirects guide domains to a separate proxy while `SERVER_IP` remains the DNS server and backend address.

### Point DNS at the server

**Option A — PS5 only**

Settings → Network → Set Up Internet Connection → Custom → DNS. Primary = `SERVER_IP`. Leave secondary DNS unset or `0.0.0.0`.

**Option B — whole LAN (optional)**

Set your router’s DHCP DNS to `SERVER_IP` so every device (including the PS5) uses dnsmasq. Upstream resolvers in `.env` handle everything that isn’t overridden.

### On the PS5

1. Confirm firmware is in the supported range (7.00–13.60) and stays there (update hosts are blocked).
2. Open **User’s Guide** (the book icon). You should see the Relapse / WAK host page, not Sony’s manual.
3. Press **START**. After a successful run, use **PAYLOADS** (OnionHEN, ShadowMount+, FTP, ProsperoStore, etc.).

---

## Overlay (what `setup-host.sh` applies)

Default `HOST_REF` pins [WAK1360-Relapse](https://github.com/arg0WAK/WAK1360-Relapse) at commit `b2398fd5bea116f990595e0a187ae94d8c6db43d`. Files under `overlay/` are copied on top:

| File | Purpose |
|------|---------|
| `overlay/index.html` | `<base href="/">`, `?v=4` cache-bust on **all** scripts, includes `force-ready.js` |
| `overlay/src/firmware.js` | More tolerant UA / firmware detection + clearer rejection text |
| `overlay/src/helper.js` | Logs UA; shows the real rejection string when incompatible |
| `overlay/src/force-ready.js` | Marks the UI READY when the UA looks like a PlayStation |

`overlay/payloads.json` (with the FTP Server entry) is applied by `scripts/add-ftpsrv.sh`, not by `setup-host.sh`.

---

## Optional: FTP payload

```bash
docker compose run --rm --build setup add-ftpsrv
```

Downloads [`ftpsrv-ps5.elf`](https://github.com/ps5-payload-dev/ftpsrv/releases/download/v0.21.1/ftpsrv-ps5.elf) from the official [ps5-payload-dev/ftpsrv](https://github.com/ps5-payload-dev/ftpsrv) **v0.21.1** release, verifies SHA-256 `7d4b31c8…`, installs it into `www/payloads/`, and writes `payloads.json` with the FTP Server entry (port **2121**). The ELF is **never** committed to this repo.

If the release URL is unreachable, download that asset by hand into `www/payloads/ftpsrv-ps5.elf` and copy `overlay/payloads.json` over `www/payloads/payloads.json`.

---

## The gotchas (why this package exists)

### 1. HTTPS on port 443

The User’s Guide loads over **HTTPS**. Serving only port 80 is not enough.

### 2. SPA fallback silently kills `firmware.js`

If nginx falls back to `index.html` for missing `.js` files, a bad path returns HTML with HTTP 200 and the exploit dies silently. This package makes `.js` / `.css` return a real **404**.

### 3. Deep User’s Guide paths are handled on the server

The Guide opens URLs like `/document/en/ps5/…`. nginx rewrites nested `/src/` and `/assets/` requests back to the site root, and `try_files` serves `index.html` for the deep HTML path. The overlay still includes `<base href="/">` as an optional client-side backup.

### 4. The PS5 browser caches aggressively

nginx sends `Cache-Control: no-store`, and the overlay uses `?v=4` on script tags.

### 5. ShadowMount+ only scans when it starts

Re-run ShadowMount+ from PAYLOADS after installing new titles.

### 6. Autoload ShadowMount+ and FTP

Configure autoload in `payloads.json` (order = injection priority). See upstream docs.

### 7. OnionHEN + homebrew title IDs

Homebrew may need a correct `param.json` and an OnionHEN config entry, or you get a generic error dialog.

### 8. Plain HTTP containers on a side port are not enough

Publishing the same files on an alternate HTTP port (for example **:8765**) without the SPA `try_files` fallback will **404** on `/document/en/ps5/`. The PS5 User’s Guide talks to **HTTPS :443** on `manuals.playstation.net`. The default Compose setup serves that port directly. For reverse proxy deployment, see the [Unraid guide](docs/unraid.md).

---

## Layout

```
├── docker-compose.yml
├── docker-compose.windows.yml   # optional Docker Desktop DNS port mappings
├── docker/setup/                # one-off preparation image and entrypoint
├── .env.example
├── docs/unraid.md        # Unraid deployment and optional NPM setup
├── overlay/                    # exact page files applied onto pinned WAK1360
│   ├── index.html
│   ├── payloads.json           # used by add-ftpsrv.sh
│   └── src/{firmware,helper,force-ready}.js
├── dnsmasq/dnsmasq.conf.template
├── nginx/default.conf.template
├── unraid/
│   ├── relapse-nginx.conf.template   # host-nginx drop-in (templated IP)
│   └── apply-nginx.sh
├── scripts/
│   ├── render-config.sh
│   ├── generate-cert.sh
│   ├── setup-host.sh
│   ├── add-ftpsrv.sh
│   └── verify.sh
├── tests/test_setup.py          # offline setup integration checks
└── README.md
```

Generated / cloned (gitignored): `.env`, rendered configs, `certs/`, `www/`.

---

## Updating the host page

```bash
docker compose run --rm --build setup
docker compose restart dns web
```

If you use FTP, run `docker compose run --rm --build setup prepare --with-ftp` instead of the plain setup command. Refreshing the upstream clone removes the locally added FTP payload, so it must be installed again.

To move the pin, set `HOST_REF` in `.env` and refresh the overlay files so they still apply cleanly.

---

## Testing the setup helper

Run the offline integration checks with the helper's toolchain:

```bash
docker compose run --rm --build --entrypoint python3 setup -B -m unittest discover -s tests -v
```

The tests use a temporary local Git repository and inert payload fixtures; they do not download or execute exploit code. They can also run on a host with the preparation tools installed using `python3 -B -m unittest discover -s tests -v`. Set `BASH_BIN` to the Bash executable when it is not available as `bash` on `PATH`.

---

## Security notes

- The self-signed cert is only so the PS5 browser can speak TLS to **you**. Do not reuse it elsewhere.
- dnsmasq on this host becomes a DNS oracle for anyone pointed at it — keep it on a trusted LAN.
- Payloads (`*.elf`, `*.bin`) come from upstream clones / release downloads and stay in `www/` (gitignored). **Never commit them.**
- This repo deliberately contains **no** exploit sources.

---

## Upstream contributions

Broader firmware/UA detection and on-screen rejection text are offered upstream as:

https://github.com/arg0WAK/WAK1360-Relapse/pull/1

Deep Guide path rewrites, `<base href="/">`, `force-ready.js`, DNS, Unraid drop-ins, and ftpsrv wiring stay in this kit (server / self-host layer).

## Credits

- Relapse exploit chain: Sonic_Iso, Jordy, ntfargo, ufm42, Dr. Yenyen, and others listed in [ntfargo/Relapse-Exploit](https://github.com/ntfargo/Relapse-Exploit)
- WAK1360 host UI: [arg0WAK/WAK1360-Relapse](https://github.com/arg0WAK/WAK1360-Relapse)
- ftpsrv: [ps5-payload-dev/ftpsrv](https://github.com/ps5-payload-dev/ftpsrv)
- Other payload authors (OnionHEN, ShadowMount+, etc.) — see their respective projects

---

## License

Packaging and scripts in this repository are provided as-is, without warranty. Upstream exploit and host-page licenses apply to material cloned into `www/`.
