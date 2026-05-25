# CHANGELOG v2 — proyecto DPD (ubIcA)

> PR: `AlejandroMarceloCh/feat/v2-imbalance-and-nse-fix` → `lmontoyas/main`
> Fecha: 2026-05-24 (Día 1) → 2026-05-31 (Día 7)
> Autor: Alejandro Marcelo · sobre la base original de Leo Montoya

---

## Resumen ejecutivo

Esta v2 ataca tres problemas del modelo v1:

1. **Desbalance natural del mercado limeño**: Lima es centralizada — 41 % de los avisos vienen de Miraflores y San Isidro. Zonas premium-residenciales (La Molina, San Borja Alto, Surco Las Casuarinas) tienen <100 listings de alquiler porque allá la gente **compra**, no alquila. El modelo v1 promedia con sesgo a la baja en esas zonas.
2. **Ausencia de variable socioeconómica**: el v1 no tenía nada que capture "estrato A intra-distrito". `distrito_oficial` solo promedia.
3. **4 bugs auditados en el pipeline original** (matriz NB05 invertida, mismatch 74 vs 77 features, `outlier_caps` huérfano, `features_log_transformed` con feature fantasma).

### Mejoras globales en test (mismo dataset, splits estratificados distintos):

| Métrica | v1 (RF, 74) | v2 (XGB, 95) | Δ      | Δ%      |
|---------|-------------|--------------|--------|---------|
| MAE_USD | 173.35      | **157.93**   | -15.43 | -8.9 %  |
| MAPE_pct| 15.92       | **15.74**    | -0.17  | -1.1 %  |
| RMSE_USD| 378.01      | **283.67**   | -94.34 | -25.0 % |
| R²      | 0.785       | **0.861**    | +0.076 | +9.7 %  |

**Distritos donde v2 mejora MAPE** (`delta_mape` negativo = mejor):

- Punta Hermosa: −30.78 pp · Comas: −10.44 pp · SJL: −10.29 pp · Jesús María: −9.50 pp
- SMP: −6.00 pp · Chorrillos: −5.35 pp · Magdalena: −3.27 pp · Pueblo Libre: −2.84 pp
- 14 distritos mejoran en total.

**Distritos donde v2 EMPEORA** (honestidad):

- La Molina: +18.00 pp (subpredicción → sobrepredicción). Las nuevas features socio-eco le dicen "premium" pero los listings REALES del dataset son los populares (Sol de La Molina). Ver §"Limitación honesta" abajo.
- Ate: +8.53 pp · Callao: +8.05 pp.

---

## Cambios estructurales

### 1. Features nuevas (29 columnas en `inmuebles_clean_v2.csv`)

| Familia | Columnas | Origen |
|---------|----------|--------|
| **NSE** | `estrato_nse` (1-5), `cat_dist_emergente`, `cat_dist_establecido`, `cat_dist_popular` (OHE) | Tabla manual `scripts/distritos_lima_features.py` basada en APEIM 2023-2024 + INEI Lib1744 + criterio inmobiliario |
| **POIs OSM** | `count_500m_osm_*`, `count_1km_osm_*`, `dist_nearest_m_osm_*` para 7 categorías (supermercados, malls, universidades, parques, farmacias, bancos, estaciones) | OSM Overpass · 11,200+ elementos · `data/external/osm_overpass/*.json` |
| **Seguridad estatal** | `n_comisarias_distrito` | CENACOM 2017 INEI · 149 comisarías Lima Metropolitana · `data/external/inei_comisarias/` |
| **Denuncias por tipo** | `denuncias_violentas_distrito`, `denuncias_patrimoniales_distrito`, `denuncias_otras_distrito` (año 2024) | MININTER 2018-2026 · 43 distritos × 7 modalidades · `data/external/mininter_denuncias/` |

### 2. Mejoras de pipeline

| Mejora | Dónde | Por qué |
|--------|-------|---------|
| **Split estratificado** | `08_pipeline_v2.ipynb` celda 4 | Cada split mantiene la misma proporción de premium/popular. Sin esto, La Molina (68 listings) podía concentrarse en train y dejar val/test sin cobertura. |
| **Bayesian smoothing target encoder (k=30)** | `08_pipeline_v2.ipynb` celda 6 | Villa El Salvador (1 listing) antes daba mean=5.85; ahora smoothed=6.68 (cerca del global mean 6.71). El modelo no se compromete con valores de pocos listings. |
| **outlier_caps activados** | `08_pipeline_v2.ipynb` celda 8 | Parche #3 cerrado: ahora se calcula percentil 99 en train y se aplica a los 3 splits. Antes el archivo estaba en `models/` pero ninguna celda lo aplicaba. |
| **Sample weighting** `1/sqrt(count)` | `08_pipeline_v2.ipynb` celda 16 | Miraflores (874 listings)=0.417 · La Molina (68 listings)=1.465 → **La Molina cuenta 3.51× más** durante entrenamiento. |
| **Optuna 20 trials** RF + XGB | `09_entrenamiento_v2.ipynb` celdas 5-7 | RF: n=176, depth=17, leaf=5. XGB: n=489, depth=11, lr=0.039. |

### 3. Bugs auditados cerrados

| # | Bug original | Fix v2 |
|---|--------------|--------|
| 1 | Matriz NB05 invertida → `modelo_final.joblib` era LR (peor R²) con métricas de XGBoost asignadas | `09_entrenamiento_v2.ipynb` celda 11: `best_model_name = res_test_df.iloc[0]['modelo']`. El nuevo `modelo_final_v2.joblib` guarda XGBoost con SUS PROPIAS métricas (R² 0.861, MAPE 15.74%). |
| 2 | Mismatch 74 vs 77 features (drop por correlación corría después del escalado) | `08_pipeline_v2.ipynb`: el feature selection corre ANTES del scaler. `feature_names_v2.joblib` y `feature_names_sc_v2.joblib` son consistentes (95 features ambos). |
| 3 | `outlier_caps.joblib` huérfano (nunca aplicado al training) | `08_pipeline_v2.ipynb` celda 8: ahora se calcula desde train y se aplica a los 3 splits. Nuevo `outlier_caps_v2.joblib`. |
| 4 | `features_log_transformed.joblib` listaba `dist_centro_km` que se eliminaba después | `08_pipeline_v2.ipynb` celda 10: la lista se computa post-drop. Nuevo `features_log_transformed_v2.joblib` (35 features, todas presentes). |

---

## Estructura nueva del repo

```
pipeline/
├── notebooks/
│   ├── 01-05 (originales de Leo, sin tocar)
│   ├── 06_diagnostico_v2.ipynb       ← cuantifica el bug
│   ├── 07_features_geo_v2.ipynb      ← features nuevas
│   ├── 08_pipeline_v2.ipynb          ← splits + smoothing + caps + weights
│   ├── 09_entrenamiento_v2.ipynb     ← Optuna + fix modelo_final
│   └── 10_comparativa_v1_v2.ipynb    ← métricas + casos resueltos
├── scripts/
│   ├── build_06_diagnostico.py       ← regenera notebook 06 desde Python
│   ├── build_07_features_v2.py       ← idem 07
│   ├── build_08_pipeline_v2.py       ← idem 08
│   ├── build_09_train_v2.py          ← idem 09
│   ├── build_10_comparativa.py       ← idem 10
│   └── distritos_lima_features.py    ← tabla manual NSE (reusable)
├── data/
│   ├── processed/
│   │   ├── inmuebles_clean_v2.csv    ← dataset enriquecido (3,348 × 105)
│   │   ├── X_train/val/test_v2.csv   ← splits estratificados
│   │   ├── df_train/val/test_v2_full.csv  ← splits con distrito_oficial preservado
│   │   └── resultados_test_v2.csv    ← métricas v2 (XGB ganador real)
│   └── external/                      ← NUEVO
│       ├── data_sources.md           ← investigación del Día 1
│       ├── inei_comisarias/          ← CENACOM 2017 procesado
│       ├── mininter_denuncias/       ← MININTER 2018-2026 procesado
│       ├── osm_overpass/             ← 7 categorías OSM raw
│       └── inei_estratos/            ← PDF INEI Lib1744 (referencia)
└── models/v2/                         ← NUEVO
    ├── 01-05_<modelo>_v2.joblib       ← 5 modelos re-entrenados
    ├── modelo_final_v2.joblib        ← XGBoost (objeto + métricas REALES)
    ├── target_enc_distrito_v2.joblib ← smoothed k=30
    ├── outlier_caps_v2.joblib        ← activos (no huérfanos)
    ├── features_log_transformed_v2.joblib
    ├── feature_names_v2.joblib       ← 95
    ├── feature_names_sc_v2.joblib    ← 95
    └── scaler_v2.joblib
```

---

## Cómo regenerar todo desde cero

```bash
# 1. Reproducir descargas de fuentes externas (Día 2)
# OSM Overpass — 7 queries separadas
python3 -c "
import requests, json
queries = {
  'supermercados.json': '[out:json][timeout:60];(node[\"shop\"=\"supermarket\"](-12.5,-77.2,-11.7,-76.7););out center;',
  # ... resto de queries en build_07_features_v2.py
}
for name, q in queries.items():
    r = requests.post('https://overpass-api.de/api/interpreter', data={'data': q.strip()})
    open(f'data/external/osm_overpass/{name}', 'w').write(r.text)
"

# CENACOM ZIP
curl -L -o data/external/inei_comisarias/cenacom_2017.zip \
  https://www.inei.gob.pe/media/DATOS_ABIERTOS/CENACOM/DATA/2017.zip
cd data/external/inei_comisarias && unzip -o cenacom_2017.zip && cd -

# MININTER denuncias
UA='Mozilla/5.0 ...'
curl -A "$UA" -L -o data/external/mininter_denuncias/denuncias_2018_2026.csv \
  "https://www.datosabiertos.gob.pe/sites/default/files/DATASET_Denuncias_Policiales_Ene%202018%20a%20Abr%202026.csv"

# 2. Re-correr los notebooks 06→10 en orden
for i in 06 07 08 09 10; do
  jupyter nbconvert --to notebook --execute notebooks/${i}_*.ipynb --output notebooks/${i}_*.ipynb
done

# 3. Validar resultados
cat data/processed/resultados_test_v2.csv
```

---

## Limitación honesta — zonas premium con N=0 comparables

**El problema:** La Planicie (La Molina), Las Casuarinas (Surco), San Borja Alto — son distritos donde los avisos de alquiler son **casi inexistentes** porque ahí la gente compra. El dataset original (Urbania + AdondeVivir + Properati) tiene 0-3 listings en esas zonas.

**Por qué v2 no lo arregla del todo:** ningún modelo puede aprender la distribución de precios de zonas que **no están en su training**. v2 mejora las métricas globales, mejora 14 distritos, pero en La Molina específicamente:
- v1 subpredecía (bias +7.81 % sobre los 15 listings de test)
- v2 ahora **sobrepredice** en los mismos listings (bias +35.32 %) porque las features socio-eco le dicen "premium" y el modelo predice "premium" — pero los 15 listings que SÍ existen son los populares (Sol de La Molina). Resultado: predice $1,200 cuando el listing es de $700.

**Lo que sí hicimos** (compromiso "cero data sintética"):
1. **Frontend honesto**: cuando `n_comparables < 20`, el resultado muestra un banner amarillo: *"Cobertura baja. Solo X avisos comparables en 1 km. Precisión esperada ±28 %."*
2. **HomeScreen explica el desbalance**: párrafo nuevo en "La data detrás" sobre el sesgo centralizado de Lima.
3. **`confidence: 'Baja'`** se devuelve en la API para esos casos.

**Para v2.1** (no en este PR):
- Re-scrapeo focused on Adondevivir/Properati/Casas.pe para zonas low-coverage.
- Shapefile INEI Lib1744 si conseguimos un mirror estable (granularidad manzana en vez de distrito).
- Scraping del Mapa del Delito MININTER georreferenciado (vs el agregado por distrito que usamos hoy).

---

## Integración al backend de la app (`app/backend/`)

> Esto es la demo de cómo se consume desde el producto. NO es parte del PR a Leo
> (el repo de Leo es solo el pipeline ML), pero existe en el proyecto general.

**Cambios mínimos en el backend:**

- `model_service.py` detecta `models/v2/modelo_final_v2.joblib` y carga v2; cae a v1 si no existe (env var `DPD_FORCE_V1=1` para tests legacy).
- `ml.py` rama por `model_service.mode == 'v2'` y llama a `build_features_v2()`.
- `ml_v2.py` (NUEVO) — build_features_v2 con las 95 features (reusa `geo_lookup` original).
- `osm_lookup.py` (NUEVO) — KD-trees por categoría OSM, lookup por (lat, lng).
- `distrito_features.py` (NUEVO) — carga tabla NSE + comisarías + denuncias por distrito.
- `tests/test_v2_features.py` (NUEVO) — 12 tests senior end-to-end.

**Frontend (`app/screens.jsx` + `index.html`):**

- Banner `low-coverage` en `FairValueResult` cuando `n_comparables < 20`.
- HomeScreen "La data detrás" actualizada: 95 features, MAPE 15.74 %, párrafo sobre el desbalance.

**Tests pasando:** 42 (30 originales + 12 v2 senior · 2 v1-only saltados en modo v2).

---

## Métricas de éxito definidas a priori (del plan_v2.md)

- ✅ MAPE global v2 ≤ MAPE v1 (15.74 ≤ 15.92). **Cumplido**.
- ⚠️ MAPE en distritos low-coverage baja 25 % relativo. **Parcial** — algunos distritos sí (Punta Hermosa -64 %, Comas -50 %, SJL -28 %), otros empeoran (La Molina +91 % por flip de bias).
- ❌ Predicción La Planicie premium > $1,500. **No cumplido** — v2 predice $720 (v1 daba $769). Es limitación de DATOS, no de modelo (zero data sintética). Mitigación: UX honesta.
- ✅ Los 4 bugs auditados cerrados.
- ✅ Tests pytest pasando (42).
- ✅ PR mergeable sin conflictos.

---

## Próximos pasos sugeridos para Leo

1. **Mergear este PR** y usar `modelo_final_v2.joblib` como nuevo `modelo_final.joblib` (XGBoost, 95 features).
2. **Re-scrape de Urbania/Adondevivir** focused en La Molina, San Borja Alto, Surco — la única forma real de cerrar el gap premium-low-coverage.
3. **Considerar Mapa del Delito georreferenciado** (scraping con Playwright, ~1-2 días) para reemplazar el agregado por distrito.
4. Si APEIM/INEI Lib1744 publican el shapefile, sustituir la tabla manual `distritos_lima_features.py` por point-in-polygon real.
