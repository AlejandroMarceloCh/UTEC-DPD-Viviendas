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
