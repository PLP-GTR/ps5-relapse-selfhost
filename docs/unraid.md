# Unraid deployment

The project supports three deployment options. Standalone hosting remains the default. All commands and file paths below are relative to the repository root.

| Option | Guide HTTPS address | Backend web ports |
|--------|---------------------|-------------------|
| 1. Standalone (default) | Unraid host IP | 80 / 443 |
| 2. NPM shares Unraid's IP | Unraid host IP | 8080 / 8443, or other free ports |
| 3. NPM has its own LAN IP | NPM's IP (`GUIDE_IP`) | Free ports on the Unraid host |

`SERVER_IP` is always the Unraid host's LAN IPv4 address, where the DNS service runs and web ports are published. `GUIDE_IP` is the address returned for the three guide hostnames; it defaults to `SERVER_IP` when unset or empty. Set the PS5's DNS to `SERVER_IP` in all three options.

## 1. Standalone hosting (default)

Follow the [main quick start](../README.md#quick-start) when host ports **53 (UDP/TCP), 80, and 443** are free. The default web port settings are:

```dotenv
WEB_HTTP_PORT=80
WEB_HTTPS_PORT=443
```

Leave `GUIDE_IP` unset. The PS5 connects directly to the web container without a reverse proxy.

## 2. Nginx Proxy Manager shares Unraid's IP

If NPM owns **80/443** on the Unraid host's IP, change these values in `.env` before starting the stack:

```dotenv
WEB_HTTP_PORT=8080
WEB_HTTPS_PORT=8443
```

Leave `GUIDE_IP` unset so guide domains resolve to `SERVER_IP`. This publishes the backend on `8080:80` and `8443:443`, leaving **80/443** to NPM. If those backend ports are occupied, choose free ports and use the matching HTTP port in NPM. Then follow the shared NPM setup below.

## 3. Nginx Proxy Manager has its own LAN IP

Use this option when NPM runs on a custom network such as `br0` with its own LAN IP. For an Unraid host at **192.168.0.13** and NPM at **192.168.0.14**, set:

```dotenv
SERVER_IP=192.168.0.13
GUIDE_IP=192.168.0.14
WEB_HTTP_PORT=18080
WEB_HTTPS_PORT=18443
```

These example backend ports avoid the **8080** port already used by qBittorrent in this layout. Confirm **18080/18443** and DNS port **53 (UDP/TCP)** are available on the host.

| Purpose | Address |
|---------|---------|
| PS5's DNS server | `192.168.0.13:53` |
| DNS answer for each guide hostname | `192.168.0.14` |
| PS5's guide HTTPS connection | `192.168.0.14:443` (NPM) |
| NPM's HTTP upstream | `192.168.0.13:18080` |
| Direct backend HTTPS for diagnostics | `192.168.0.13:18443` |

```text
PS5 --DNS--> 192.168.0.13:53
             guide domains resolve to 192.168.0.14
PS5 --HTTPS--> NPM 192.168.0.14:443
               --HTTP--> Relapse backend 192.168.0.13:18080
```

Keep `SERVER_IP` set to the Unraid host IP; `GUIDE_IP` only changes the guide-domain DNS answers. Existing Cloudflare records for your own domains can stay as they are. The Sony guide hostnames are redirected by the local DNS service.

NPM must be able to reach the chosen backend address. Existing proxy hosts forwarding to `192.168.0.13` demonstrate the required route. If they use different upstream addresses, verify this route before relying on it; no Docker network change is required when it already works.

## Shared setup for both NPM options

Complete the file preparation from the [main quick start](../README.md#quick-start), using your selected `.env` values before rendering or starting containers. For an existing installation, apply the settings with:

```bash
./scripts/render-config.sh
docker compose up -d
docker compose restart dns
```

Restarting DNS makes dnsmasq read the new guide-domain answers even if its Compose service definition is unchanged. NPM handles client ports **80/443**; the backend retains its internal ports **80/443** and uses your configured published ports on the host.

After starting the stack, configure NPM:

1. Under **SSL Certificates**, add a **Custom** certificate. Upload `certs/manuals.crt` as the certificate and `certs/manuals.key` as its key. This uses NPM's [custom certificate support](https://nginxproxymanager.com/guide/); use the generated certificate rather than requesting a Let's Encrypt certificate for Sony's domains.
2. Add a **Proxy Host** with all three domain names: `manuals.playstation.net`, `manual.playstation.net`, and `doc.dl.playstation.net`.
3. Set **Scheme** to `http`, **Forward Hostname / IP** to `SERVER_IP`, and **Forward Port** to `WEB_HTTP_PORT`. For option 3's example, this is `192.168.0.13:18080`. Leave **Cache Assets** disabled and keep the request path unchanged.
4. In the proxy host's **SSL** tab, select the uploaded certificate. NPM receives the PS5's HTTPS connection on **443** and forwards HTTP to the backend. The published backend HTTPS port is available for direct TLS checks.
5. Apply an IP-based **Access List** allowing the PS5 and trusted admin devices, especially if NPM's ports are forwarded from the internet. Avoid username/password authentication for this proxy host so the PS5 can load it directly.

The backend retains the deep-path fallback, asset rewrites, JavaScript/CSS 404 handling, and `Cache-Control: no-store`. Keep these rules in the backend configuration.

Check option 3's example from a LAN computer (replace addresses and ports for your deployment):

```bash
nslookup manuals.playstation.net 192.168.0.13
curl -I http://192.168.0.13:18080/src/firmware.js
curl -k --resolve manuals.playstation.net:443:192.168.0.14 \
  https://manuals.playstation.net/document/en/ps5/
```

Expect the DNS answer **192.168.0.14**, an HTTP **200** for the script, and the host page HTML through HTTPS. The `--resolve` check tests NPM independently of DNS, while `nslookup` checks the DNS redirect. If NPM returns **502**, check its access to `SERVER_IP:WEB_HTTP_PORT` and confirm the web container is running. Set the PS5's DNS to `SERVER_IP` after completing the proxy configuration.

## Optional: Unraid host nginx (legacy)

For **Nginx Proxy Manager**, use the proxy-host instructions above. It runs separately from Unraid's management nginx and does not require `unraid/apply-nginx.sh`.

The legacy script edits Unraid's own nginx configuration. It has a known marker-matching bug that can delete unrelated trailing configuration when rerun; avoid it until that is fixed. The template in `unraid/` remains available as a reference for manually managed deployments.
