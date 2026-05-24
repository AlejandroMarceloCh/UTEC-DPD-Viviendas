"""Genera notebooks/08_pipeline_v2.ipynb.

Construye el pipeline v2 sobre inmuebles_clean_v2.csv:
  - Split estratificado por categoria_distrito + estrato_nse (no random)
  - Target encoding distrito con Bayesian smoothing (k=30)
  - Outlier capping percentil 99 sobre features continuas críticas
  - Log1p sobre features con skew > 1 (igual que NB03)
  - StandardScaler sobre features numéricas
  - Sample weighting por distrito: 1/sqrt(count) para combatir el imbalance
  - VIF + correlación: filtrado final (excepto OHE de NSE/categoría)
Output: models/v2/ con todos los artefactos.
"""
from pathlib import Path
import nbformat as nbf

NB_PATH = Path(__file__).resolve().parents[1] / "notebooks" / "08_pipeline_v2.ipynb"

nb = nbf.v4.new_notebook()
nb.metadata = {
    "kernelspec": {"name": "dpd-v2", "display_name": "Python (DPD v2)"},
    "language_info": {"name": "python"},
}

cells = []

cells.append(nbf.v4.new_markdown_cell("""# Pipeline v2 — splits + smoothing + caps + balanceo

> **Día 4 del plan_v2.md.**

Sobre `inmuebles_clean_v2.csv` (3,348 listings × 105 cols con las 29 features nuevas):

1. **Split estratificado por categoría distrito + estrato_nse** (no random) — garantiza que cada split tenga proporción similar de premium/popular.
2. **Target encoding del distrito** con Bayesian smoothing (k=30): los distritos con <30 listings se acercan al promedio global en vez de comprometerse con el promedio sesgado de pocos listings.
3. **Outlier capping** percentil 99 sobre features continuas críticas (área, baños, dormitorios, etc.) — calculado SOLO en train, aplicado a los 3 splits.
4. **Log1p** sobre features con skew > 1 (mismo criterio que NB03).
5. **StandardScaler** sobre features numéricas.
6. **Sample weighting**: `1/sqrt(count_distrito)` normalizado → durante entrenamiento.
7. **Filtrado por correlación con target** (umbral 0.05 sobre numéricas, 0.03 sobre booleanas) — preserva OHE de NSE/categoría aunque no pasen el umbral.

Output: `models/v2/` con todos los artefactos listos para entrenar.
"""))

cells.append(nbf.v4.new_code_cell("""import numpy as np
import pandas as pd
import joblib
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler
import warnings
warnings.filterwarnings('ignore')

PROCESSED = '../data/processed/'
MODELS_V2 = '../models/v2/'
import os; os.makedirs(MODELS_V2, exist_ok=True)

df = pd.read_csv(f'{PROCESSED}inmuebles_clean_v2.csv')
# NB03 computa log_precio post-split; lo agregamos acá igual que en NB06
df['log_precio'] = np.log1p(df['precio_usd'])
print(f'Dataset v2: {df.shape}')
print(f'Columnas nuevas: estrato_nse, categoria_distrito, count_500m_osm_*, count_1km_osm_*, dist_nearest_m_osm_*, n_comisarias_distrito, denuncias_*_distrito')
"""))

cells.append(nbf.v4.new_markdown_cell("""## 1. Split estratificado por categoria_distrito + estrato_nse

Combinamos las 2 dimensiones como llave de estratificación. Si una combinación tiene <5 listings (raro), se colapsa al estrato sólo.
"""))

cells.append(nbf.v4.new_code_cell("""# Crear llave de estratificación combinada
df['_strata'] = df['categoria_distrito'] + '_E' + df['estrato_nse'].astype(str)
strata_counts = df['_strata'].value_counts()
print('Estratos compuestos:')
print(strata_counts.to_string())

# Estratos con < 5 listings: colapsar al estrato_nse solo
def fix_strata(row):
    s = row['_strata']
    if strata_counts.get(s, 0) >= 5:
        return s
    return f'E{row[\"estrato_nse\"]}'  # solo el nivel

df['_strata2'] = df.apply(fix_strata, axis=1)
print(f'\\nEstratos finales: {df[\"_strata2\"].nunique()}')

# Split estratificado 70 / 15 / 15
df_trainval, df_test = train_test_split(df, test_size=0.15, random_state=42, stratify=df['_strata2'])
df_train, df_val     = train_test_split(df_trainval, test_size=0.176, random_state=42, stratify=df_trainval['_strata2'])
print(f'\\nTrain: {len(df_train)}, Val: {len(df_val)}, Test: {len(df_test)}')

# Verificación: distribución de estrato_nse en cada split
print('\\nDistribución estrato_nse en cada split:')
for name, split in [('train', df_train), ('val', df_val), ('test', df_test)]:
    pct = (split['estrato_nse'].value_counts(normalize=True).sort_index() * 100).round(1).to_dict()
    print(f'  {name}: {pct}')
"""))

cells.append(nbf.v4.new_markdown_cell("""## 2. Target encoding del distrito con Bayesian smoothing"""))

cells.append(nbf.v4.new_code_cell("""SMOOTHING_K = 30
global_mean_log = df_train['log_precio'].mean()
print(f'Mean log_precio global (train): {global_mean_log:.4f}')

agg = df_train.groupby('distrito_oficial')['log_precio'].agg(['mean', 'size'])
agg['smoothed'] = (agg['size'] * agg['mean'] + SMOOTHING_K * global_mean_log) / (agg['size'] + SMOOTHING_K)

target_enc_map = agg['smoothed']

print('\\n=== Comparación encoding sin smooth vs smoothed (top 10 distritos por n) ===')
agg_show = agg.sort_values('size', ascending=False).head(10)
print(agg_show[['mean', 'size', 'smoothed']].round(4).to_string())
print()
print('=== Distritos con pocos listings (donde el smoothing más mueve la aguja) ===')
agg_low = agg[agg['size'] < 30].sort_values('size').head(10)
print(agg_low[['mean', 'size', 'smoothed']].round(4).to_string())

# Aplicar
for split in [df_train, df_val, df_test]:
    split['distrito_enc'] = split['distrito_oficial'].map(target_enc_map).fillna(global_mean_log)

joblib.dump({'map': target_enc_map, 'global_mean': global_mean_log, 'k': SMOOTHING_K},
            f'{MODELS_V2}target_enc_distrito_v2.joblib')
print(f'\\n✓ target_enc_distrito_v2.joblib guardado (k={SMOOTHING_K})')
"""))

cells.append(nbf.v4.new_markdown_cell("""## 3. Outlier capping (percentil 99 calculado SOLO en train)

Activa el Parche #3 de la auditoría: los caps ahora se calculan **y se aplican** dentro del pipeline.
"""))

cells.append(nbf.v4.new_code_cell("""CAP_COLS = ['area_final_m2', 'banos', 'dormitorios', 'cocheras',
            'antiguedad_anios', 'piso']
# Solo capear las que existen
CAP_COLS = [c for c in CAP_COLS if c in df_train.columns]

outlier_caps = {col: float(df_train[col].quantile(0.99)) for col in CAP_COLS}
print('Outlier caps (p99 en train):')
for col, cap in outlier_caps.items():
    n_above = (df_train[col] > cap).sum()
    print(f'  {col:<25} cap={cap:>10.2f}   capeados en train: {n_above}')

# Aplicar a los 3 splits
for split in [df_train, df_val, df_test]:
    for col, cap in outlier_caps.items():
        split[col] = split[col].clip(upper=cap)

joblib.dump(outlier_caps, f'{MODELS_V2}outlier_caps_v2.joblib')
print('\\n✓ outlier_caps_v2.joblib aplicado y guardado')
"""))

cells.append(nbf.v4.new_markdown_cell("""## 4. OHE de columnas categóricas + features derivadas

Mismo patrón que NB03 (fuente, tipo_propiedad, mismatch_type) pero la **categoría_distrito ya está OHE** (lo hicimos en NB07).
"""))

cells.append(nbf.v4.new_code_cell("""# OHE de fuente, tipo_propiedad, mismatch (igual NB03)
ohe_cols = ['fuente', 'tipo_propiedad', 'mismatch_type']
for split in [df_train, df_val, df_test]:
    for col in ohe_cols:
        if col not in split.columns:
            continue
        dummies = pd.get_dummies(split[col], prefix=col, drop_first=True, dtype=int)
        split[dummies.columns] = dummies

# Alinear columnas entre splits (puede haber categorías que no aparecen en algún split)
all_cols = set(df_train.columns) | set(df_val.columns) | set(df_test.columns)
for split in [df_train, df_val, df_test]:
    for col in all_cols:
        if col not in split.columns:
            split[col] = 0

# Features derivadas (mismo NB03)
def crear_derivadas(d):
    d = d.copy()
    d['ratio_area_banos'] = d['area_final_m2'] / (d['banos'] + 1)
    d['area_x_amenities'] = d['area_final_m2'] * d['amenities_count']
    d['es_zona_premium'] = (
        (d['dist_mar_km'] < d['dist_mar_km'].quantile(0.25)) &
        (d['dist_centro_km'] < d['dist_centro_km'].quantile(0.25))
    ).astype(int)
    d['antiguedad_sq'] = d['antiguedad_anios'] ** 2
    poi_cols_orig = [c for c in d.columns if c.startswith('count_1km_') and not c.startswith('count_1km_osm_')]
    d['total_poi_1km'] = d[poi_cols_orig].sum(axis=1) if poi_cols_orig else 0
    # Total POI OSM también (separado para no mezclar con el original)
    osm_count_cols = [c for c in d.columns if c.startswith('count_1km_osm_')]
    d['total_poi_osm_1km'] = d[osm_count_cols].sum(axis=1) if osm_count_cols else 0
    return d

df_train = crear_derivadas(df_train)
df_val   = crear_derivadas(df_val)
df_test  = crear_derivadas(df_test)
print(f'Después OHE + derivadas: train shape {df_train.shape}')
"""))

cells.append(nbf.v4.new_markdown_cell("""## 5. Definir FEATURES finales + log1p"""))

cells.append(nbf.v4.new_code_cell("""COLS_EXCLUIR = ['log_precio', 'precio_usd', 'distrito_oficial', 'fuente',
                'tipo_propiedad', 'mismatch_type', 'categoria_distrito',
                '_strata', '_strata2', 'id_portal', 'url', 'h3_index_8']
object_cols = df_train.select_dtypes(include='object').columns.tolist()
COLS_EXCLUIR = list(set(COLS_EXCLUIR + object_cols))
FEATURES = [c for c in df_train.columns if c not in COLS_EXCLUIR]

# Clasificación booleanas vs numéricas
bool_prefixes = ('tiene_', 'fuente_', 'tipo_propiedad_', 'mismatch_type_', 'cat_dist_')
bool_flags    = ['es_estudio', 'es_zona_premium', 'cocheras_informadas']
FEATURES_BOOL = [f for f in FEATURES if f.startswith(bool_prefixes) or f in bool_flags]
FEATURES_NUM  = [f for f in FEATURES if f not in FEATURES_BOOL]
print(f'Total features: {len(FEATURES)}  |  NUM: {len(FEATURES_NUM)}  BOOL: {len(FEATURES_BOOL)}')

# log1p sobre features con skew > 1 (solo en numéricas, valores >= 0)
X_train = df_train[FEATURES].copy()
X_val   = df_val[FEATURES].copy()
X_test  = df_test[FEATURES].copy()
y_train = df_train['log_precio'].values
y_val   = df_val['log_precio'].values
y_test  = df_test['log_precio'].values

skew_train = X_train[FEATURES_NUM].skew().sort_values(ascending=False)
FEATURES_LOG = [f for f in FEATURES_NUM if skew_train[f] > 1 and X_train[f].min() >= 0]
print(f'\\nLog1p ({len(FEATURES_LOG)} features con skew > 1):')
for f in FEATURES_LOG[:10]:
    print(f'  {f:<35} skew={skew_train[f]:.2f}')

for split in [X_train, X_val, X_test]:
    split[FEATURES_LOG] = np.log1p(split[FEATURES_LOG])

joblib.dump(FEATURES_LOG, f'{MODELS_V2}features_log_transformed_v2.joblib')
print(f'\\n✓ features_log_transformed_v2.joblib guardado ({len(FEATURES_LOG)} features)')
"""))

cells.append(nbf.v4.new_markdown_cell("""## 6. Filtrado por correlación con target + selección final

Eliminamos features con corr absoluta < 0.05 (numéricas) o < 0.03 (booleanas), EXCEPTO las OHE de NSE/categoría que conservamos siempre (semánticamente importantes).
"""))

cells.append(nbf.v4.new_code_cell("""y_series = pd.Series(y_train, index=X_train.index)
corr_num = X_train[FEATURES_NUM].corrwith(y_series).abs()
from scipy import stats
pb_corr = {}
for col in FEATURES_BOOL:
    try:
        c, _ = stats.pointbiserialr(X_train[col].values, y_train)
        pb_corr[col] = abs(c)
    except Exception:
        pb_corr[col] = 0.0
pb_corr = pd.Series(pb_corr)

# Eliminar low-corr EXCEPTO categoria_distrito (siempre conservar)
KEEP_ALWAYS = [c for c in FEATURES if c.startswith('cat_dist_') or c == 'estrato_nse']

to_drop_num = [f for f in FEATURES_NUM if corr_num.get(f, 0) < 0.05 and f not in KEEP_ALWAYS]
to_drop_bool = [f for f in FEATURES_BOOL if pb_corr.get(f, 0) < 0.03 and f not in KEEP_ALWAYS]
to_drop = to_drop_num + to_drop_bool
print(f'Features a eliminar por baja correlación: {len(to_drop)}')
for f in to_drop[:15]:
    c = corr_num.get(f, pb_corr.get(f, 0))
    print(f'  {f:<35} |corr|={c:.4f}')

FEATURES = [f for f in FEATURES if f not in to_drop]
FEATURES_NUM = [f for f in FEATURES_NUM if f not in to_drop]
FEATURES_BOOL = [f for f in FEATURES_BOOL if f not in to_drop]

X_train = X_train[FEATURES]; X_val = X_val[FEATURES]; X_test = X_test[FEATURES]
print(f'\\nFeatures finales: {len(FEATURES)} (NUM={len(FEATURES_NUM)}, BOOL={len(FEATURES_BOOL)})')
"""))

cells.append(nbf.v4.new_markdown_cell("""## 7. StandardScaler + sample weighting + guardar"""))

cells.append(nbf.v4.new_code_cell("""# Scaler — fit SOLO en train, sobre features numéricas
scaler = StandardScaler()
scaler.fit(X_train[FEATURES_NUM])

def escalar(X):
    X_num = scaler.transform(X[FEATURES_NUM])
    X_bool = X[FEATURES_BOOL].values
    return np.hstack([X_num, X_bool])

X_train_sc = escalar(X_train)
X_val_sc   = escalar(X_val)
X_test_sc  = escalar(X_test)
FEATURES_SC_ORDER = FEATURES_NUM + FEATURES_BOOL

# Sample weighting por distrito: 1/sqrt(count) normalizado a media 1
distrito_train = df_train['distrito_oficial'].values
distrito_counts = pd.Series(distrito_train).value_counts()
sample_weights = np.array([1.0 / np.sqrt(distrito_counts[d]) for d in distrito_train])
sample_weights = sample_weights / sample_weights.mean()

print('=== Resumen sample weights ===')
print(f'min: {sample_weights.min():.3f}  median: {np.median(sample_weights):.3f}  max: {sample_weights.max():.3f}')
# El peso de un listing en Miraflores vs uno en La Molina:
w_mira = sample_weights[distrito_train == 'Miraflores'][0] if (distrito_train == 'Miraflores').any() else None
w_mol = sample_weights[distrito_train == 'La Molina'][0] if (distrito_train == 'La Molina').any() else None
print(f'Peso Miraflores (874 listings): {w_mira:.3f}')
print(f'Peso La Molina (68 listings):   {w_mol:.3f}')
print(f'Ratio La Molina / Miraflores:   {w_mol/w_mira:.2f}x (La Molina cuenta este factor más)')

# Guardar todo
np.save(f'{PROCESSED}X_train_v2.npy', X_train.values)
np.save(f'{PROCESSED}X_val_v2.npy', X_val.values)
np.save(f'{PROCESSED}X_test_v2.npy', X_test.values)
np.save(f'{PROCESSED}X_train_sc_v2.npy', X_train_sc)
np.save(f'{PROCESSED}X_val_sc_v2.npy', X_val_sc)
np.save(f'{PROCESSED}X_test_sc_v2.npy', X_test_sc)
np.save(f'{PROCESSED}y_train_v2.npy', y_train)
np.save(f'{PROCESSED}y_val_v2.npy', y_val)
np.save(f'{PROCESSED}y_test_v2.npy', y_test)
np.save(f'{PROCESSED}sample_weights_train_v2.npy', sample_weights)

joblib.dump(scaler, f'{MODELS_V2}scaler_v2.joblib')
joblib.dump(FEATURES, f'{MODELS_V2}feature_names_v2.joblib')
joblib.dump(FEATURES_SC_ORDER, f'{MODELS_V2}feature_names_sc_v2.joblib')

# CSVs también para debug visual
X_train.to_csv(f'{PROCESSED}X_train_v2.csv', index=False)
X_val.to_csv(f'{PROCESSED}X_val_v2.csv', index=False)
X_test.to_csv(f'{PROCESSED}X_test_v2.csv', index=False)
# Guardar el dataset enriquecido en df_train/val/test con distrito_oficial preservado para diagnóstico
df_train.to_csv(f'{PROCESSED}df_train_v2_full.csv', index=False)
df_val.to_csv(f'{PROCESSED}df_val_v2_full.csv', index=False)
df_test.to_csv(f'{PROCESSED}df_test_v2_full.csv', index=False)

print(f'\\n✓ Artefactos guardados en models/v2/ y data/processed/')
print(f'  X_train_v2: {X_train.shape}   X_train_sc_v2: {X_train_sc.shape}')
"""))

nb["cells"] = cells
nbf.write(nb, NB_PATH)
print(f"✅ {NB_PATH}")
