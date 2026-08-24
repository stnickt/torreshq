# torreshq.com

The Torres family site, meant to be hosted on the family Raspberry Pi
(`192.168.0.20`) as `torreshq.com`. Kid-specific subpages (Brandon's, etc.)
are planned to live under this later.

## Structure

```
site/               static site (edit index.html / assets/style.css / assets/script.js)
backend/             small Flask API that emails access requests via SMTP
Dockerfile          builds an nginx image serving site/
nginx.conf          nginx server block (gzip, cache headers, proxies /api/ to backend)
docker-compose.yml  runs both containers, site published on :8090 (LAN-accessible)
deploy/deploy.sh     rsyncs the repo to the Pi and rebuilds the containers
.env.example         template for the backend's SMTP credentials (copy to .env on the Pi)
data/                SQLite DB of access requests, created on first run (gitignored)
```

## Customize the content

Edit `site/index.html` directly:

- Tagline and hero text
- Links section (Instagram href)
- Minecraft server addresses, hosted on the Mac mini — Java (`#mc-java-address`,
  currently `mcjava.torreshq.com`, no port needed) and Bedrock
  (`#mc-bedrock-address` / `#mc-bedrock-port`, currently `mcbedrock.torreshq.com`
  port `49980` — Bedrock has no SRV-record shortcut, so the port must be kept
  in sync with whatever playit.gg assigns the Bedrock tunnel)

## Preview locally

Just open `site/index.html` in a browser, or serve it:

```bash
cd site && python3 -m http.server 8000
```

Note the "Request Access" form won't work this way since it needs the backend
+ nginx proxy — test that through the full Docker setup instead (see below).

## Backend setup (Request Access emails)

The Minecraft access-request form POSTs to `/api/request-access`, which nginx
proxies to a small Flask service (`backend/`) that sends the email itself via
SMTP — no third-party form relay involved.

On the Pi, create a `.env` file in the repo root (never committed — it's in
`.gitignore`) based on `.env.example`:

```bash
cp .env.example .env
```

Then fill in:

- `SMTP_USER` — the Gmail account that sends the mail. Needs a
  [Google App Password](https://myaccount.google.com/apppasswords) (requires
  2-Step Verification enabled), not the normal account password.
- `SMTP_PASS` — that app password.
- `TO_EMAIL` — where requests should land (`stnickt@gmail.com`).
- `PUBLIC_BASE_URL` — `https://torreshq.com`, used to build the Accept/Deny
  links in the email.
- `RCON_HOST` / `RCON_PORT` / `RCON_PASSWORD` — see "Accept/Deny and the
  whitelist" below. Optional — leave unset to skip whitelist automation.
- `ADMIN_API_KEY` — required for `GET /api/requests` (returns all requests as
  JSON, used by the mccontroller panel's grid view). Generate with
  `openssl rand -hex 32`; the endpoint always returns 403 without it.

`docker compose up -d --build` picks up `.env` automatically for the
`backend` service. If it's missing, the backend container will fail to start
(`SMTP_USER`/`SMTP_PASS` are required env vars).

Every request is also saved to a SQLite database at `data/requests.db`
(bind-mounted into the container, so it survives rebuilds), including its
`status` (`pending` / `accepted` / `denied` / `accept_failed`). To view
entries, run this from the repo root on the Pi:

```bash
sqlite3 data/requests.db "SELECT * FROM requests ORDER BY created_at DESC;"
```

If `sqlite3` isn't installed on the Pi, install it with
`sudo apt install sqlite3`, or query it from inside the container instead:

```bash
docker compose exec backend python3 -c "
import sqlite3
for row in sqlite3.connect('/app/data/requests.db').execute('SELECT * FROM requests ORDER BY created_at DESC'):
    print(row)
"
```

### Accept/Deny and the whitelist

The access-request email includes **Accept** and **Deny** buttons. Clicking
one opens a confirmation page (`/api/request-access/<id>/review`) — nothing
happens until you actually click "Confirm" there, so email link-scanners
(Outlook Safe Links, etc.) prefetching the link can't accidentally trigger
an action. Confirming Deny just marks the request denied. Confirming Accept
runs `whitelist add <username>` on the Minecraft server over RCON.

For that automation to work, RCON needs to be enabled on the Mac mini
running the server — in its `server.properties`:

```
enable-rcon=true
rcon.port=25575
rcon.password=<a strong password>
```

Then set `RCON_HOST` (the Mac mini's LAN IP or hostname), `RCON_PORT`, and
`RCON_PASSWORD` (matching the value above) in `.env`. If these are left
unset, or the server is unreachable when you click Accept, the request is
still marked `accept_failed` and the page tells you to whitelist the
username manually — nothing fails silently.

### Listing requests for mccontroller

`GET /api/requests` returns every request as JSON (id, name, grade,
minecraft_username, created_at, status — no tokens), for the mccontroller
panel's grid view. Requires the `X-Admin-Key` header to match `ADMIN_API_KEY`;
returns 403 otherwise. Example:

```bash
curl -H "X-Admin-Key: <value from .env>" https://torreshq.com/api/requests
```

## Deploy to the Pi

Requires SSH access and Docker + the Compose plugin installed on the Pi.

```bash
./deploy/deploy.sh pi@192.168.0.20
```

This rsyncs the repo to `~/apps/torreshq` on the Pi and runs
`docker compose up -d --build`, which starts the site on port `8090`,
reachable from any device on the LAN at `http://192.168.0.20:8090`.

## Going live (already set up)

`torreshq.com` is live via a **Cloudflare Tunnel** (the Cloudflared Home
Assistant add-on, tunnel name `TorresHome`) that runs on the Home Assistant
box (`192.168.0.174`) — a *different* machine from this site's Pi
(`192.168.0.20`). DNS records for `torreshq.com` and `www.torreshq.com` are
Tunnel-routed (Proxied) in Cloudflare, and the add-on's Additional Hosts list
maps:

```
torreshq.com -> http://192.168.0.20:8090
```

Because the tunnel reaches the site over the LAN from a separate device
(not from the Pi itself), `docker-compose.yml` must keep publishing `8090`
on all interfaces (`"8090:80"`), not just `127.0.0.1` — binding to localhost
would cut the tunnel off from reaching it. The site is still not directly
exposed to the internet; only traffic routed through the Cloudflare Tunnel
reaches it from outside your LAN.

Other `*.torreshq.com` subdomains (`hass`, `frigate`, `mccontroller`,
`blake`, `brandon`, `minecraft`) are routed the same way to their own
services, so this site's rule only claims `torreshq.com`/`www.torreshq.com`
and doesn't touch the others.

If the tunnel or Additional Hosts config ever needs changing, that's done in
the Cloudflared add-on's Options page in Home Assistant, not in this repo.
