# Security Remediation

## Redis public exposure

DigitalOcean reported public Redis access on `45.55.173.72:6379`. The Docker Compose production stack must not publish Redis, Postgres, or internal service ports directly to the host. Only Caddy should publish public ports:

- `80/tcp`
- `443/tcp`

The services still communicate over the internal Docker network by service name, for example `redis:6379` and `postgres:5432`.

## DigitalOcean Cloud Firewall

Use a DigitalOcean Cloud Firewall in front of the Droplet because Docker-published ports can bypass host firewall expectations.

Recommended inbound policy:

- Allow `22/tcp` only from your current trusted admin IP.
- Allow `80/tcp` from all IPv4 and IPv6 sources if the public website remains online.
- Allow `443/tcp` from all IPv4 and IPv6 sources if the public website remains online.
- Do not allow `6379`, `5432`, `8001`, `8007`, `8008`, `8009`, or `8010`.

Recommended outbound policy:

- Allow all outbound TCP, UDP, and ICMP unless a stricter production egress policy is required.

## Deploy the compose hardening

From the Droplet checkout:

```bash
cd /opt/code-chef/deploy
docker compose up -d --remove-orphans
```

If Compose does not recreate containers after port changes, force recreation:

```bash
cd /opt/code-chef/deploy
docker compose up -d --force-recreate --remove-orphans
```

## Verify exposure is closed

Run these checks from outside the Droplet network:

```bash
nc -vz 45.55.173.72 6379
nc -vz 45.55.173.72 5432
nc -vz 45.55.173.72 8001
nc -vz 45.55.173.72 8007
nc -vz 45.55.173.72 8008
nc -vz 45.55.173.72 8009
nc -vz 45.55.173.72 8010
nmap -Pn -p 22,80,443,5432,6379,8001,8007,8008,8009,8010 45.55.173.72
```

The private service ports should be closed or filtered. If the public site remains online, HTTPS should still respond:

```bash
curl -I https://codechef.appsmithery.co
```

On the Droplet, confirm the stack only publishes Caddy:

```bash
cd /opt/code-chef/deploy
docker compose ps
docker ps --format "table {{.Names}}\t{{.Ports}}"
```

## Decommission option

If the project no longer needs a live demo, the lowest-risk option is to stop the stack and power off, snapshot, or destroy the Droplet. The public GitHub repository remains available as the portfolio showcase without any live attack surface.
