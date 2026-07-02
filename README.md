# Vigilante

Sistema piloto para detectar, investigar y gestionar posibles suplantaciones de
concesionarios Yamaha en Google Maps.

Vigilante combina monitoreo público, eventos de Google Business Profile,
análisis de evidencia, gestión de casos y asistencia para reportes. El objetivo
operativo es reducir el tiempo entre la aparición de un perfil o contenido
sospechoso y una decisión humana respaldada por evidencia.

> Estado: piloto funcional. Sirve para demos, validación de flujos y desarrollo
> local. Todavía no debe tratarse como un sistema autónomo de protección en
> producción.

## Qué funciona hoy

| Capacidad | Estado | Alcance actual |
|---|---|---|
| Dashboard ejecutivo y operativo | Funcional | Vistas de red, organizaciones, perfiles, casos, evidencia y actividad |
| Gestión de usuarios y organizaciones | Funcional | Roles, sesiones, selección de organización e invitaciones |
| Scout | Funcional | Consolida candidatos obtenidos de búsquedas públicas y crea casos |
| Forensic | Funcional | Evalúa nombre, teléfono, ubicación, texto extraído y señales de riesgo |
| Reporter | Funcional | Genera paquetes de evidencia, alertas y borradores de reporte |
| Google Places | Parcial | Usa la API real cuando existe `GOOGLE_MAPS_API_KEY`; sin ella usa datos demo |
| Google Business Profile | Parcial | Incluye OAuth, conexión por organización e ingesta de customer media; requiere acceso real a las cuentas GBP |
| Persistencia | Parcial | Memoria para demo y adaptador Firestore para Google Cloud |
| Evidencia y OCR | Parcial | Almacenamiento local o GCS y soporte opcional para Google Vision |
| Notificaciones | Parcial | Webhook y SMTP configurables |
| Browser enforcement | Experimental | Prepara o ejecuta flujos asistidos; no debe operar sin revisión humana |
| Captura pública con Playwright | Experimental | Google puede bloquear el tráfico o redirigirlo a `google.com/sorry` |
| Pruebas y CI | Funcional | 75 pruebas, Ruff, build del paquete, smoke test y builds Docker |

## Flujo actual

1. Cargar concesionarios autorizados y perfiles monitoreados.
2. Buscar candidatos públicos alrededor de las zonas objetivo.
3. Recibir eventos GBP cuando una organización ha autorizado el acceso.
4. Analizar identidad, teléfonos, ubicación, texto e imágenes.
5. Consolidar señales en casos con nivel de riesgo y evidencia.
6. Preparar alertas y paquetes de reporte.
7. Mantener una decisión humana antes de cualquier acción irreversible.

## Inicio rápido

Requisitos:

- Python 3.11 o superior.
- `make`.
- `curl` para el smoke test.
- Docker solo para validar o ejecutar contenedores.

```bash
git clone <repository-url>
cd vigilante
make setup
make run
```

Abrir `http://127.0.0.1:8000`.

Sin credenciales externas, la aplicación carga datos demo y usa almacenamiento
en memoria. Las cuentas demo están definidas en `app/services/demo_data.py` y
son exclusivamente para desarrollo.

## Comandos canónicos

```bash
make setup       # crea .venv e instala aplicación y herramientas
make run         # inicia FastAPI con recarga local
make test        # ejecuta pytest
make lint        # ejecuta Ruff
make format      # formatea y corrige hallazgos seguros
make build       # construye wheel y source distribution
make smoke       # inicia la aplicación y prueba /login
make check       # lint, pruebas, build y compilación
```

El mapa completo para Codex y otros agentes está en
[`AGENTS.md`](AGENTS.md).

## Arquitectura del repositorio

```text
app/
  agents/        Scout, Forensic y Reporter
  services/      autenticación, integraciones, evidencia y operaciones
  templates/     dashboard server-rendered
  static/        estilos y assets
  main.py        rutas FastAPI y wiring
  models.py      modelo de dominio
  store.py       repositorios en memoria y Firestore
docs/            guías operativas, matrices y planes
infra/           Terraform y políticas de infraestructura
scripts/         herramientas operativas reutilizables
tests/           pruebas unitarias y de API
```

## Configuración

Copiar la plantilla y reemplazar solo los valores necesarios para el modo que
se va a ejecutar:

```bash
cp .env.example .env
```

Variables mínimas para demo:

```dotenv
APP_ENV=development
STORAGE_BACKEND=memory
SEED_DEMO_DATA=true
SESSION_SECRET=<valor-local-aleatorio>
```

Integraciones externas relevantes:

- `GOOGLE_MAPS_API_KEY`
- `GOOGLE_OAUTH_CLIENT_ID`
- `GOOGLE_OAUTH_CLIENT_SECRET`
- `GOOGLE_OAUTH_REDIRECT_URI`
- `GOOGLE_GBP_WEBHOOK_SECRET`
- `GOOGLE_CLOUD_PROJECT`
- `EVIDENCE_BUCKET_NAME`
- `ALERT_WEBHOOK_URL`
- configuración SMTP

No guardar credenciales, service accounts ni estados de navegador en Git.

## Lo que falta para que sea verdaderamente útil

### P0. Probar valor operativo con datos reales

El siguiente hito no es agregar más agentes. Es cerrar un flujo real de punta a
punta con una organización y un conjunto pequeño de sedes.

- Conseguir acceso GBP de una organización piloto.
- Completar la matriz de perfiles, cuentas y responsables.
- Conectar Places, GBP, Firestore, GCS y notificaciones en un entorno de prueba.
- Ejecutar un scan real y confirmar que un analista puede distinguir un falso
  positivo de una amenaza.
- Generar un expediente que pueda revisarse y reportarse sin reconstruir
  evidencia manualmente.

Criterio de salida: al menos un caso real o controlado pasa desde detección
hasta decisión humana con evidencia, trazabilidad y tiempos medidos.

### P0. Definir el contrato de detección

Hoy existen reglas y scoring, pero falta convertirlos en un contrato operativo:

- Qué constituye perfil oficial, sospechoso, watchlist y suplantación confirmada.
- Qué señales son obligatorias antes de escalar.
- Umbrales de riesgo y responsables de aprobar cambios.
- Tratamiento de falsos positivos y mecanismo de apelación.
- Dataset etiquetado para medir precisión y recall.

Criterio de salida: los mismos inputs producen decisiones explicables y
reproducibles, con métricas conocidas.

### P0. Seguridad y operación mínima

- Rechazar secretos por defecto fuera de desarrollo.
- Completar `.env.example` con todas las variables soportadas.
- Validar autenticación de webhooks y llamadas de Cloud Scheduler.
- Definir retención, acceso y cadena de custodia para evidencia.
- Añadir rate limiting, headers de seguridad y auditoría de acciones sensibles.
- Documentar backup, restauración, rollback y respuesta a incidentes.

Criterio de salida: el piloto puede almacenar evidencia real sin depender de
credenciales demo ni controles implícitos.

### P1. Observabilidad y recuperación

- Logs estructurados con organization ID, case ID, scan ID y correlation ID.
- Métricas de cobertura, latencia, errores, casos creados y falsos positivos.
- Estado visible de Places, GBP, OCR, storage y notificaciones.
- Reintentos idempotentes y dead-letter handling para eventos fallidos.
- Runbooks con comandos exactos para diagnosticar y recuperar cada integración.

Criterio de salida: un operador puede detectar y explicar una falla sin leer el
código ni repetir el flujo a ciegas.

### P1. Validación de producto

Medir durante el piloto:

- Tiempo medio desde detección hasta triage.
- Tiempo desde triage hasta reporte.
- Precisión de casos escalados.
- Cobertura de sedes y perfiles oficiales.
- Incidentes evitados o tiempo operativo ahorrado.
- Costo por sede monitoreada.

Sin estas métricas, Vigilante puede ser técnicamente interesante pero no
demostrar valor comercial.

### P2. Automatización segura

Solo después de validar precisión y operación:

- Automatizar acciones reversibles de bajo riesgo.
- Mantener aprobación humana para reportes o cambios externos.
- Registrar evidencia antes y después de cada acción.
- Incorporar browser automation como fallback, no como fuente principal.
- Añadir cleanup periódico de deuda, documentación y reglas obsoletas.

## Riesgos conocidos

- Google Maps puede bloquear automatización de navegador.
- El acceso GBP depende de permisos y estructura de cuentas de cada concesionario.
- Los datos demo no representan la distribución real de fraude.
- La memoria local no es persistencia productiva.
- Un score alto no equivale por sí solo a fraude confirmado.
- Automatizar reportes incorrectos puede afectar perfiles legítimos.

## Documentación

- [`docs/google-cloud-pilot.md`](docs/google-cloud-pilot.md): despliegue piloto.
- [`docs/gbp-access-matrix-guide.md`](docs/gbp-access-matrix-guide.md): levantamiento de acceso GBP.
- [`docs/experimental-browser-capture.md`](docs/experimental-browser-capture.md): límites de captura pública.
- [`docs/plans/active/codex-harness-v1.md`](docs/plans/active/codex-harness-v1.md): arnés del repositorio para Codex.
- [`Agente IA Anti-Phishing Google Maps.md`](Agente%20IA%20Anti-Phishing%20Google%20Maps.md): investigación y propuesta original.

## Regla de contribución

Antes de entregar un cambio:

```bash
make check
make smoke
```

Los cambios que afecten scoring, autorizaciones, persistencia, retención o
acciones externas deben incluir criterios de aceptación, pruebas y plan de
rollback.
