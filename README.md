# Vigilante

[English](README.en.md) | [Español](README.md)

Vigilante es un piloto para detectar suplantacion de concesionarios Yamaha en Google Maps, consolidar evidencia y ayudar a un humano a decidir si un caso debe escalarse, archivarse o reportarse.

No es un sistema autonomo de enforcement. Hoy es un producto de operaciones asistidas con foco en:

- deteccion publica de puntos clonados o sospechosos
- analisis de evidencia y construccion de expedientes
- gestion operativa por red, concesionario y sede
- preparacion de reportes con aprobacion humana

## Produccion

La aplicacion publica esta disponible en:

- [https://www.watchmanhub.com](https://www.watchmanhub.com)

La ruta publica de produccion es:

```text
Cloudflare
  -> Google Cloud Global External Application Load Balancer
  -> Cloud Armor
  -> Serverless NEG
  -> Cloud Run
  -> Firestore y Cloud Storage
```

Controles activos:

- TLS administrado para `watchmanhub.com` y `www.watchmanhub.com`
- redireccion HTTP a HTTPS y dominio canonico en `www`
- Cloud Run limitado a trafico interno y del Load Balancer
- URL publica `run.app` bloqueada para acceso directo desde internet
- Cloud Armor conectado con reglas administradas en preview
- runtime y Cloud Scheduler con service accounts separadas
- Scheduler autenticado con OIDC
- secretos administrados con Secret Manager
- cookies seguras y headers HTTP defensivos
- datos demo desactivados en produccion

## Estado real del proyecto

El producto ya paso de ser un prototipo generico a un piloto operativo con UI, casos, expediente, mapa territorial, jerarquia de red y rutas de integracion. Lo importante es esto:

- el monitoreo publico de puntos clonados si funciona
- la gestion de casos, expediente y operacion manual si funciona
- la estructura organizacional nueva ya quedo modelada
- la integracion formal con Google Business Profile quedo implementada en software
- el acceso real a `customer media` de GBP no quedo habilitado por Google
- la captura automatizada por navegador contra Google Maps no es confiable en Cloud Run

En corto: Vigilante ya sirve para operar el piloto y validar flujos humanos reales, pero todavia no tiene una fuente estable y oficial para fotos GBP.

## Resumen ejecutivo

### Lo que si logramos

1. Construimos un dashboard operativo usable.
2. Rehicimos la UX de login, dashboard, case detail y settings.
3. Simplificamos cards, copies y jerarquia visual para que el sistema se sienta mas liviano.
4. Modelamos la jerarquia correcta de red:
   - Vigilante plataforma
   - Vista global de redes
   - Yamaha Red Oficial
   - Concesionarios
   - Sedes
5. Ajustamos whitelist, organizaciones y sedes reales para la red Yamaha.
6. Corregimos la logica para que los casos y alertas se agreguen a la organizacion correcta.
7. Reparamos el endpoint de escaneo publico para aceptar trafico confiable de Cloud Scheduler.
8. Dejamos operativa la ruta formal de `customer media` por GBP, con UI y mensajes de bloqueo claros.
9. Reinsertamos evidencia visual en expediente para casos de foto manipulada.
10. Dejamos documentado que browser capture es experimental y no debe tratarse como evidencia oficial.

### Lo que no funciono

1. Google bloqueo o degrado repetidamente la captura automatizada por navegador.
2. El proyecto no obtuvo aprobacion de Google para acceso real a GBP API con cuota operativa.
3. Sin esa aprobacion, `Requests per minute` para Business Information API quedo en `0`.
4. Sin cuota aprobada, no podemos leer `customer media` oficial aunque la integracion tecnica este lista.

### Por que no funciono

No fue un problema principal de codigo. El bloqueo fue externo en dos capas:

1. Google Maps detecta y limita trafico automatizado, incluso endureciendo la navegacion con redirecciones a `google.com/sorry`.
2. Google rechazo la solicitud de acceso GBP porque la cuenta o proyecto no pasaron sus chequeos internos de calidad.

## Contexto del producto

El problema que resuelve Vigilante es operativo, no solo tecnico.

Los concesionarios oficiales pueden ser afectados por:

- perfiles clonados
- sedes falsas
- fotos manipuladas
- phishing dentro de Google Maps

El trabajo manual para detectar, comparar, documentar y hacer seguimiento consume tiempo, se dispersa entre personas y deja poca trazabilidad. Vigilante nace para concentrar:

- monitoreo
- evidencia
- scoring
- decision humana
- seguimiento

## Proceso de desarrollo del producto

Este ha sido el recorrido real del piloto.

### Fase 1. Base del sistema

Se construyo la app FastAPI con:

- autenticacion
- organizaciones y roles
- dashboard server-rendered
- casos, evidencia y timeline
- servicios Scout, Forensic y Reporter

### Fase 2. Operacion y UX

Se hizo una pasada profunda de UI y UX para volver la app mas directa:

- login mas claro y moderno
- dashboard con mapas y tarjetas mas operacionales
- expedientes mas legibles
- settings por vista activa mas ordenado
- mensajes menos narrativos y mas accionables

### Fase 3. Jerarquia real de la red

Se rehizo la arquitectura operativa alrededor de:

- una sola Yamaha Red Oficial
- varios concesionarios dentro de esa red
- una o mas sedes por concesionario

Esto obligo a:

- migrar asociaciones de casos y alertas
- rehacer dropdowns y vistas activas
- actualizar whitelist y concesionarios reales
- corregir agregaciones para perfiles protegidos, alertas y comando

### Fase 4. Deteccion publica

Se estabilizo el scan publico para posibles clonaciones y perfiles sospechosos.

Tambien se corrigio el endpoint `/api/scans/run` para que acepte ejecuciones confiables desde Cloud Scheduler, con sus headers reales.

Esto dejo funcional la parte mas importante del piloto hoy: barrido publico y creacion de casos.

### Fase 5. Fotos y evidencia

Intentamos dos caminos en paralelo:

#### Camino A. Captura publica con navegador

Se construyo un flujo experimental con Playwright para:

- abrir perfiles oficiales
- navegar a fotos
- tomar captura
- ingestar evidencia

Se mejoro con:

- `storage_state`
- variantes con Chrome local y CDP
- filtros por perfil
- validacion de aterrizaje correcto

Resultado:

- sigue siendo experimental
- en Cloud Run Google lo bloquea o lo manda a landing equivocada
- no se puede tomar como fuente estable

#### Camino B. Integracion formal GBP

Se implemento la ruta formal para leer `customer media` oficial:

- OAuth por organizacion
- conexion de cuentas GBP
- binding de locations
- backfill manual desde settings
- mensajes claros de estado y bloqueo

Resultado:

- la integracion tecnica quedo lista
- la plataforma muestra el bloqueo correctamente
- Google no habilito el acceso real

## Lo que funciona hoy

| Capacidad | Estado | Comentario |
|---|---|---|
| Login, roles y sesiones | Funcional | Google OAuth en produccion; demo solo local |
| Dashboard operativo | Funcional | Vistas de plataforma, red y concesionario |
| Territory map | Funcional | Enfoque operativo en alertas |
| Gestion de casos | Funcional | Triage, expediente, timeline y operacion |
| Deteccion publica de clonados | Funcional | Ruta mas confiable del producto hoy |
| Expediente de foto manipulada | Funcional | Con evidencia visual recuperada |
| Jerarquia red -> concesionario -> sede | Funcional | Ajustada a estructura real Yamaha |
| Browser enforcement guiado | Funcional con limites | Humano-in-the-loop |
| Ingesta formal GBP en codigo | Funcional en software | Bloqueada externamente por Google |
| Captura publica de fotos con Playwright | Experimental | No confiable en Cloud Run |

La autenticacion publica usa `https://www.watchmanhub.com/auth/google/callback`.
Las cuentas demo solo pertenecen al entorno local y sus credenciales conocidas
son rechazadas en produccion.

## Lo que no funciona hoy

| Tema | Estado | Razon |
|---|---|---|
| Customer media oficial GBP | Bloqueado | Google rechazo acceso del proyecto |
| Cuota operativa Business Information API | Bloqueada | `Requests per minute = 0` |
| Scraper de fotos por navegador en cloud | Inestable | Antibot y redireccion a `google.com/sorry` |
| Cobertura automatica de fotos oficiales | No disponible | Depende de alguno de los dos puntos anteriores |

## Punto exacto donde estamos

Hoy Vigilante esta en un punto intermedio sano:

- el producto ya tiene forma operativa real
- el flujo de casos ya es usable
- la red y los concesionarios ya quedaron modelados
- el monitoreo publico ya genera valor
- el gran bloqueo pendiente es la fuente oficial o confiable de fotos GBP

No estamos bloqueados para seguir mejorando producto. Si estamos bloqueados para validar el modulo de fotos oficiales como capacidad productiva real.

## Que debe resolverse

### P0. Resolver la fuente de fotos oficiales

Hay dos caminos:

1. Reaplicar correctamente a GBP API y lograr aprobacion real de Google.
2. Definir un fallback humano o semiautomatico para fotos mientras llega esa aprobacion.

Mi lectura hoy es clara: este es el cuello de botella principal del proyecto.

### P0. Confirmar criterio operativo de denuncia

Ya avanzamos hacia un modelo donde el sistema prepara y el humano decide. Falta cerrar de forma estable:

- umbral real de alta certeza
- que evidencia minima exige una denuncia
- como documentar evidencia y seguimiento posterior
- cuando un caso se archiva como falso positivo

### P0. Medir precision con casos reales

Hace falta dataset y rutina operativa para medir:

- precision de alertas
- falsos positivos
- tiempo de triage
- tiempo a decision
- valor real por concesionario

### P1. Operacion productiva

Firestore, Cloud Storage, Secret Manager, Load Balancer e identidades separadas
ya estan operativos. Falta completar:

- retencion de evidencia
- alertas y dashboards de observabilidad
- auditoria
- runbooks
- recuperacion ante fallos externos
- calibracion y enforcement final de Cloud Armor

## Plan actual recomendado

### Frente 1. Producto

Seguir mejorando lo que ya genera valor sin depender de Google:

1. dashboard operativo
2. case detail
3. comando por concesionario
4. filtros, historicos y trazabilidad
5. evidencia y seguimiento manual

### Frente 2. GBP oficial

No seguir invirtiendo horas en hacks tecnicos hasta resolver aprobacion.

Lo correcto ahora es:

1. corregir lo necesario en website, negocio y perfil para cumplir criterios de Google
2. volver a aplicar
3. esperar aprobacion de cuota real
4. reconectar y volver a probar `customer media`

### Frente 3. Fallback operativo

Si el negocio necesita validar fotos antes de esa aprobacion, conviene definir un flujo manual controlado o semiasistido, no seguir apostandole por ahora a un scraper cloud frágil.

## Credenciales demo

Las cuentas demo base viven en `app/services/demo_data.py`.
Solo se cargan localmente cuando `SEED_DEMO_DATA=true`. Produccion exige
`SEED_DEMO_DATA=false` y rechaza configuraciones inseguras durante el arranque.

- `operator@vigilante.local` / `change-me`
- `yamaha@vigilante.local` / `yamaha-demo`
- `bello@motoblu.local` / `dealer-demo`
- `asesor.bello@motoblu.local` / `dealer-demo`

## Inicio rapido

Requisitos:

- Python 3.11 o superior
- `make`
- `curl` para smoke test
- Docker solo si vas a validar contenedores

```bash
git clone <repository-url>
cd vigilante
make setup
make run
```

Abrir [http://127.0.0.1:8000](http://127.0.0.1:8000).

## Comandos canónicos

```bash
make setup       # crea .venv e instala app y herramientas
make run         # inicia FastAPI local
make test        # ejecuta pruebas
make lint        # ejecuta Ruff
make format      # formatea Python
make build       # construye wheel y sdist
make smoke       # prueba que /login responda
make check       # lint, pruebas, build y compile checks
```

## Arquitectura del repositorio

```text
app/
  agents/        Scout, Forensic y Reporter
  services/      autenticacion, integraciones, evidencia y operaciones
  templates/     dashboard server-rendered
  static/        estilos y assets
  main.py        rutas FastAPI y wiring
  models.py      modelo de dominio
  store.py       repositorios en memoria y Firestore
docs/            guias operativas, matrices y planes
infra/           Terraform e infraestructura
scripts/         herramientas operativas reutilizables
tests/           pruebas unitarias y de API
```

## Configuracion

```bash
cp .env.example .env
```

Variables minimas para demo:

```dotenv
APP_ENV=development
STORAGE_BACKEND=memory
SEED_DEMO_DATA=true
SESSION_SECRET=<valor-local-aleatorio>
```

Integraciones externas importantes:

- `GOOGLE_MAPS_API_KEY`
- `GOOGLE_OAUTH_CLIENT_ID`
- `GOOGLE_OAUTH_CLIENT_SECRET`
- `GOOGLE_OAUTH_REDIRECT_URI`
- `GOOGLE_GBP_WEBHOOK_SECRET`
- `GOOGLE_CLOUD_PROJECT`
- `EVIDENCE_BUCKET_NAME`
- `ALERT_WEBHOOK_URL`
- SMTP si aplica

Nunca guardar credenciales, service accounts, evidencia real ni `storage_state` de navegador en Git.

## Documentacion clave

- [`AGENTS.md`](AGENTS.md): mapa rapido del repo para agentes.
- [`openspec/specs`](openspec/specs): specs vivos del producto y comportamiento esperado.
- [`openspec/changes`](openspec/changes): cambios Spec-Driven Development activos y archivados.
- [`ai-specs/docs/base-standards.md`](ai-specs/docs/base-standards.md): reglas portables para agentes.
- [`ai-specs/docs/product-context.md`](ai-specs/docs/product-context.md): contexto de producto, usuarios y oportunidad.
- [`docs/onboarding/developer-onboarding.md`](docs/onboarding/developer-onboarding.md): onboarding en ingles para developers externos.
- [`docs/google-cloud-pilot.md`](docs/google-cloud-pilot.md): checklist de despliegue del piloto.
- [`docs/watchmanhub-production-runbook.md`](docs/watchmanhub-production-runbook.md): operacion, diagnostico y rollback de produccion.
- [`docs/gbp-access-matrix-guide.md`](docs/gbp-access-matrix-guide.md): levantamiento de acceso GBP.
- [`docs/experimental-browser-capture.md`](docs/experimental-browser-capture.md): limites y uso del scraper experimental.
- [`Agente IA Anti-Phishing Google Maps.md`](Agente%20IA%20Anti-Phishing%20Google%20Maps.md): investigacion y propuesta original.

## Spec-Driven Development

Vigilante usa OpenSpec como capa viva de especificaciones. Para cambios no
triviales de producto, comportamiento, integraciones, seguridad, operaciones o
arquitectura:

```bash
/opsx:explore
/opsx:propose <change-name>
/opsx:apply <change-name>
npx --yes @fission-ai/openspec@latest validate --all --no-interactive
/opsx:archive <change-name>
```

La regla practica: si el cambio afecta casos, evidencia, scoring, permisos,
reportes, GBP, Places, operaciones productivas o experiencia principal, primero
debe quedar expresado como spec con criterios de aceptacion y escenarios.

## Regla de entrega

Antes de cerrar cambios:

```bash
make check
make smoke
```

Si un cambio toca scoring, autorizaciones, persistencia, retencion o acciones externas, debe venir con:

- pruebas
- criterio de aceptacion
- rollback claro
