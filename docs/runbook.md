# Operations Runbook

## 1. Service Overview
- **Backend**: FastAPI service (`backend/main.py`) orchestrating data ingestion, regime-aware prediction, and websocket broadcasting.
- **Data Lake**: Versioned Parquet layers at `data/{raw,bronze,silver}` produced via `backend/data_pipeline`.
- **Training Platform**: Walk-forward orchestrator (`backend/ml/training`) logging experiments under `data/experiments`.
- **Frontend**: Nuxt 3 interface (`frontend-nuxt/`) for charting, indicator presets, and websocket streaming.
- **Monitoring**: Prometheus metrics exposed at `/metrics` with new gauges for regime state and prediction quality.

## 2. On-Call Responsibilities
- Maintain API uptime and websocket availability ≥ 99.5%.
- Ensure predictions remain within SLA (≤ 150 ms P95). Monitor `prediction_latency_seconds` histogram.
- Track regime gauge (`market_regime_state`) and `prediction_quality_metric` for anomaly detection.

## 3. Standard Operating Procedures
### 3.1 Backend Restart
```bash
cd /Users/pits/Projects/new-bot-trading/backend
source venv/bin/activate
uvicorn main:app --host 0.0.0.0 --port 8182
```
- Confirm startup logs show scheduler and websocket tasks active.
- Hit `/health` and `/metrics` to validate subsystems.

### 3.2 Nuxt Frontend
```bash
cd /Users/pits/Projects/new-bot-trading/frontend-nuxt
npm install
npm run dev
```
- Configure `NUXT_PUBLIC_API_BASE` and `NUXT_PUBLIC_WS_BASE` for remote deployments.

### 3.3 Manual Prediction Trigger
```bash
curl -X POST http://localhost:8182/api/prediction/trigger \
  -H 'Content-Type: application/json' \
  -d '{"symbol": "TCS.NS", "timeframe": "5m", "horizon_minutes": 180}'
```
Check logs for gating decisions and probabilistic bands.

## 4. Incident Playbooks
| Incident | Detection | Mitigation |
| --- | --- | --- |
| **Data Feed Gap** | `market_regime_state` stuck on `unknown` + `/metrics` `cache_misses_total` spike | Run `python backend/utils/data_fetcher.py` diagnostic; failover to TwelveData by setting `PRIMARY_DATA_PROVIDER=twelvedata`. |
| **Prediction Drift** | `prediction_quality_metric{metric="mape"}` > 8% sustained | Trigger orchestrator retraining via `POST /api/prediction/train` with `bot_name="orchestrator"`; prune stale models using `/api/models/clear`. |
| **Websocket Flood** | `websocket_connections_total` spikes + UI lag | Scale backend workers, enable rate-limit via `settings.ws_heartbeat_interval`, recycle connections via `$socket.scheduleReconnect()`. |
| **Regime Misclassification** | Analysts disagree with automated regime | Validate data via `data/bronze/`; override weights through experiment registry by logging curated experiment with `families` tuned for desired bots. |

## 5. Validation & QA
- Run unit tests: `pytest backend/tests/test_data_pipeline.py backend/tests/test_training_orchestrator.py`.
- Smoke test drift monitor via `python -m backend.monitoring.drift_monitor` (add sample data).
- Validate Prometheus metrics: `curl http://localhost:8182/metrics | grep regime`.

## 6. Change Management
- Tag releases with semantic versioning (`vMAJOR.MINOR.PATCH`).
- Registry artifacts stored under `data/experiments`. Back up before pruning (`tar -czf experiments-$(date +%Y%m%d).tgz data/experiments`).
- Document any gating weight overrides in `docs/ml_audit.md` appendix.

## 7. Escalation
- Level 1: ML Ops engineer on-call
- Level 2: Core backend developer (predictive orchestrator)
- Level 3: Data engineering owner for pipeline integrity
- Provide Grafana dashboards pointing to `/metrics` (panel templates in `observability/dashboard.json` TBD).

## 8. Glossary
- **Regime**: High-level market state (trending_up/down, range_bound, volatile, neutral, unknown).
- **Champion/Challenger**: Best-performing model families logged by orchestrator; used to bias gating weights.
- **Silver Layer**: Feature-engineered dataset ready for training/inference.

Keep this runbook alongside infrastructure-as-code manifests so that updates sync with deployments.
