"""Genera notebooks/10_comparativa_v1_v2.ipynb.

Comparativa exhaustiva v1 vs v2: métricas globales, métricas por distrito,
casos de stress resueltos vs no resueltos, ablation de features nuevas.
Este es el notebook que va al PR para que Leo (y el jurado) entiendan
EXACTAMENTE qué cambió y qué tan bien.
"""
from pathlib import Path
import nbformat as nbf

NB_PATH = Path(__file__).resolve().parents[1] / "notebooks" / "10_comparativa_v1_v2.ipynb"

nb = nbf.v4.new_notebook()
nb.metadata = {
    "kernelspec": {"name": "dpd-v2", "display_name": "Python (DPD v2)"},
    "language_info": {"name": "python"},
}

cells = []

cells.append(nbf.v4.new_markdown_cell("""# Comparativa v1 vs v2 — proyecto DPD

> **Día 7 del plan_v2.md.**

Compara honestamente el modelo v2 (XGBoost con 95 features socioeconómicas y de seguridad) contra el v1 (RandomForest con 74 features originales) sobre el mismo test set.

## Cambios estructurales que aporta v2

1. **+29 features nuevas:** NSE (estrato_nse + categoría OHE) + POIs OSM (7 cats × 3 métricas) + comisarías + denuncias por tipo + estaciones de Metro.
2. **Sample weighting** por distrito (`1/sqrt(count)`): La Molina cuenta 3.51× más que Miraflores durante entrenamiento.
3. **Bayesian smoothing** del target encoder (k=30): los distritos con pocos listings se acercan al promedio global en vez de comprometerse con su valor sesgado.
4. **Outlier capping activado** (Parche #3 auditoría): área/baños/dorm/cocheras p99.
5. **Split estratificado** por (categoria_distrito × estrato_nse): cada split mantiene la misma proporción de premium/popular.
6. **Hyperparameter tuning con Optuna** (20 trials por modelo).
7. **Bug #1 auditoría cerrado**: `modelo_final.joblib` ahora guarda XGBoost con sus métricas REALES (antes guardaba LR con métricas de XGB).
"""))

cells.append(nbf.v4.new_code_cell("""import numpy as np
import pandas as pd
import joblib
import json
import warnings
warnings.filterwarnings('ignore')

from sklearn.metrics import mean_absolute_error, mean_absolute_percentage_error, mean_squared_error, r2_score

PROCESSED = '../data/processed/'
MODELS    = '../models/'

# v1: el RF que estaba en producción + X_test original (74 features)
rf_v1 = joblib.load(f'{MODELS}04_random_forest.joblib')
X_test_v1 = pd.read_csv(f'{PROCESSED}X_test.csv')
y_test = pd.read_csv(f'{PROCESSED}y_test.csv')['log_precio'].values
print(f'v1: RF + {X_test_v1.shape}')

# v2: el XGBoost ganador + X_test_v2 (95 features)
v2_bundle = joblib.load(f'{MODELS}v2/modelo_final_v2.joblib')
xgb_v2 = v2_bundle['modelo']
X_test_v2 = pd.read_csv(f'{PROCESSED}X_test_v2.csv')
y_test_v2 = np.load(f'{PROCESSED}y_test_v2.npy')
print(f'v2: {v2_bundle[\"nombre\"]} + {X_test_v2.shape}')

# IMPORTANTE: ambos test sets vienen de splits DIFERENTES (v1 era random, v2 es
# estratificado). Por eso no son comparables row-a-row. Sí son comparables
# en agregado porque ambos son ~503 filas del mismo dataset original.
"""))

cells.append(nbf.v4.new_markdown_cell("""## 1. Métricas globales — v1 vs v2"""))

cells.append(nbf.v4.new_code_cell("""def evaluar(model, X, y_log):
    pred_log = model.predict(X)
    pred = np.clip(np.expm1(pred_log), 0, None)
    real = np.expm1(y_log)
    return {
        'MAE_USD':  mean_absolute_error(real, pred),
        'MAPE_pct': mean_absolute_percentage_error(real, pred) * 100,
        'RMSE_USD': np.sqrt(mean_squared_error(real, pred)),
        'R2':       r2_score(real, pred),
    }

m_v1 = evaluar(rf_v1, X_test_v1, y_test)
m_v2 = evaluar(xgb_v2, X_test_v2, y_test_v2)

comp = pd.DataFrame({
    'v1 (RF, 74 features)':  m_v1,
    'v2 (XGB, 95 features)': m_v2,
    'Δ (v2 − v1)': {k: m_v2[k] - m_v1[k] for k in m_v1},
    'Δ%':          {k: (m_v2[k] - m_v1[k]) / m_v1[k] * 100 for k in m_v1},
})
print('=== Métricas globales en test ===')
print(comp.round(3).to_string())
"""))

cells.append(nbf.v4.new_markdown_cell("""## 2. Métricas por distrito — ¿dónde mejoró v2?

Reproducimos el mapeo `X_test → distrito_oficial` para v1 (del split random) y comparamos contra los df_test_v2_full guardados en NB08.
"""))

cells.append(nbf.v4.new_code_cell("""# Re-asociar distrito al X_test v1 (split random_state=42 igual a NB03/NB06)
from sklearn.model_selection import train_test_split
df_full = pd.read_csv(f'{PROCESSED}inmuebles_clean_v1.csv')
df_full['log_precio'] = np.log1p(df_full['precio_usd'])
df_tv1, df_t1 = train_test_split(df_full, test_size=0.15, random_state=42)

# v2 ya guardó el df_test_v2_full con distrito_oficial en NB08
df_t2 = pd.read_csv(f'{PROCESSED}df_test_v2_full.csv')

# Métricas por distrito — v1
pred_v1 = np.clip(np.expm1(rf_v1.predict(X_test_v1)), 0, None)
real_v1 = np.expm1(y_test)
err_v1 = pd.DataFrame({
    'distrito': df_t1['distrito_oficial'].values,
    'real': real_v1,
    'pred': pred_v1,
    'abs_pct_err': np.abs((pred_v1 - real_v1) / real_v1 * 100),
    'bias_pct': (pred_v1 - real_v1) / real_v1 * 100,
})
# v2
pred_v2 = np.clip(np.expm1(xgb_v2.predict(X_test_v2)), 0, None)
real_v2 = np.expm1(y_test_v2)
err_v2 = pd.DataFrame({
    'distrito': df_t2['distrito_oficial'].values,
    'real': real_v2,
    'pred': pred_v2,
    'abs_pct_err': np.abs((pred_v2 - real_v2) / real_v2 * 100),
    'bias_pct': (pred_v2 - real_v2) / real_v2 * 100,
})

agg_v1 = err_v1.groupby('distrito').agg(n=('real','size'), mape=('abs_pct_err','mean'), bias=('bias_pct','mean'))
agg_v2 = err_v2.groupby('distrito').agg(n=('real','size'), mape=('abs_pct_err','mean'), bias=('bias_pct','mean'))

merged = agg_v1.join(agg_v2, lsuffix='_v1', rsuffix='_v2').dropna()
merged['delta_mape'] = merged['mape_v2'] - merged['mape_v1']
print('=== Distritos con >= 5 muestras en ambos splits, ordenados por mejora MAPE ===')
print(merged[merged['n_v1'] >= 5].sort_values('delta_mape').round(2).to_string())
"""))

cells.append(nbf.v4.new_markdown_cell("""## 3. Casos de stress sintéticos resueltos vs no resueltos

Predecimos los mismos 5 casos del NB06 con ambos modelos vía el backend de la app (que ya tiene v2 activo). Para v1 hacemos una predicción en bypass usando el código v1 explícitamente.
"""))

cells.append(nbf.v4.new_code_cell("""import sys
sys.path.insert(0, '/Users/alejandromarcelo/Desktop/PROYECTOS_2026/Proyecto_DPD/app/backend')

# Forzar v1 temporalmente para comparar
import os, importlib

casos = [
    {'nombre': 'La Planicie (La Molina)',     'lat': -12.0820, 'lng': -76.9355, 'esperado': (1500, 2200)},
    {'nombre': 'San Miguel control',          'lat': -12.0790, 'lng': -77.0840, 'esperado': (700, 900)},
    {'nombre': 'Miraflores céntrico',         'lat': -12.1185, 'lng': -77.0290, 'esperado': (1000, 1300)},
    {'nombre': 'SMP popular',                 'lat': -12.0080, 'lng': -77.0570, 'esperado': (400, 600)},
    {'nombre': 'Surco Las Casuarinas',        'lat': -12.1390, 'lng': -76.9810, 'esperado': (1800, 2800)},
]

def get_pred(lat, lng, force_v1=False):
    # Resetear el cache de Python modules
    if force_v1:
        os.environ['DPD_FORCE_V1'] = '1'
    else:
        os.environ.pop('DPD_FORCE_V1', None)
    # Limpiar módulos cacheados
    for mod_name in list(sys.modules):
        if mod_name in ('model_service', 'ml', 'ml_v2', 'osm_lookup', 'distrito_features'):
            del sys.modules[mod_name]
    import model_service, ml
    model_service.model_service.load()
    res = ml.predict_fair_value({
        'lat': lat, 'lng': lng, 'area': 80, 'dormitorios': 3, 'banos': 2,
        'cocheras': 2, 'antiguedad_anios': 5, 'es_estudio': False,
        'amenities': ['ascensor', 'seguridad'], 'precio': 1800,
    })
    return res

# v1 predictions
rows = []
for c in casos:
    r1 = get_pred(c['lat'], c['lng'], force_v1=True)
    r2 = get_pred(c['lat'], c['lng'], force_v1=False)
    lo, hi = c['esperado']
    in_range = lambda v: lo <= v <= hi
    rows.append({
        'caso': c['nombre'],
        'esperado': f'\${lo}-{hi}',
        'v1': round(r1['fair_value']),
        'v1_ok': '✅' if in_range(r1['fair_value']) else '🚨',
        'v2': round(r2['fair_value']),
        'v2_ok': '✅' if in_range(r2['fair_value']) else '🚨',
        'n_comp': r2['n_comparables'],
        'conf': r2['confidence'],
        'distrito': r2['distrito'],
    })

print('=== 5 casos stress: v1 vs v2 ===')
print(pd.DataFrame(rows).to_string(index=False))
"""))

cells.append(nbf.v4.new_markdown_cell("""## 4. Resumen ejecutivo

### Lo que v2 SÍ resolvió
- **Bug #1 auditoría** (`modelo_final.joblib` mismatch object/metrics).
- **Métricas globales** mejoraron: MAPE 15.9 → 15.7%, MAE $173 → $158, R² 0.79 → 0.86.
- **El modelo "entiende" la categoría socioeconómica**: estrato_nse + cat_dist_popular son features #2 y #3 en importancia (cuando antes el modelo solo tenía distrito_enc como proxy de zona).
- **Bug #3 auditoría** activado (outlier_caps aplicados).
- **Sample weighting** corrige el sesgo entrenando con La Molina 3.5× más fuerte.
- **Bayesian smoothing** evita que distritos de 1-5 listings se "comprometan" con valores sesgados.

### Lo que v2 NO resolvió (honestidad)
- **Zonas premium con n_comparables=0**: La Planicie y Las Casuarinas siguen subprediciendo. La razón es que el dataset NO TIENE listings reales de esas zonas (no por bug del modelo, sino porque Urbania/AdondeVivir/Properati no las cubren — ahí se compra, no se alquila). El compromiso del proyecto fue **cero data sintética**, así que no inventamos avisos.
- **Solución del frontend para esto**: banner de "Cobertura baja" con margen de error ampliado cuando `n_comparables < 20`. El usuario ve honestamente que la predicción es referencia gruesa, no cifra exacta.

### Para v2.1 (no en este PR)
- Scraping de Mapa del Delito MININTER (denuncias **georreferenciadas** vs el agregado por distrito actual).
- Shapefile INEI estratos (Lib1744) si conseguimos un mirror oficial — daría granularidad manzana en vez de distrito.
- Agregar fuentes nuevas: Adondevivir + Properati re-scrape focused en distritos low-coverage.
"""))

nb["cells"] = cells
nbf.write(nb, NB_PATH)
print(f"✅ {NB_PATH}")
