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
- Minecraft server address (`#mc-address`, hosted on the Mac mini — currently
  `minecraft.torreshq.com`)

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

`docker compose up -d --build` picks up `.env` automatically for the
`backend` service. If it's missing, the backend container will fail to start
(`SMTP_USER`/`SMTP_PASS` are required env vars).

Every request is also saved to a SQLite database at `data/requests.db`
(bind-mounted into the container, so it survives rebuilds). To view entries,
run this from the repo root on the Pi:

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

## Deploy to the Pi

Requires SSH access and Docker + the Compose plugin installed on the Pi.

```bash
./deploy/deploy.sh pi@192.168.0.20
```

This rsyncs the repo to `~/apps/torreshq` on the Pi and runs
`docker compose up -d --build`, which starts the site on port `8090`, reachable
from any device on the LAN at `http://192.168.0.20:8090` — handy for previewing
while you're filling in content.

Once you're ready to go live on the real domain, point whatever reverse proxy
already terminates TLS on the Pi (e.g. Nginx Proxy Manager, Caddy, or a
Cloudflare Tunnel) at `127.0.0.1:8090`, and switch the port mapping in
`docker-compose.yml` back to `"127.0.0.1:8090:80"` so the site is no longer
exposed directly on the LAN. For example, with a plain Caddy reverse proxy:

```
torreshq.com, www.torreshq.com {
    reverse_proxy 127.0.0.1:8090
}
```

Also add/confirm DNS for the apex domain: an **A record** for `torreshq.com`
itself (not a CNAME — most DNS providers don't allow CNAMEs at the apex)
pointing at the Pi's public IP, or the equivalent your provider offers for
apex records (e.g. Cloudflare's proxied "A"/CNAME flattening, or an
ALIAS/ANAME record). Add `www.torreshq.com` as a CNAME to `torreshq.com` if
you want the `www.` version to work too.

If anything currently lives at `torreshq.com` (or other `*.torreshq.com`
subdomains on the same reverse proxy), make sure this site's rule doesn't
collide with it — this config only claims `torreshq.com` and
`www.torreshq.com`, leaving other subdomains alone.
