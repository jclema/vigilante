# Google Cloud pilot checklist

## 1. Create the project

1. Create `vigilante-pilot` in Google Cloud.
2. Attach billing.
3. Pick `us-central1` as the main region.

## 2. Enable APIs

- Cloud Run Admin API
- Artifact Registry API
- Cloud Build API
- Firestore API
- Cloud Storage API
- Secret Manager API
- Cloud Scheduler API
- Pub/Sub API
- Places API
- Vision API
- Business Profile API
- Vertex AI API only if Gemini is enabled

## 3. Create identities

- `vigilante-runtime`
- `vigilante-deploy`

Grant least-privilege roles for:

- Run
- Storage
- Firestore
- Secret Manager
- Pub/Sub
- Logging

## 4. Provision storage

- Firestore in native mode
- Evidence bucket with 30-day lifecycle
- Pub/Sub topic for GBP events

## 5. Prepare secrets

- `GOOGLE_MAPS_API_KEY`
- `GOOGLE_GBP_WEBHOOK_SECRET`
- `DASHBOARD_USERNAME`
- `DASHBOARD_PASSWORD`
- `ALERT_WEBHOOK_URL`
- Gemini credentials only if used

## 6. Configure GBP partial access

1. Link Motoblu Bello and Motoblu Itagui accounts.
2. Confirm location IDs.
3. Point GBP notifications to Pub/Sub.
4. Route Pub/Sub delivery to `/api/webhooks/gbp`.

## 7. Deploy

1. Build image.
2. Push to Artifact Registry.
3. Deploy Cloud Run.
4. Set env vars and secrets.
5. Validate the home dashboard and `/api/scans/run`.

## 8. Schedule scans

- Create hourly scan job for the public mode.
- Use authenticated HTTP target with OIDC.

## 9. Validate pilot

- Trigger one public scan.
- Simulate one GBP event.
- Confirm case creation.
- Confirm dashboard updates.
- Confirm report generation.
