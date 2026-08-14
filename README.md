# brandon.torreshq.com

Personal landing page for Brandon, meant to be hosted on the family Raspberry Pi
(`192.168.0.20`) as `brandon.torreshq.com`.

## Structure

```
site/               static site (edit index.html / assets/style.css / assets/script.js)
backend/             small Flask API that emails access requests via SMTP
Dockerfile          builds an nginx image serving site/
nginx.conf          nginx server block (gzip, cache headers, proxies /api/ to backend)
docker-compose.yml  runs both containers, site published on :8090 (LAN-accessible)
deploy/deploy.sh     rsyncs the repo to the Pi and rebuilds the containers
.env.example         template for the backend's SMTP credentials (copy to .env on the Pi)
```

## Customize the content

Edit `site/index.html` directly:

- Tagline and about text
- Links section (Instagram href)
- Minecraft server address (`#mc-address`, hosted on the Mac mini — currently
  `minecraft.torreshq.com`)
- Contact email

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

## Deploy to the Pi

Requires SSH access and Docker + the Compose plugin installed on the Pi.

```bash
./deploy/deploy.sh pi@192.168.0.20
```

This rsyncs the repo to `~/apps/brandon-torreshq` on the Pi and runs
`docker compose up -d --build`, which starts the site on port `8090`, reachable
from any device on the LAN at `http://192.168.0.20:8090` — handy for previewing
while you're filling in content.

Once you're ready to go live on the real domain, point whatever reverse proxy
already terminates TLS and routes `*.torreshq.com` subdomains on the Pi (e.g.
Nginx Proxy Manager, Caddy, or a Cloudflare Tunnel) at `127.0.0.1:8090`, and
switch the port mapping in `docker-compose.yml` back to
`"127.0.0.1:8090:80"` so the site is no longer exposed directly on the LAN.
For example, with a plain Caddy reverse proxy:

```
brandon.torreshq.com {
    reverse_proxy 127.0.0.1:8090
}
```

Also add/confirm a DNS record for `brandon.torreshq.com` pointing at wherever
`torreshq.com`'s other subdomains resolve (the Pi's public IP or the tunnel,
depending on how the rest of the site is set up).
