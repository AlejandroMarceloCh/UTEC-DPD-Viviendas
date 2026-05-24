"""Tabla manual de features socioeconómicas por distrito de Lima Metropolitana.

Sustituye al shapefile de estratos INEI (Lib1744) que no es descargable directo.
Cada distrito tiene:

  - `estrato_nse`: 5=Alto · 4=Medio Alto · 3=Medio · 2=Medio Bajo · 1=Bajo
  - `categoria_distrito`: 'establecido' / 'emergente' / 'popular'
    * establecido = premium consolidado, mercado maduro de alquiler/venta
    * emergente   = clase media activa, en crecimiento, alquiler creciente
    * popular     = clase media baja / popular, gran volumen poblacional

Criterios de asignación:
  - APEIM Niveles Socioeconómicos 2023-2024 (Zona 1-10 Lima)
  - INEI Lib1744 — Planos Estratificados 2020 (estrato dominante por distrito)
  - Precio mediano de alquiler en mercado público (Urbania/Adondevivir,
    independiente del dataset sesgado del proyecto)
  - Conocimiento inmobiliario público

LIMITACIÓN HONESTA: distritos muy heterogéneos (La Molina, Surco, Chorrillos)
tienen una asignación de estrato "dominante" que NO captura zonas premium
internas (La Planicie, Las Casuarinas). El point-in-polygon con shapefile
hubiera sido superior, pero no es viable en esta entrega. Para esos distritos
heterogéneos, la app complementa con `geo_index.lookup()` que pondera por
listings cercanos (mitigación parcial).
"""
from __future__ import annotations
import pandas as pd
import unicodedata

# Tabla maestra — 50 distritos de Lima Metropolitana + Callao
# Ordenada por nivel socioeconómico aproximado para revisión visual.
DISTRITOS_LIMA = [
    # === Establecidos premium (estrato 5 Alto) ===
    ('San Isidro',                5, 'establecido'),
    ('Miraflores',                5, 'establecido'),
    ('La Molina',                 4, 'establecido'),  # heterogéneo, baja a 4 promedio
    ('San Borja',                 5, 'establecido'),
    ('Santiago de Surco',         4, 'establecido'),  # heterogéneo Casuarinas vs Surco viejo
    ('Surco',                     4, 'establecido'),  # alias usado en algunos portales
    ('Barranco',                  4, 'establecido'),
    # === Emergentes / clase media activa ===
    ('Magdalena del Mar',         3, 'emergente'),
    ('Jesus Maria',               3, 'emergente'),
    ('Pueblo Libre',              3, 'emergente'),
    ('San Miguel',                3, 'emergente'),
    ('Lince',                     3, 'emergente'),
    ('Surquillo',                 3, 'emergente'),
    ('La Punta',                  4, 'emergente'),    # Callao
    ('San Bartolo',               3, 'emergente'),    # balneario
    # === Populares / medios bajos ===
    ('Chorrillos',                3, 'popular'),       # heterogéneo, Casuarinas eleva
    ('La Victoria',               2, 'popular'),
    ('Cercado de Lima',           2, 'popular'),       # alias INEI: Lima
    ('Lima',                      2, 'popular'),
    ('Breña',                     2, 'popular'),
    ('San Luis',                  2, 'popular'),
    ('San Martin de Porres',      2, 'popular'),
    ('Los Olivos',                2, 'popular'),
    ('Callao',                    2, 'popular'),
    ('Bellavista',                3, 'popular'),       # Callao, parte alta
    ('La Perla',                  2, 'popular'),
    ('Carmen de la Legua Reynoso',2, 'popular'),
    ('Cieneguilla',               3, 'popular'),       # heterogéneo, quintas elevan
    ('Punta Hermosa',             3, 'popular'),       # balneario
    ('Punta Negra',               3, 'popular'),       # balneario
    ('Pachacamac',                2, 'popular'),       # mix urbano + agrícola
    ('Lurin',                     2, 'popular'),
    ('Santa Rosa',                2, 'popular'),
    ('Pucusana',                  2, 'popular'),
    ('Santa Maria del Mar',       3, 'popular'),       # balneario premium
    ('Ate',                       2, 'popular'),
    ('Santa Anita',               2, 'popular'),
    ('Chaclacayo',                3, 'popular'),
    ('Mi Peru',                   1, 'popular'),
    ('Ventanilla',                1, 'popular'),
    # === Bajos (estrato 1 Bajo) ===
    ('Comas',                     2, 'popular'),
    ('Independencia',             2, 'popular'),
    ('Carabayllo',                1, 'popular'),
    ('Puente Piedra',             1, 'popular'),
    ('Ancon',                     1, 'popular'),
    ('Rimac',                     2, 'popular'),
    ('El Agustino',               1, 'popular'),
    ('San Juan de Lurigancho',    1, 'popular'),
    ('Lurigancho',                1, 'popular'),
    ('San Juan de Miraflores',    2, 'popular'),
    ('Villa Maria del Triunfo',   1, 'popular'),
    ('Villa el Salvador',         1, 'popular'),
]


def _norm(s: str) -> str:
    """Normaliza un nombre de distrito para matching robusto."""
    if pd.isna(s):
        return ''
    s = unicodedata.normalize('NFKD', str(s)).encode('ascii', 'ignore').decode()
    return s.upper().strip()


def get_district_table() -> pd.DataFrame:
    """Devuelve la tabla maestra como DataFrame con columna `nombre_norm` para join."""
    df = pd.DataFrame(DISTRITOS_LIMA, columns=['distrito_oficial', 'estrato_nse', 'categoria_distrito'])
    df['nombre_norm'] = df['distrito_oficial'].apply(_norm)
    return df


def attach_features(df_listings: pd.DataFrame,
                    col_distrito: str = 'distrito_oficial') -> pd.DataFrame:
    """Joinea las features socioeconómicas a un DataFrame de listings.

    Si un distrito del listings no está en la tabla, se asigna estrato=2,
    categoría='popular' (default conservador) y se imprime un warning.
    """
    df = df_listings.copy()
    df['_join'] = df[col_distrito].apply(_norm)
    table = get_district_table()
    out = df.merge(
        table[['nombre_norm', 'estrato_nse', 'categoria_distrito']],
        left_on='_join', right_on='nombre_norm', how='left',
    )
    missing = out[out['estrato_nse'].isna()][col_distrito].unique().tolist()
    if missing:
        print(f'⚠ Distritos sin entrada en tabla NSE (default estrato=2, popular): {missing}')
        out['estrato_nse'] = out['estrato_nse'].fillna(2).astype(int)
        out['categoria_distrito'] = out['categoria_distrito'].fillna('popular')
    else:
        out['estrato_nse'] = out['estrato_nse'].astype(int)
    return out.drop(columns=['_join', 'nombre_norm'])


if __name__ == '__main__':
    table = get_district_table()
    print(f'Tabla maestra: {len(table)} distritos')
    print(table['estrato_nse'].value_counts().sort_index().to_string())
    print()
    print('Categorías:')
    print(table['categoria_distrito'].value_counts().to_string())
    print()
    # Sanity check sobre el dataset del proyecto
    df = pd.read_csv('../data/processed/inmuebles_clean_v1.csv')
    enriched = attach_features(df)
    print('=== Listings con estrato/categoría ===')
    print(enriched.groupby(['estrato_nse', 'categoria_distrito']).size().to_string())
