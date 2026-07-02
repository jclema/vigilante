# Vigilante

Vigilante es un piloto híbrido para detectar suplantación de concesionarios Yamaha en Google Maps.

## Qué incluye este repositorio

- Backend `FastAPI` con agentes internos:
  - `Scout`
  - `Forensic`
  - `Reporter`
- Dashboard ejecutivo y operativo server-rendered
- Endpoints JSON para casos, métricas y ejecución de scans
- Seed data local para demo sin credenciales reales
- Esqueleto de despliegue en Google Cloud y CI/CD en GitHub Actions

## Flujo del piloto

1. Cargar concesionarios autorizados y perfiles monitoreados.
2. Escanear Google Maps públicamente para detectar clones.
3. Recibir eventos de Google Business Profile para perfiles con acceso.
4. Analizar fotos, nombres, teléfonos y ubicación.
5. Crear casos, agregar evidencia y preparar reportes a Google.
6. Exponer todo en un dashboard útil para operación y gerencia.

## Estructura

```text
app/
  agents/
  services/
  static/
  templates/
infra/terraform/
tests/
```

## Ejecución local

```bash
make setup
make run
```

La aplicación cargará datos demo para mostrar los dashboards aunque no existan credenciales reales de Google Cloud.

## Verificación

```bash
make check
make smoke
```

`make check` ejecuta lint, pruebas, build del paquete y compilación de módulos.
Los comandos canónicos y límites para agentes están documentados en `AGENTS.md`.

## Variables de entorno

Ver `.env.example`.

## Estado actual

Esta versión deja lista la base funcional del piloto:

- storage local en memoria con seeds demo,
- puertos de integración para Places API y GBP,
- métricas ejecutivas, operativas y de amenazas,
- pruebas unitarias del scoring y agregación del dashboard.

Los conectores reales de Google Cloud pueden activarse reemplazando los stubs de servicios por clientes reales.
