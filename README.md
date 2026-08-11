# brandon.torreshq.com

Personal landing page for Brandon, meant to be hosted on the family Raspberry Pi
(`192.168.0.20`) as `brandon.torreshq.com`.

## Structure

```
site/               static site (edit index.html / assets/style.css / assets/script.js)
Dockerfile          builds an nginx image serving site/
nginx.conf          nginx server block (gzip, cache headers)
docker-compose.yml  runs the container, published on 127.0.0.1:8081
deploy/deploy.sh     rsyncs the repo to the Pi and rebuilds the container
```

## Customize the content

Edit `site/index.html` directly:

- Tagline and about text
- Links section (GitHub/LinkedIn/Instagram hrefs)
- Minecraft server address (`#mc-address`, hosted on the Mac mini — update the
  hostname/port if it's not `mc.torreshq.com`)
- Contact email

## Preview locally

Just open `site/index.html` in a browser, or serve it:

```bash
cd site && python3 -m http.server 8000
```

## Deploy to the Pi

Requires SSH access and Docker + the Compose plugin installed on the Pi.

```bash
./deploy/deploy.sh pi@192.168.0.20
```

This rsyncs the repo to `~/apps/brandon-torreshq` on the Pi and runs
`docker compose up -d --build`, which starts the site on `127.0.0.1:8081`.

The container only binds to localhost on the Pi on purpose — it's meant to sit
behind whatever reverse proxy already terminates TLS and routes
`*.torreshq.com` subdomains on that box (e.g. Nginx Proxy Manager, Caddy, or a
Cloudflare Tunnel), rather than being exposed directly. Point that proxy's
`brandon.torreshq.com` entry at `127.0.0.1:8081`. For example, with a plain
Caddy reverse proxy:

```
brandon.torreshq.com {
    reverse_proxy 127.0.0.1:8081
}
```

Also add/confirm a DNS record for `brandon.torreshq.com` pointing at wherever
`torreshq.com`'s other subdomains resolve (the Pi's public IP or the tunnel,
depending on how the rest of the site is set up).
