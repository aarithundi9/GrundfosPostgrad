# Pod 1: Models (expands Lucent's Week 2 plan)

| Part | Plan |
|---|---|
| Input | `features_hourly` (Daksh): weather, calendar, `profile_type`, target `heat_intensity`, lags |
| Steps | 1. **Model A** (profiles): one LightGBM over all profile types; features = weather + calendar + `profile_type` (categorical); target = heat intensity (kWh per sqft or per unit). No demand lags. 2. **Model B** (short-term forecaster): Model A features + `demand_lag_24h`, `demand_lag_168h`. 3. Tune both with `forecasting.splits.month_folds` (leave-one-month-out inside Jan–Sep, 168 h gap). Small grid: num_leaves, learning_rate, min_data_in_leaf, n_estimators with early stopping. 4. Score on Oct–Dec **once** with `heatreuse.metrics.score`: MAE, CV(RMSE), NMBE, peak-hour error. Compare Model A to the degree-hour baseline and Model B to same-hour-last-week. 5. Feature importance / SHAP for the deck. 6. Stretch: LSTM (PyTorch), 168 h input window → next 24 h, same split, compared to Model B. |
| Output | `forecast_predictions` (all models), `model_scores`, and `hourly_shares` with source `model_a` via `shares.shares_from_predictions` (full-year predictions, train+test). Shares are value/annual sum, **not softmax**. |
| Tools | pandas, lightgbm (or xgboost), scikit-learn, shap, matplotlib; torch for the LSTM |
| Risks | Simulated data is smooth, so expect high accuracy: say this in the deck. Profile types built from few models (hospital, small schools) are flagged `low_model_count`. Only one year of data, so the test is Oct–Dec only. |
