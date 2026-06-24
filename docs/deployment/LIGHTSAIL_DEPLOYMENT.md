# AWS Lightsail Deployment

Deploys the real CounterOS POS app on one Ubuntu Lightsail instance:

- Nginx public port `80`
- Next.js frontend on `127.0.0.1:3000`
- FastAPI backend on `127.0.0.1:8000`
- Browser API calls to same-origin `/api/v1`
- PM2 keeps both processes alive after SSH disconnect and reboot

## Instance

Use Ubuntu 24.04 LTS if available, otherwise Ubuntu 22.04 LTS.

Recommended demo size: Lightsail Linux/Unix general purpose bundle with at least
2 GB RAM. Use 4 GB RAM if several people will use the demo at once or if builds
run on the server. AWS documents Lightsail bundles as fixed plans containing
compute, memory, SSD storage, and transfer allowance. See:

- https://aws.amazon.com/lightsail/pricing/
- https://docs.aws.amazon.com/lightsail/latest/userguide/amazon-lightsail-bundles.html

SQLite is acceptable for this client demo. Production should move to Postgres or
a managed database before real multi-user usage.

## Lightsail Firewall

Open:

- `22/tcp` SSH, restricted to your IP
- `80/tcp` HTTP, public
- `443/tcp` HTTPS, public when TLS is configured

Do not expose `3000` or `8000`; Nginx proxies to localhost. AWS Lightsail
firewall rules are configured in the Lightsail console:

- https://docs.aws.amazon.com/lightsail/latest/userguide/understanding-firewall-and-port-mappings-in-amazon-lightsail.html

## Bootstrap Server

SSH into the instance:

```sh
ssh ubuntu@SERVER_IP
```

Clone the repo:

```sh
sudo mkdir -p /opt/counteros
sudo chown -R "$USER":"$USER" /opt/counteros
cd /opt/counteros
git clone REPO_URL POS-Project
cd POS-Project
```

Install server dependencies:

```sh
chmod +x scripts/deploy/lightsail/*.sh
scripts/deploy/lightsail/install-server.sh
```

The install script:

- updates apt
- installs `git`, `curl`, `nginx`, `python3`, `python3-venv`, `python3-pip`
- installs Node.js LTS via NodeSource
- installs PM2 globally
- creates `/opt/counteros` and `/var/log/counteros`

## Environment

Create backend env:

```sh
cp backend/.env.example backend/.env
nano backend/.env
```

Recommended demo values:

```sh
COUNTEROS_ENV=production
COUNTEROS_HOST=127.0.0.1
COUNTEROS_BACKEND_PORT=8000
COUNTEROS_DATABASE_PATH=/opt/counteros/POS-Project/backend/data/counteros.sqlite3
COUNTEROS_CORS_ORIGINS=http://localhost:3000,http://127.0.0.1:3000
```

Same-origin browser traffic goes through Nginx, so production CORS is normally
not used. Keep localhost origins for local development. Add a domain origin only
if the browser will call the backend directly, which is not the preferred setup.

Create frontend env only if needed:

```sh
cp frontend/.env.example frontend/.env
nano frontend/.env
```

For Lightsail same-origin deployment:

```sh
NEXT_PUBLIC_COUNTEROS_API_BASE_URL=/api/v1
```

For local dev, keep:

```sh
NEXT_PUBLIC_COUNTEROS_API_BASE_URL=http://127.0.0.1:8000/api/v1
```

## Build And Start With PM2

From repo root:

```sh
cd /opt/counteros/POS-Project
pm2 start scripts/deploy/lightsail/ecosystem.config.cjs
pm2 status
pm2 logs
```

Save PM2 process list and enable reboot startup:

```sh
pm2 save
pm2 startup
```

Run the command printed by `pm2 startup`; it usually starts with `sudo env`.

Useful PM2 commands:

```sh
pm2 status
pm2 logs
pm2 restart all
pm2 restart counteros-backend
pm2 restart counteros-frontend
```

The backend script creates/uses `backend/.venv`, installs requirements, runs
database initialization/migrations, then starts Uvicorn on `127.0.0.1:8000`.

The frontend script installs dependencies with `npm ci`, builds Next.js with
`NEXT_PUBLIC_COUNTEROS_API_BASE_URL=/api/v1`, then starts production Next.js on
`127.0.0.1:3000`.

## Configure Nginx

Install the Nginx site:

```sh
sudo cp scripts/deploy/lightsail/nginx-pos.conf /etc/nginx/sites-available/pos
sudo ln -sf /etc/nginx/sites-available/pos /etc/nginx/sites-enabled/pos
sudo rm -f /etc/nginx/sites-enabled/default
sudo nginx -t
sudo systemctl reload nginx
```

Nginx routes:

- `/` to `http://127.0.0.1:3000`
- `/api/v1/` to `http://127.0.0.1:8000/api/v1/`

## Static IP

Attach a Lightsail static IP so the public IP does not change when the instance
is stopped and started:

- https://docs.aws.amazon.com/lightsail/latest/userguide/lightsail-create-static-ip.html

In the Lightsail console:

1. Networking
2. Create static IP
3. Attach it to the instance
4. Use that IP for smoke tests and DNS

## Optional Domain

Create an `A` record:

```text
pos.example.com -> SERVER_STATIC_IP
```

Then edit `server_name` in `/etc/nginx/sites-available/pos`:

```nginx
server_name pos.example.com;
```

Reload:

```sh
sudo nginx -t
sudo systemctl reload nginx
```

Add HTTPS later with Certbot if needed. Keep this deployment HTTP-only until the
demo is stable.

## Smoke Tests

Local on server:

```sh
curl http://127.0.0.1:8000/api/v1/health
curl http://127.0.0.1:8000/api/v1/startup/status
curl -I http://127.0.0.1:3000/startup
```

Public:

```sh
curl http://SERVER_IP/api/v1/health
curl http://SERVER_IP/api/v1/startup/status
curl -I http://SERVER_IP/startup
```

Browser URLs:

- `http://SERVER_IP/startup`
- `http://SERVER_IP/login`
- `http://SERVER_IP/dashboard`
- `http://SERVER_IP/registrations`
- `http://SERVER_IP/api/v1/health`
- `http://SERVER_IP/api/v1/startup/status`

Hospital demo flow:

```text
Login -> Dashboard -> Registration Center -> OP Registration -> Send to Billing -> New Bill
```

## Troubleshooting

Check services:

```sh
pm2 status
pm2 logs counteros-backend
pm2 logs counteros-frontend
```

Check Nginx:

```sh
sudo nginx -t
sudo systemctl status nginx
sudo systemctl reload nginx
sudo tail -n 100 /var/log/nginx/error.log
```

Check ports:

```sh
ss -ltnp | grep -E ':80|:3000|:8000'
```

Check backend health:

```sh
curl http://127.0.0.1:8000/api/v1/health
```

If public `/api/v1/health` fails but local backend works, check Nginx config and
Lightsail firewall port `80`.

If frontend shows API errors, confirm it was built with:

```sh
pm2 restart counteros-frontend
pm2 logs counteros-frontend
```

The production frontend should use `/api/v1`, not `http://127.0.0.1:8000`, in
browser requests.
