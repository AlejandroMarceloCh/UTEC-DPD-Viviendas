# CENACOM 2017 — Censo Nacional de Comisarías PNP

**Fuente oficial:** INEI · https://www.inei.gob.pe/media/DATOS_ABIERTOS/CENACOM/DATA/2017.zip
**Fecha de descarga:** 2026-05-24

## Contenido del ZIP

- Módulo 1226 — Capítulo 100 Infraestructura (el que usamos)
- Otros módulos: 1227 (Cap 200), 1228, 1229, 1230, 1231, 1232, 1233, 1234 — datos no usados.

## Procesamiento realizado

1. Lectura `Cap_100_Infraestructura 2017.csv` (separador `|`, encoding `latin-1`).
2. Parser de `NOMBREDI` para extraer `ubigeo (6 dígitos) + nombre distrito`.
3. Filtro por UBIGEO empezando con `1501` (Lima provincia) o `0701` (Callao provincia).
4. Agregación por distrito → `comisarias_por_distrito.csv` (NOMBREDI, n_comisarias).

## Limitaciones honestas

- **Coordenadas GPSLATITUD_INF / GPSLONGITUD_INF**: las columnas existen pero la mayoría
  de comisarías de Lima tienen valor faltante o 0. No se puede usar para distancia exacta.
- **Año 2017** — 9 años de desfase. Posibles nuevas comisarías post-2017 no están.
- **Feature usable**: `n_comisarias_por_distrito` como proxy de "presencia policial".
  Más comisarías ≠ más seguro, pero indica esfuerzo del Estado en esa zona.
