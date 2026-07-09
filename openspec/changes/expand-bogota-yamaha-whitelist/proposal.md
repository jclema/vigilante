## Why

Vigilante needs broader official Yamaha coverage beyond Medellín to monitor
high-risk fraud patterns in Bogotá, where fake Google Maps listings and
AI-manipulated storefront photos can redirect customers to false phone numbers.

The official source is Incolmotos Yamaha's public points-of-attention data used
by `https://www.incolmotos-yamaha.com.co/puntos-de-atencion/`. For this slice,
the whitelist must include official rows matching:

- `tienda = SI`
- `id_departamento = 11`
- city aliases `Bogotá D.C.` and `Bogotá. D.C.`

## What Changes

- Extend the official Yamaha whitelist importer to support city aliases and
  department-specific fixed phone normalization.
- Add 29 official Bogotá Tienda Yamaha points to the local/demo whitelist.
- Create public-scan dealer profiles for those Bogotá points.
- Update dashboard territory copy and filters so Bogotá appears as monitored
  network coverage, not as an out-of-band dataset.
- Keep enforcement and Google reporting behavior unchanged.

## Capabilities

### New Capabilities

- None.

### Modified Capabilities

- `public-scanning`: Expands official whitelist import behavior for Bogotá and
  public-scan coverage.
- `case-management`: Ensures dashboard filters and territory summaries include
  the expanded Bogotá network.

## Impact

- Adds Bogotá official dealer coverage to demo/local seed data.
- Improves import correctness for Colombian city aliases and fixed phone area
  codes.
- No schema, infrastructure, IAM, secret, or production dependency changes.
