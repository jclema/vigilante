# Matriz de acceso GBP

Archivo base: [`gbp-access-matrix.csv`](gbp-access-matrix.csv).

## Cómo usarla

Llena una fila por sede oficial. El objetivo es responder cuatro preguntas:

1. Qué perfil oficial estamos monitoreando.
2. Quién administra ese perfil hoy.
3. Bajo qué cuenta de Google Business Profile vive.
4. Si ya tenemos acceso suficiente para activar customer media.

## Columnas clave

- `dealer_name`: nombre comercial de la sede oficial.
- `official_profile_url`: URL pública del perfil oficial en Google Maps / GBP.
- `gbp_location_id`: id de location cuando ya exista.
- `admin_company`: socio, concesionario o equipo que administra el perfil.
- `admin_contact_email`: correo de la persona que puede conceder acceso.
- `gbp_account_name`: nombre de la cuenta GBP que agrupa la ubicación.
- `gbp_account_id`: account id real que necesitaremos para la integración.
- `role_on_profile`: owner, primary owner, manager, site manager, etc.
- `access_status`: sugerido: `Pendiente`, `Contactado`, `Con acceso`, `Bloqueado`.
- `oauth_ready`: `Si/No`, según si ya podemos obtener token con permisos.
- `notification_ready`: `Si/No`, según si esa cuenta ya podría activar `NEW_CUSTOMER_MEDIA`.

## Regla práctica

No necesitamos una credencial por sede si varias sedes viven bajo la misma `gbp_account_id`.

Al final del levantamiento debemos poder agrupar por:

- `gbp_account_id`
- `admin_company`
- `access_status`

Eso nos dirá cuántas integraciones reales hay que activar.

## Resultado esperado

Cuando esta matriz esté llena, podremos definir:

- cuántas cuentas GBP distintas existen en la red
- qué sedes ya están listas para customer media
- qué socios faltan por autorizar
- qué orden seguir para activar la integración oficial
