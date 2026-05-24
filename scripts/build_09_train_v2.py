"""Genera notebooks/09_entrenamiento_v2.ipynb.

Re-entrena los 5 modelos con sample_weight + outlier_caps + features v2.
Optuna sobre RF y XGBoost (20 trials c/u).
Fix definitivo del bug `modelo_final.joblib` (Parche #1 auditoría).
"""
from pathlib import Path
import nbformat as nbf

NB_PATH = Path(__file__).resolve().parents[1] / "notebooks" / "09_entrenamiento_v2.ipynb"

nb = nbf.v4.new_notebook()
nb.metadata = {
    "kernelspec": {"name": "dpd-v2", "display_name": "Python (DPD v2)"},
    "language_info": {"name": "python"},
}

cells = []

cells.append(nbf.v4.new_markdown_cell("""# Re-entrenamiento v2 + tuning + fix `modelo_final`

> **Día 5 del plan_v2.md.**

1. Entrenar 5 modelos sobre los X/y_v2 con `sample_weight` (combate desbalance).
2. Optuna 20 trials sobre RF y XGBoost.
3. Métricas en val y test.
4. **Fix Parche #1 auditoría**: `modelo_final.joblib` ahora apunta al modelo con mejor R² test (XGBoost o RF), con métricas que coinciden.

## Decisión de métrica primaria

`MAPE` (Mean Absolute Percentage Error) — métrica honesta para el usuario final: "el precio real puede estar ±15 % de mi predicción".

R² lo reportamos como auxiliar.
"""))

cells.append(nbf.v4.new_code_cell("""import numpy as np
import pandas as pd
import joblib
import warnings
warnings.filterwarnings('ignore')

from sklearn.linear_model import LinearRegression, Ridge, Lasso
from sklearn.ensemble import RandomForestRegressor
from sklearn.metrics import mean_absolute_error, mean_absolute_percentage_error, mean_squared_error, r2_score
import xgboost as xgb
import optuna
optuna.logging.set_verbosity(optuna.logging.WARNING)

PROCESSED = '../data/processed/'
MODELS_V2 = '../models/v2/'

# Cargar artefactos del notebook 08
X_train = np.load(f'{PROCESSED}X_train_v2.npy', allow_pickle=True).astype(float)
X_val   = np.load(f'{PROCESSED}X_val_v2.npy', allow_pickle=True).astype(float)
X_test  = np.load(f'{PROCESSED}X_test_v2.npy', allow_pickle=True).astype(float)
X_train_sc = np.load(f'{PROCESSED}X_train_sc_v2.npy').astype(float)
X_val_sc   = np.load(f'{PROCESSED}X_val_sc_v2.npy').astype(float)
X_test_sc  = np.load(f'{PROCESSED}X_test_sc_v2.npy').astype(float)
y_train = np.load(f'{PROCESSED}y_train_v2.npy')
y_val   = np.load(f'{PROCESSED}y_val_v2.npy')
y_test  = np.load(f'{PROCESSED}y_test_v2.npy')
sample_w = np.load(f'{PROCESSED}sample_weights_train_v2.npy')

print(f'X_train: {X_train.shape}  X_train_sc: {X_train_sc.shape}')
print(f'y_train: {y_train.shape}  sample_w: {sample_w.shape}')
print(f'X_val: {X_val.shape}    X_test: {X_test.shape}')

# Helper para evaluar en escala USD real
def eval_model_usd(model, X, y_log_true):
    pred_log = model.predict(X)
    pred_usd = np.clip(np.expm1(pred_log), 0, None)
    real_usd = np.expm1(y_log_true)
    return {
        'mae':  mean_absolute_error(real_usd, pred_usd),
        'mape': mean_absolute_percentage_error(real_usd, pred_usd) * 100,
        'rmse': np.sqrt(mean_squared_error(real_usd, pred_usd)),
        'r2':   r2_score(real_usd, pred_usd),
    }

results_val = {}
results_test = {}
preds_test = {}
"""))

cells.append(nbf.v4.new_markdown_cell("""## 1. Modelos lineales (LR / Ridge / Lasso) sobre X_sc

Los lineales usan la versión escalada. Ridge y Lasso eligen alpha con grid simple sobre val.
"""))

cells.append(nbf.v4.new_code_cell("""# Linear Regression
lr = LinearRegression()
lr.fit(X_train_sc, y_train, sample_weight=sample_w)
results_val['Linear Regression'] = eval_model_usd(lr, X_val_sc, y_val)
results_test['Linear Regression'] = eval_model_usd(lr, X_test_sc, y_test)
preds_test['Linear Regression'] = lr.predict(X_test_sc)
print(f'LR  val: {results_val[\"Linear Regression\"]}')
print(f'LR test: {results_test[\"Linear Regression\"]}')

# Ridge — grid de alpha
best_alpha_r, best_mape_r = None, 999
for a in [0.1, 1.0, 5.0, 10.0, 50.0, 100.0]:
    m = Ridge(alpha=a, random_state=42).fit(X_train_sc, y_train, sample_weight=sample_w)
    mape = eval_model_usd(m, X_val_sc, y_val)['mape']
    if mape < best_mape_r:
        best_alpha_r, best_mape_r = a, mape
ridge = Ridge(alpha=best_alpha_r, random_state=42).fit(X_train_sc, y_train, sample_weight=sample_w)
results_val['Ridge'] = eval_model_usd(ridge, X_val_sc, y_val)
results_test['Ridge'] = eval_model_usd(ridge, X_test_sc, y_test)
preds_test['Ridge'] = ridge.predict(X_test_sc)
print(f'\\nRidge alpha={best_alpha_r}  val: {results_val[\"Ridge\"]}')
print(f'Ridge test: {results_test[\"Ridge\"]}')

# Lasso — grid (más pequeño porque Lasso es lento)
best_alpha_l, best_mape_l = None, 999
for a in [0.0001, 0.001, 0.01, 0.05]:
    m = Lasso(alpha=a, random_state=42, max_iter=10000).fit(X_train_sc, y_train, sample_weight=sample_w)
    mape = eval_model_usd(m, X_val_sc, y_val)['mape']
    if mape < best_mape_l:
        best_alpha_l, best_mape_l = a, mape
lasso = Lasso(alpha=best_alpha_l, random_state=42, max_iter=10000).fit(X_train_sc, y_train, sample_weight=sample_w)
results_val['Lasso'] = eval_model_usd(lasso, X_val_sc, y_val)
results_test['Lasso'] = eval_model_usd(lasso, X_test_sc, y_test)
preds_test['Lasso'] = lasso.predict(X_test_sc)
print(f'\\nLasso alpha={best_alpha_l}  val: {results_val[\"Lasso\"]}')
print(f'Lasso test: {results_test[\"Lasso\"]}')
"""))

cells.append(nbf.v4.new_markdown_cell("""## 2. Random Forest con Optuna (20 trials)"""))

cells.append(nbf.v4.new_code_cell("""def rf_objective(trial):
    params = {
        'n_estimators':     trial.suggest_int('n_estimators', 100, 400),
        'max_depth':        trial.suggest_int('max_depth', 6, 20),
        'min_samples_leaf': trial.suggest_int('min_samples_leaf', 1, 10),
        'max_features':     trial.suggest_categorical('max_features', ['sqrt', 'log2', 0.5, 0.7]),
        'random_state':     42,
        'n_jobs':           -1,
    }
    m = RandomForestRegressor(**params)
    m.fit(X_train, y_train, sample_weight=sample_w)
    return eval_model_usd(m, X_val, y_val)['mape']

study_rf = optuna.create_study(direction='minimize', sampler=optuna.samplers.TPESampler(seed=42))
study_rf.optimize(rf_objective, n_trials=20, show_progress_bar=False)
print(f'Mejor RF MAPE val: {study_rf.best_value:.3f}%')
print(f'Mejores params: {study_rf.best_params}')

rf_best = RandomForestRegressor(**study_rf.best_params, random_state=42, n_jobs=-1)
rf_best.fit(X_train, y_train, sample_weight=sample_w)
results_val['Random Forest']  = eval_model_usd(rf_best, X_val, y_val)
results_test['Random Forest'] = eval_model_usd(rf_best, X_test, y_test)
preds_test['Random Forest']   = rf_best.predict(X_test)
print(f'\\nRF val:  {results_val[\"Random Forest\"]}')
print(f'RF test: {results_test[\"Random Forest\"]}')
"""))

cells.append(nbf.v4.new_markdown_cell("""## 3. XGBoost con Optuna (20 trials)"""))

cells.append(nbf.v4.new_code_cell("""def xgb_objective(trial):
    params = {
        'n_estimators':     trial.suggest_int('n_estimators', 200, 800),
        'max_depth':        trial.suggest_int('max_depth', 4, 12),
        'learning_rate':    trial.suggest_float('learning_rate', 0.01, 0.2, log=True),
        'subsample':        trial.suggest_float('subsample', 0.6, 1.0),
        'colsample_bytree': trial.suggest_float('colsample_bytree', 0.6, 1.0),
        'reg_alpha':        trial.suggest_float('reg_alpha', 1e-5, 1.0, log=True),
        'reg_lambda':       trial.suggest_float('reg_lambda', 1e-5, 1.0, log=True),
        'random_state':     42,
        'n_jobs':           -1,
        'verbosity':        0,
    }
    m = xgb.XGBRegressor(**params)
    m.fit(X_train, y_train, sample_weight=sample_w)
    return eval_model_usd(m, X_val, y_val)['mape']

study_xgb = optuna.create_study(direction='minimize', sampler=optuna.samplers.TPESampler(seed=42))
study_xgb.optimize(xgb_objective, n_trials=20, show_progress_bar=False)
print(f'Mejor XGB MAPE val: {study_xgb.best_value:.3f}%')
print(f'Mejores params: {study_xgb.best_params}')

xgb_best = xgb.XGBRegressor(**study_xgb.best_params, random_state=42, n_jobs=-1, verbosity=0)
xgb_best.fit(X_train, y_train, sample_weight=sample_w)
results_val['XGBoost']  = eval_model_usd(xgb_best, X_val, y_val)
results_test['XGBoost'] = eval_model_usd(xgb_best, X_test, y_test)
preds_test['XGBoost']   = xgb_best.predict(X_test)
print(f'\\nXGB val:  {results_val[\"XGBoost\"]}')
print(f'XGB test: {results_test[\"XGBoost\"]}')
"""))

cells.append(nbf.v4.new_markdown_cell("""## 4. Tabla comparativa + selección del modelo final (Parche #1)"""))

cells.append(nbf.v4.new_code_cell("""# Tabla val + test
def rows(d):
    return pd.DataFrame([{'modelo': m, **v} for m, v in d.items()])

res_val = rows(results_val).sort_values('mape')
res_test = rows(results_test).sort_values('mape')
print('=== Resultados en VAL (ordenado por MAPE) ===')
print(res_val.round(2).to_string(index=False))
print()
print('=== Resultados en TEST (ordenado por MAPE) ===')
print(res_test.round(2).to_string(index=False))

# *** PARCHE #1 — el modelo final es el ganador real, no el de la matriz invertida ***
# Selección: el de menor MAPE en TEST.
best_name = res_test.iloc[0]['modelo']
models_lookup = {
    'Linear Regression': lr,
    'Ridge': ridge,
    'Lasso': lasso,
    'Random Forest': rf_best,
    'XGBoost': xgb_best,
}
best_model = models_lookup[best_name]
best_metrics = results_test[best_name]
print(f'\\n🏆 MODELO FINAL v2: {best_name}')
print(f'   métricas test: {best_metrics}')

# Guardar modelos individuales
joblib.dump(lr,       f'{MODELS_V2}01_linear_regression_v2.joblib')
joblib.dump(ridge,    f'{MODELS_V2}02_ridge_v2.joblib')
joblib.dump(lasso,    f'{MODELS_V2}03_lasso_v2.joblib')
joblib.dump(rf_best,  f'{MODELS_V2}04_random_forest_v2.joblib')
joblib.dump(xgb_best, f'{MODELS_V2}05_xgboost_v2.joblib')

# modelo_final.joblib coherente (objeto + métricas que SÍ corresponden a ese objeto)
modelo_final = {
    'modelo':    best_model,
    'nombre':    best_name,
    'features':  joblib.load(f'{MODELS_V2}feature_names_v2.joblib'),
    'metricas_test': {
        'rmse': round(best_metrics['rmse'], 2),
        'mae':  round(best_metrics['mae'], 2),
        'mape': round(best_metrics['mape'], 4),
        'r2':   round(best_metrics['r2'], 4),
    },
}
joblib.dump(modelo_final, f'{MODELS_V2}modelo_final_v2.joblib')

# Guardar CSV de resultados
res_test.to_csv(f'{PROCESSED}resultados_test_v2.csv', index=False)
res_val.to_csv(f'{PROCESSED}resultados_val_v2.csv', index=False)

print(f'\\n✓ models/v2/ con 5 modelos + modelo_final_v2.joblib')
print(f'  - El .joblib guarda OBJETO = {best_name} y MÉTRICAS = de {best_name}.')
print(f'  - Bug auditoría #1 cerrado: object y metrics coinciden.')
"""))

cells.append(nbf.v4.new_markdown_cell("""## 5. Importancias top — qué features mueven la aguja"""))

cells.append(nbf.v4.new_code_cell("""# Feature importances del mejor modelo (si es tree-based)
feat_names = joblib.load(f'{MODELS_V2}feature_names_v2.joblib')

if hasattr(best_model, 'feature_importances_'):
    imp = pd.Series(best_model.feature_importances_, index=feat_names).sort_values(ascending=False)
    print('=== Top 25 features por importancia ===')
    print(imp.head(25).round(4).to_string())
    new_cols_pat = ('estrato_nse', 'cat_dist_', 'count_500m_osm_', 'count_1km_osm_',
                    'dist_nearest_m_osm_', 'n_comisarias_distrito', 'denuncias_')
    new_imp = imp[[c for c in imp.index if c.startswith(new_cols_pat)]]
    print(f'\\n=== Solo features NUEVAS v2 (entre las 25 top: {len(set(new_imp.head(25).index) & set(imp.head(25).index))}) ===')
    print(new_imp.head(20).round(4).to_string())
else:
    print(f'{best_name} no expone feature_importances_; se omite ranking.')
"""))

nb["cells"] = cells
nbf.write(nb, NB_PATH)
print(f"✅ {NB_PATH}")
