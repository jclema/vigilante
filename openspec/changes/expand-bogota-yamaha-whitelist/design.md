## Source

The user-facing page is:

`https://www.incolmotos-yamaha.com.co/puntos-de-atencion/`

The page is backed by the public JSON endpoint already used by the repository:

`https://www.incolmotos-yamaha.com.co/wp-json/v2/distributors/`

The importer consumes the JSON endpoint with a browser-like user agent and
filters the official dataset locally.

## Filtering

For Bogotá, the accepted source rows are:

- `tienda` equals `SI`.
- `id_departamento` equals `11`.
- `municipio` matches `Bogotá D.C.` or `Bogotá. D.C.` after normalizing spaces
  and punctuation.

The canonical city stored in Vigilante is `Bogotá D.C.`.

## Phone Normalization

Bogotá fixed-line numbers with seven digits are normalized with area code `601`.
The previous Medellín default remains `604`.

This matters because Incolmotos rows may provide values such as `3904947`, which
must become `6013904947`, not `6043904947`.

## Runtime Behavior

The local demo seed includes the 29 official Bogotá dealers as authorized
dealers under `org-yamaha-network`, each with a `PUBLIC_SCAN` profile. Startup
does not fetch the external endpoint; external refresh remains an explicit sync
operation.

The dashboard uses the existing city/filter mechanics. Copy changes from
Valle de Aburrá-only language to Yamaha network language so Bogotá coverage is
visible without implying that the current visual map is a precise national GIS
view.

## Out of Scope

- Automatic Google enforcement.
- Google Business Profile customer media extraction.
- Firestore migration.
- A full Colombia map redesign.
