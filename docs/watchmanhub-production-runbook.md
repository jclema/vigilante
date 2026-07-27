# WatchmanHub production runbook

## Developer viewer access

Developer collaborators who need to understand the production product use the
application-level `developer_viewer` role. This role is network-wide and
read-only. It does not grant Google Cloud, Firestore console, Secret Manager,
Cloudflare, deployment, integration administration, reporting, or enforcement
permissions.

Run the provisioning command first without `--apply`, then repeat it with
`--apply` only after the revision containing the role has been deployed:

```bash
STORAGE_BACKEND=firestore GOOGLE_CLOUD_PROJECT=vigilante-pilot \
  python -m scripts.provision_developer_viewer \
  --full-name "Trystan Jaquet" \
  --email "trystan.jaquet@gmail.com"

STORAGE_BACKEND=firestore GOOGLE_CLOUD_PROJECT=vigilante-pilot \
  python -m scripts.provision_developer_viewer \
  --full-name "Trystan Jaquet" \
  --email "trystan.jaquet@gmail.com" \
  --apply
```

The user signs in through Google at `https://www.watchmanhub.com`. Verify
network dashboards and case reads, confirm `/settings` returns `403`, and
confirm representative POST requests return `403` without side effects.

Revocation is performed by deactivating the user or removing the
`developer_viewer` membership. No secret rotation is required because this
access path does not issue a password, service account, or application secret.

## Public service

- URL: `https://www.watchmanhub.com`
- Health: `https://www.watchmanhub.com/healthz`
- Readiness: `https://www.watchmanhub.com/readyz`
- Google Cloud project: `vigilante-pilot`
- Region: `us-central1`
- Cloud Run service: `vigilante-app`
- Load Balancer IP: `136.68.191.26`

## Request path

```text
Cloudflare
  -> Google Global External Application Load Balancer
  -> Cloud Armor
  -> Serverless NEG
  -> Cloud Run
```

Direct internet access to `run.app` must return `404`.

## First response

```bash
curl -fsS https://www.watchmanhub.com/healthz
curl -fsS https://www.watchmanhub.com/readyz

gcloud run services describe vigilante-app \
  --project=vigilante-pilot \
  --region=us-central1

gcloud logging read \
  'resource.type="cloud_run_revision" AND resource.labels.service_name="vigilante-app" AND severity>=ERROR' \
  --project=vigilante-pilot \
  --freshness=30m \
  --limit=50
```

Check Cloudflare DNS and proxy status if health succeeds against the Load
Balancer but the public hostname fails.

## Rollback

List healthy revisions:

```bash
gcloud run revisions list \
  --service=vigilante-app \
  --project=vigilante-pilot \
  --region=us-central1
```

Route traffic to the last known-good revision:

```bash
gcloud run services update-traffic vigilante-app \
  --to-revisions=REVISION_NAME=100 \
  --project=vigilante-pilot \
  --region=us-central1
```

Do not disable Cloudflare, weaken ingress, expose `run.app`, or remove Cloud
Armor as a first response.

## Security checks

```bash
curl -o /dev/null -sS -w '%{http_code}\n' \
  https://vigilante-app-580644425192.us-central1.run.app/login

gcloud compute security-policies describe watchmanhub-edge-policy \
  --project=vigilante-pilot
```

Expected direct Cloud Run response: `404`.

Cloud Armor SQLi and XSS rules stay in preview until Load Balancer logs show
representative traffic without legitimate matches. Promote one rule at a time
and keep rollback commands ready.

## Monitoring

- Uptime check: `WatchmanHub public health`, every 60 seconds.
- Alert policy: `WatchmanHub public unavailable`, after 120 seconds.
- Notification channels must be configured separately for the operating team.
