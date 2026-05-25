# PredictRent — Predicción de precios de alquiler en Lima Metropolitana

## Descripción
Modelo de machine learning para predecir el precio mensual de alquiler (en USD) de inmuebles en Lima Metropolitana y Callao, a partir de características estructurales, geoespaciales y de amenities obtenidas mediante web scraping de portales inmobiliarios (Urbania, AdondeVivir, Properati).

## Dataset
- **Fuente:** Web scraping con Playwright + httpx
- **Registros:** 3,348 listings
- **Features:** 73 columnas (estructurales, geoespaciales, POIs, criminalidad, amenities binarias)
- **Target:** `precio_usd` — precio mensual de alquiler en USD

## Estructura del proyecto
```
predictrent/
├── data/
│   ├── raw/              ← Datos originales (no modificar)
│   └── processed/        ← Datos limpios y feature-engineered
├── notebooks/
│   ├── 01_limpieza.ipynb
│   ├── 02_eda.ipynb
│   ├── 03_feature_engineering.ipynb
│   ├── 04_entrenamiento_modelos.ipynb
│   └── 05_evaluacion_seleccion.ipynb
├── src/
│   ├── preprocessing.py  ← Funciones de limpieza reutilizables
│   ├── features.py       ← Funciones de feature engineering
│   └── evaluation.py     ← Funciones de métricas y visualización
├── models/               ← Modelos serializados (.joblib)
├── reports/
│   └── figures/          ← Gráficos generados en los notebooks
└── README.md
```

## Secuencia de ejecución
1. `notebooks/01_limpieza.ipynb` — Limpieza y validación de datos
2. `notebooks/02_eda.ipynb` — Análisis exploratorio
3. `notebooks/03_feature_engineering.ipynb` — Preparación de features
4. `notebooks/04_entrenamiento_modelos.ipynb` — Entrenamiento y experimentación
5. `notebooks/05_evaluacion_seleccion.ipynb` — Comparación de métricas y selección final

## Modelos evaluados
- Linear Regression (baseline)
- Ridge Regression
- Lasso Regression
- Random Forest
- XGBoost / LightGBM

## Métricas principales
| Métrica | Descripción |
|---------|-------------|
| RMSE    | Root Mean Squared Error — penaliza errores grandes |
| MAE     | Mean Absolute Error — interpretable en USD |
| MAPE    | Mean Absolute Percentage Error — error relativo |
| R²      | Coeficiente de determinación — varianza explicada |

## Decisiones clave de diseño
- `distrito_oficial` se usa en lugar del distrito declarado por el portal (puede ser fraudulento)
- NaN en amenities binarias de Properati ≠ 0; se trata como "no informado"
- NaN en `cocheras` ≠ 0 cocheras (distinción semántica importante)
- Imputación de `antiguedad_anios` por mediana agrupada por distrito y tipo de propiedad

---

## v2 — features socioeconómicas + fix imbalance (mayo 2026)

Branch: `feat/v2-imbalance-and-nse-fix`. Detalle completo en [`CHANGELOG_v2.md`](CHANGELOG_v2.md).

**Notebooks 06-10** (nuevos, no tocan los originales):
- `06_diagnostico_v2.ipynb` — cuantifica el bias por desbalance + 5 casos de stress
- `07_features_geo_v2.ipynb` — agrega 29 features: NSE, POIs OSM, denuncias por tipo, comisarías
- `08_pipeline_v2.ipynb` — split estratificado, target encoding smoothed, outlier caps activados, sample weights
- `09_entrenamiento_v2.ipynb` — re-entrenamiento + Optuna; XGBoost gana (R² 0.86, MAPE 15.74 %, MAE $158)
- `10_comparativa_v1_v2.ipynb` — métricas before/after por distrito + casos resueltos

**Artefactos v2** en `models/v2/` (5 modelos + scaler + encoder + caps + feature_names).
**Fuentes externas reales** en `data/external/`: CENACOM (INEI), MININTER denuncias, OSM Overpass, INEI Lib1744 PDF.

**Bugs auditados cerrados:** matriz NB05 invertida, mismatch 74-vs-77 features, outlier_caps huérfano, features_log con feature fantasma.

**Resultados:**
- MAPE 15.92 % → 15.74 % · MAE $173 → $158 · R² 0.785 → 0.861 · RMSE $378 → $284 (−25 %)
- 14 distritos mejoran, 3 empeoran (La Molina sobrepredice ahora — limitación de DATOS, no del modelo)
- UX del frontend muestra banner honesto cuando `n_comparables < 20`

**Limitación honesta:** zonas premium con N=0 comparables (La Planicie, Casuarinas) no se resuelven sin más datos. El compromiso del PR fue **cero data sintética**.
