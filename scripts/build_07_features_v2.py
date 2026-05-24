"""Genera notebooks/07_features_geo_v2.ipynb.

El notebook inyecta features socioeconómicas y de seguridad real al dataset:
  - estrato_nse + categoria_distrito (tabla manual sustituye shapefile INEI)
  - POIs OSM (7 categorías nuevas: 11,200+ elementos)
  - n_comisarias_por_distrito (CENACOM 2017)
  - denuncias_violentas + patrimoniales + otras por distrito (MININTER 2018-2026)
  - dist_estacion_metro
  - count_500m y dist_nearest_m a los POIs (en paralelo a las existentes en 1km)
Output: data/processed/inmuebles_clean_v2.csv con ~25 columnas nuevas.
"""
from pathlib import Path
import nbformat as nbf

NB_PATH = Path(__file__).resolve().parents[1] / "notebooks" / "07_features_geo_v2.ipynb"

nb = nbf.v4.new_notebook()
nb.metadata = {
    "kernelspec": {"name": "dpd-v2", "display_name": "Python (DPD v2)"},
    "language_info": {"name": "python"},
}

cells = []

cells.append(nbf.v4.new_markdown_cell("""# Feature engineering v2 — proyecto DPD

> **Día 3 del plan_v2.md.**
> Combina datos del proyecto original con las fuentes externas adquiridas en el día 2 + tabla manual de NSE construida desde APEIM/INEI.

## Features que se agregan

| Categoría | Nuevas columnas | Origen |
|---|---|---|
| Socioeconómico | `estrato_nse` (1-5), `categoria_distrito` (3 OHE) | Tabla manual `distritos_lima_features.py` |
| POIs OSM premium | `count_1km_osm_supermercados`, `osm_malls`, `osm_universidades`, `osm_parques`, `osm_farmacias`, `osm_bancos`, `osm_estaciones` (count_1km + dist_nearest_m) | OSM Overpass · 11,200+ elementos |
| POI distancia corta | `count_500m_osm_*` (7 cols) | OSM filtrado a 500m |
| Seguridad estatal | `n_comisarias_distrito` | CENACOM 2017 · 149 comisarías |
| Denuncias por tipo | `denuncias_violentas_distrito`, `denuncias_patrimoniales_distrito`, `denuncias_otras_distrito` (por año 2024) | MININTER 2018-2026 |

**Total features nuevas:** ~25 (sumadas a las 74 originales).

## Outputs

- `data/processed/inmuebles_clean_v2.csv` — dataset enriquecido (3,348 filas × ~100 cols)
- `data/processed/geo_index_v2.csv` — versión consumida por el backend de la app
"""))

cells.append(nbf.v4.new_code_cell("""import numpy as np
import pandas as pd
import json
import sys
from pathlib import Path
from scipy.spatial import cKDTree

# Hacer accesible scripts/distritos_lima_features.py
sys.path.insert(0, '../scripts')
from distritos_lima_features import attach_features, _norm

PROCESSED = '../data/processed/'
EXTERNAL  = '../data/external/'

df = pd.read_csv(f'{PROCESSED}inmuebles_clean_v1.csv')
print(f'Listings: {len(df)}, cols originales: {len(df.columns)}')
"""))

cells.append(nbf.v4.new_markdown_cell("""## 1. Estrato NSE + categoría distrito (tabla manual)"""))

cells.append(nbf.v4.new_code_cell("""df = attach_features(df, col_distrito='distrito_oficial')
print(f'Después attach_features: {len(df.columns)} cols')
print()
print('Distribución de estrato_nse en el dataset:')
print(df['estrato_nse'].value_counts().sort_index().to_string())
print()
print('Categoría distrito:')
print(df['categoria_distrito'].value_counts().to_string())

# OHE de categoria
ohe = pd.get_dummies(df['categoria_distrito'], prefix='cat_dist', dtype=int)
df = pd.concat([df, ohe], axis=1)
print(f'\\nDespués OHE categoría: {len(df.columns)} cols')
"""))

cells.append(nbf.v4.new_markdown_cell("""## 2. POIs OSM — 7 categorías nuevas

Cargamos los JSON de Overpass y construimos un KD-tree por categoría para calcular `count_500m`, `count_1km` y `dist_nearest_m` de cada listing.
"""))

cells.append(nbf.v4.new_code_cell("""EARTH_M = 6_371_000.0

def to_unit_sphere(lat, lng):
    lat_r, lng_r = np.radians(lat), np.radians(lng)
    return np.column_stack([
        np.cos(lat_r) * np.cos(lng_r),
        np.cos(lat_r) * np.sin(lng_r),
        np.sin(lat_r),
    ])

def haversine_m(lat1, lng1, lat2, lng2):
    lat1, lng1 = np.radians(lat1), np.radians(lng1)
    lat2, lng2 = np.radians(lat2), np.radians(lng2)
    dlat, dlng = lat2 - lat1, lng2 - lng1
    a = np.sin(dlat/2)**2 + np.cos(lat1)*np.cos(lat2)*np.sin(dlng/2)**2
    return 2 * EARTH_M * np.arcsin(np.sqrt(a))

OSM_CATEGORIES = ['supermercados', 'malls', 'universidades', 'parques',
                  'farmacias', 'bancos', 'estaciones']

# Cargar y normalizar coords de cada categoría
osm_pois = {}
for cat in OSM_CATEGORIES:
    data = json.load(open(f'{EXTERNAL}osm_overpass/{cat}.json'))
    pts = []
    for el in data['elements']:
        if 'lat' in el and 'lon' in el:
            pts.append((el['lat'], el['lon']))
        elif 'center' in el:
            pts.append((el['center']['lat'], el['center']['lon']))
    osm_pois[cat] = np.array(pts) if pts else np.empty((0, 2))
    print(f'{cat:15} {len(pts):>5} POIs')
"""))

cells.append(nbf.v4.new_code_cell("""# Para cada categoría, construir KDTree en esfera unitaria y calcular features
listings_xyz = to_unit_sphere(df['latitud'].values, df['longitud'].values)

for cat, coords in osm_pois.items():
    if len(coords) == 0:
        df[f'count_500m_osm_{cat}']  = 0
        df[f'count_1km_osm_{cat}']   = 0
        df[f'dist_nearest_m_osm_{cat}'] = 9999.0
        continue
    poi_xyz = to_unit_sphere(coords[:, 0], coords[:, 1])
    tree = cKDTree(poi_xyz)
    # K=50 vecinos (suficiente para contar en 1km, ~6.4 km máx con 50 POIs en zonas densas)
    k = min(50, len(coords))
    _, idx = tree.query(listings_xyz, k=k)
    if k == 1:
        idx = idx[:, np.newaxis]
    # Distancias haversine reales a esos k vecinos
    counts_500m, counts_1km, dist_near = [], [], []
    for i, listing in enumerate(df[['latitud', 'longitud']].itertuples(index=False)):
        d_m = haversine_m(listing.latitud, listing.longitud,
                          coords[idx[i], 0], coords[idx[i], 1])
        counts_500m.append(int((d_m <= 500).sum()))
        counts_1km.append(int((d_m <= 1000).sum()))
        dist_near.append(float(d_m.min()))
    df[f'count_500m_osm_{cat}']    = counts_500m
    df[f'count_1km_osm_{cat}']     = counts_1km
    df[f'dist_nearest_m_osm_{cat}'] = dist_near
    print(f'{cat:15} count_1km median={np.median(counts_1km):.0f}  dist_near median={np.median(dist_near):.0f}m')

print(f'\\nDespués POIs OSM: {len(df.columns)} cols')
"""))

cells.append(nbf.v4.new_markdown_cell("""## 3. Seguridad estatal — comisarías por distrito"""))

cells.append(nbf.v4.new_code_cell("""com = pd.read_csv(f'{EXTERNAL}inei_comisarias/comisarias_por_distrito.csv')
com['nombre_norm'] = com['distrito_nombre'].apply(_norm)
print(f'CENACOM: {len(com)} distritos con comisarías')

df['_join'] = df['distrito_oficial'].apply(_norm)
df = df.merge(com[['nombre_norm', 'n_comisarias']],
              left_on='_join', right_on='nombre_norm', how='left')
df['n_comisarias_distrito'] = df['n_comisarias'].fillna(0).astype(int)
df = df.drop(columns=['_join', 'nombre_norm', 'n_comisarias'])
print(f'Distritos del dataset sin comisarías matched: {(df[\"n_comisarias_distrito\"] == 0).sum()} listings')
print(f'Top 5 distritos por #comisarías en el dataset:')
print(df.groupby('distrito_oficial')['n_comisarias_distrito'].first().sort_values(ascending=False).head(5).to_string())
"""))

cells.append(nbf.v4.new_markdown_cell("""## 4. Denuncias por tipo (MININTER 2018-2026)

Tomamos las denuncias del año 2024 (más reciente con cobertura completa) y las agrupamos en 3 buckets:
- **violentas**: Robo, Extorsión, Secuestro, Violencia contra la mujer
- **patrimoniales**: Hurto, Estafa
- **otras**: la categoría "Otros"
"""))

cells.append(nbf.v4.new_code_cell("""den = pd.read_csv(f'{EXTERNAL}mininter_denuncias/denuncias_lima_clean.csv')
print(f'Denuncias raw: {len(den)} filas, años={sorted(den[\"ANIO\"].unique())}')

den_2024 = den[den['ANIO'] == 2024].copy() if 2024 in den['ANIO'].values else den[den['ANIO'] == den['ANIO'].max()].copy()
print(f'Año usado: {den_2024[\"ANIO\"].iloc[0]} ({len(den_2024)} filas)')

# Clasificar modalidad en buckets
def clasificar(mod):
    mod = str(mod).strip()
    # En el CSV hay encoding raro: 'ExtorsiÃ³n' = 'Extorsión'
    if any(x in mod for x in ['Robo', 'Extorsi', 'Secuestro', 'Violencia']):
        return 'violentas'
    if any(x in mod for x in ['Hurto', 'Estafa']):
        return 'patrimoniales'
    return 'otras'

den_2024['bucket'] = den_2024['P_MODALIDADES'].apply(clasificar)
den_2024['nombre_norm'] = den_2024['DIST_HECHO'].apply(_norm)

agg = den_2024.groupby(['nombre_norm', 'bucket'], as_index=False)['cantidad'].sum()
piv = agg.pivot_table(index='nombre_norm', columns='bucket', values='cantidad', fill_value=0).reset_index()
piv.columns = ['nombre_norm'] + [f'denuncias_{c}_distrito' for c in piv.columns[1:]]
print(f'\\nPivot por distrito: {len(piv)} distritos')
print(piv.head(5).to_string(index=False))

# Join al dataset
df['_join'] = df['distrito_oficial'].apply(_norm)
df = df.merge(piv, left_on='_join', right_on='nombre_norm', how='left')
for col in [c for c in piv.columns if c.startswith('denuncias_')]:
    df[col] = df[col].fillna(0).astype(int)
df = df.drop(columns=['_join', 'nombre_norm'])
print(f'\\nDespués denuncias: {len(df.columns)} cols')
print(df.groupby('distrito_oficial')[['denuncias_violentas_distrito', 'denuncias_patrimoniales_distrito']].first().sort_values('denuncias_violentas_distrito', ascending=False).head(10).to_string())
"""))

cells.append(nbf.v4.new_markdown_cell("""## 5. Guardar dataset enriquecido v2"""))

cells.append(nbf.v4.new_code_cell("""# Sanity check final
new_cols = [c for c in df.columns if any(c.startswith(p) for p in [
    'estrato_nse', 'cat_dist_', 'count_500m_osm_', 'count_1km_osm_',
    'dist_nearest_m_osm_', 'n_comisarias_distrito', 'denuncias_'])]
print(f'Features NUEVAS: {len(new_cols)}')
for c in new_cols:
    print(f'  - {c}')

print(f'\\n=== Dataset v2 final: {df.shape} ===')
out_path = f'{PROCESSED}inmuebles_clean_v2.csv'
df.to_csv(out_path, index=False)
print(f'✓ Guardado: {out_path}')

# Sanity check sobre La Planicie y San Miguel
print('\\n=== Validación visual ===')
muestra = df[df['distrito_oficial'].isin(['La Molina', 'San Miguel', 'Miraflores', 'San Juan de Lurigancho'])]
print(muestra.groupby('distrito_oficial')[['estrato_nse', 'categoria_distrito',
       'n_comisarias_distrito', 'denuncias_violentas_distrito',
       'count_1km_osm_supermercados', 'count_1km_osm_universidades']].first().to_string())
"""))

# Escribir notebook
nb["cells"] = cells
nbf.write(nb, NB_PATH)
print(f"✅ {NB_PATH}")
