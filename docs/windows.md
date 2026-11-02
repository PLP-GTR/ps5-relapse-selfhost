# Testing with a PS5 from Windows

Use Docker Desktop with Linux containers. The optional `docker-compose.windows.yml` file replaces host-network DNS with bridge networking and publishes UDP/TCP port **53** on the configured Windows LAN address. The default Linux and Unraid deployment remains unchanged.

## Configure the PC

Run `ipconfig` in PowerShell and find the IPv4 address of the Ethernet or Wi-Fi adapter on the same LAN as the PS5. In your local `.env`, replace both placeholders below with that address and keep the other settings:

```dotenv
SERVER_IP=<PC_LAN_IP>
#GUIDE_IP=
WEB_HTTP_PORT=80
WEB_HTTPS_PORT=443
```

The User's Guide connects to HTTPS port **443**. Alternative ports are suitable for direct browser testing, but DNS does not change the port in the guide URL. Keep the PC and PS5 on the same LAN without guest-network client isolation. Host ports **53 (UDP/TCP), 80, and 443** must be available on the selected LAN address.

Prepare files and start both services from the repository root:

```powershell
docker compose run --rm --build setup
docker compose -f docker-compose.yml -f docker-compose.windows.yml config -q
docker compose -f docker-compose.yml -f docker-compose.windows.yml up -d --force-recreate
```

Binding DNS to the specific LAN address can coexist with some Windows services listening on a wildcard address. If Docker still reports port 53 unavailable, identify the conflicting service before proceeding. Windows sharing and WSL networking can depend on that listener; changing the DNS port will not help because the PS5 queries port 53.

## Allow LAN connections

For a trusted home network, verify that the Windows adapter uses the **Private** network profile. In an administrator PowerShell window, add rules restricted to the local subnet:

```powershell
New-NetFirewallRule -DisplayName "Relapse PS5 test TCP" -Group "Relapse PS5 test" -Direction Inbound -Action Allow -Protocol TCP -LocalPort 53,80,443 -Profile Private -RemoteAddress LocalSubnet
New-NetFirewallRule -DisplayName "Relapse PS5 test DNS UDP" -Group "Relapse PS5 test" -Direction Inbound -Action Allow -Protocol UDP -LocalPort 53 -Profile Private -RemoteAddress LocalSubnet
```

## Optional: Check the route

From another LAN computer, replace `<PC_LAN_IP>` with the Windows PC's address:

```powershell
nslookup manuals.playstation.net <PC_LAN_IP>
curl.exe -k --resolve manuals.playstation.net:443:<PC_LAN_IP> https://manuals.playstation.net/document/en/ps5/
```

Expect the DNS answer to be the PC's LAN IP and the HTTPS response to contain the host page. The `--resolve` check tests HTTPS independently of the DNS service.

## Connect the PS5

Set the PS5's primary DNS to the PC's LAN IP.

Settings → Network → Settings → Set Up Internet Connection → Press [`OPTIONS`]-Button → Advanced Settings

DNS Settings: Manual \
Primary DNS: `{SERVER_IP}` (same as in .env file) \
Secondary DNS: `0.0.0.0`

Open Settings → Guide & Tips, Health and Safety, and Other Information → **User's Guide**. Accept the provided certificate with **Yes**.

Follow the host page's instructions: **START**. \
After the exploit did it's job, visit the debug settings.

## Logs

Inspect startup errors with:

```powershell
docker compose -f docker-compose.yml -f docker-compose.windows.yml ps
docker compose -f docker-compose.yml -f docker-compose.windows.yml logs --tail 80 dns web
```

## Stop the Windows test

```powershell
docker compose -f docker-compose.yml -f docker-compose.windows.yml down
```

Restore the PS5's previous DNS settings after stopping its temporary DNS server. To remove the temporary firewall rules, run this in administrator PowerShell:

```powershell
Get-NetFirewallRule -Group "Relapse PS5 test" | Remove-NetFirewallRule
```

For deployment on Unraid, use the [Unraid guide](unraid.md), set `.env` to the intended server/proxy addresses, rerun setup, and start the regular `docker-compose.yml` without the Windows override.
