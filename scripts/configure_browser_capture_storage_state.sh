#!/usr/bin/env bash
set -euo pipefail

PROJECT_ID="${GOOGLE_CLOUD_PROJECT:-vigilante-pilot}"
REGION="${GOOGLE_CLOUD_REGION:-us-central1}"
JOB_NAME="${JOB_NAME:-vigilante-browser-capture}"
SECRET_NAME="${SECRET_NAME:-PLAYWRIGHT_STORAGE_STATE_JSON}"
STATE_FILE="${1:-}"

if [[ -z "${STATE_FILE}" ]]; then
  echo "Uso: $0 /ruta/a/storage-state.json"
  exit 1
fi

if [[ ! -f "${STATE_FILE}" ]]; then
  echo "No existe el archivo: ${STATE_FILE}"
  exit 1
fi

if ! gcloud secrets describe "${SECRET_NAME}" --project "${PROJECT_ID}" >/dev/null 2>&1; then
  gcloud secrets create "${SECRET_NAME}" \
    --project "${PROJECT_ID}" \
    --replication-policy="automatic"
fi

gcloud secrets versions add "${SECRET_NAME}" \
  --project "${PROJECT_ID}" \
  --data-file="${STATE_FILE}"

gcloud run jobs update "${JOB_NAME}" \
  --project "${PROJECT_ID}" \
  --region "${REGION}" \
  --update-secrets="PLAYWRIGHT_STORAGE_STATE_JSON=${SECRET_NAME}:latest"  # pragma: allowlist secret

echo
echo "Secret actualizado: ${SECRET_NAME}"
echo "Job actualizado: ${JOB_NAME}"
echo "Siguiente paso sugerido:"
echo "gcloud run jobs execute ${JOB_NAME} --project ${PROJECT_ID} --region ${REGION}"
