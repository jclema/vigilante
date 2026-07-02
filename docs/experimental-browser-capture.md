# Captura experimental de fotos públicas

Este flujo es temporal y separado de la integración oficial con GBP.

## Objetivo

Tomar screenshots diarios de perfiles oficiales en Google Maps para generar evidencia experimental mientras llega acceso real a Google Business Profile.

## Qué hace

- abre URLs públicas de perfiles oficiales
- intenta entrar a `Fotos`
- toma screenshot completo
- ingesta la captura al pipeline de Vigilante
- guarda copia en evidencia y corre OCR

## Qué no hace

- no establece relación oficial `review -> foto`
- no reemplaza `customer media` de GBP
- no debe considerarse fuente oficial final

## CSV base

Usa [`scripts/experimental_browser_capture_targets.csv`](../scripts/experimental_browser_capture_targets.csv).

Columnas mínimas:

- `profile_id`
- `profile_name`
- `public_profile_url`

## Dependencias

Instalar localmente:

```bash
python3 -m pip install playwright
playwright install chromium
```

## Ejecución

```bash
PYTHONPATH=. STORAGE_BACKEND=firestore GOOGLE_CLOUD_PROJECT=vigilante-pilot \
python3 scripts/capture_public_review_media.py scripts/experimental_browser_capture_targets.csv
```

## Sesión persistente opcional

Si Google bloquea la navegación pública con `google.com/sorry`, puedes exportar una `storage_state` real de Playwright y usarla en el job.

### 1. Exportar la sesión

```bash
python3 scripts/export_playwright_storage_state.py \
  --output /tmp/vigilante-browser-capture-storage-state.json
```

Esto abrirá un navegador visible para que un humano:

- inicie sesión en Google si hace falta
- valide Google Maps
- y luego exporte la `storage_state`

Si Google bloquea el login dentro del navegador automatizado, usa esta variante apoyada en tu perfil local de Chrome:

```bash
python3 scripts/export_playwright_storage_state_from_chrome.py \
  --output /tmp/vigilante-browser-capture-storage-state.json
```

Recomendación:

- primero inicia sesión normalmente en Google Maps desde Chrome
- luego ejecuta este script para reutilizar esa sesión

Si Google sigue detectando cualquier Chrome controlado por Playwright, usa esta variante por CDP conectandose a un Chrome real ya abierto:

1. Abre Google Chrome manualmente con depuracion remota:

```bash
/Applications/Google\ Chrome.app/Contents/MacOS/Google\ Chrome \
  --remote-debugging-port=9222 \
  --user-data-dir=/tmp/vigilante-cdp-chrome
```

2. Dentro de ese Chrome, inicia sesion en Google y abre Maps.
3. En otra terminal, exporta la sesion viva:

```bash
python3 scripts/export_playwright_storage_state_via_cdp.py \
  --cdp-url http://127.0.0.1:9222 \
  --output /tmp/vigilante-browser-capture-storage-state.json
```

### 2. Usarla localmente

```bash
PLAYWRIGHT_STORAGE_STATE_PATH=/tmp/vigilante-browser-capture-storage-state.json \
PYTHONPATH=. STORAGE_BACKEND=firestore GOOGLE_CLOUD_PROJECT=vigilante-pilot \
python3 scripts/capture_public_review_media.py scripts/experimental_browser_capture_targets.csv
```

### 3. Usarla en Cloud Run Job

La versión productiva del scraper también acepta:

- `PLAYWRIGHT_STORAGE_STATE_PATH`
- `PLAYWRIGHT_STORAGE_STATE_JSON`

La recomendación es guardar el JSON como secreto y pasarlo al job para que `vigilante-browser-capture` ejecute con una sesión persistente real.

Script helper:

```bash
bash scripts/configure_browser_capture_storage_state.sh \
  /tmp/vigilante-browser-capture-storage-state.json
```

Eso hace tres cosas:

- crea el secreto `PLAYWRIGHT_STORAGE_STATE_JSON` si no existe
- sube una nueva versión con la sesión exportada
- actualiza el job `vigilante-browser-capture` para consumir el secreto

## Resultado

Las capturas se procesan como evidencia con `ingestion_mode=experimental_browser_capture` para que queden diferenciadas de la ruta oficial GBP.

## Estado operativo actual

Al 24 de marzo de 2026 este flujo debe considerarse **experimental/manual**.

Hallazgo actual:

- Google sigue bloqueando o redirigiendo parte del trafico automatizado de Cloud Run hacia `google.com/sorry`
- por eso el job no debe asumirse como fuente productiva confiable para fotos

Recomendacion operativa actual:

- mantener este flujo solo para pruebas controladas
- no usarlo como cobertura automatica principal
- priorizar barrido publico de clonados, expedientes y rutas oficiales GBP cuando existan
