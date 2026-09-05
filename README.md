# NEWS2 QSOFA Early Warning

> **Domain:** Clinical Decision Support & Biomedical Computing
> **Reference Guidelines & Standards:** `Standard Clinical Formulations & ISO/IEC Quality Frameworks`

<div align="center">

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
![Python](https://img.shields.io/badge/Python-3.10%20%7C%203.11%20%7C%203.12-3776AB.svg?logo=python&logoColor=white)
![FastAPI](https://img.shields.io/badge/FastAPI-0.111-009688.svg?logo=fastapi&logoColor=white)
![Audit Trail](https://img.shields.io/badge/Audit-HMAC--SHA256_Tamper--Evident-brightgreen.svg)
![Zero-PHI Guard](https://img.shields.io/badge/Guard-Zero--PHI_Outbound-blue.svg)
![Docker](https://img.shields.io/badge/Docker-Ready-2496ED.svg?logo=docker&logoColor=white)

</div>

---

## What It Does

NEWS2 + qSOFA + SIRS Early Warning Calculator
==============================================

Computes three bedside deterioration scores from vitals:

- **NEWS2** (Royal College of Physicians 2017): 7 params, 0-20, with
  SpO2 scale 1 (most patients) and scale 2 (hypercapnic COPD on O2).
  Triggers: 0-4 low, 5-6 medium, >=7 high.

- **qSOFA** (Singer et al. JAMA 2016): 3 binary items, 0-3. >=2 = high sepsis risk.

- **SIRS** (Bone 1992): 4 binary items, 0-4. >=2 = SIRS positive.

Stdlib only. Single + batch CSV.

---

## Quickstart

### Installation

```bash
pip install fastapi uvicorn pydantic pytest
```

### Environment Variables

| Variable | Required | Description |
|:---------|:---------|:------------|
| `AUDIT_SECRET_KEY` | Yes (production) | Secret key for HMAC-SHA256 audit trail signing. |
| `AUDIT_ALLOW_DEV_FALLBACK` | No | Set to `1` to allow insecure dev fallback when key is missing. |
| `MODEL_PROVIDER` | No | LLM provider: `mock` (default), `ollama`, `claude`, `openai`. |

### CLI Usage

#### 1. Single Patient Evaluation
```bash
python cli.py single --rr 16 --spo2 98 --sbp 120 --hr 72 --temp 37.0
python cli.py single --rr 28 --spo2 88 --sbp 85 --hr 120 --temp 39.5 --avpu V --o2 1
```

#### 2. Batch CSV Processing
```bash
python cli.py batch --input sample_vitals.csv --output results.csv
```

#### 3. Enterprise Agent Commands
```bash
python cli.py audit --task-id TASK-001
python cli.py chat "Explain NEWS2 scoring"
python cli.py verify-audit
```

### REST API (FastAPI)

```bash
uvicorn agents.api:app --host 0.0.0.0 --port 8000
```

Endpoints:
- `GET /health` - Health check
- `GET /metrics` - Prometheus metrics
- `POST /api/audit` - Dispatch task to agent workers
- `POST /api/chat` - Supervisory chat assistant
- `GET /api/audit/logs` - Retrieve and verify audit trail

---

## Testing

```bash
pytest -v
```

---

## Project Structure

```
news2-qsofa-early-warning/
├── news2_qsofa.py       # Core scoring engine + CLI
├── cli.py               # CLI entry point
├── enrichment.py        # Extended clinical feature engines
├── simulator.py         # High-throughput simulation
├── agents/
│   ├── __init__.py      # Package init
│   ├── base.py          # PHI guard, HMAC audit trail, security
│   ├── models.py        # Pydantic schemas
│   ├── supervisor.py    # Multi-agent orchestrator
│   ├── workers.py       # Specialized worker agents
│   ├── llm_factory.py   # LLM provider factory
│   ├── api.py           # FastAPI REST server
│   ├── metrics.py       # Prometheus metrics
│   ├── learning.py      # Bayesian calibration engine
│   └── streamer.py      # WebSocket telemetry
├── tests/               # Test suite
├── web/                 # Operations console (HTML)
├── conftest.py          # Pytest configuration
├── Dockerfile           # Container build
├── docker-compose.yml   # Container orchestration
└── .github/workflows/   # CI/CD
```

---

## Security

- **Zero-PHI Outbound Interceptor:** AST and regex inspection blocking SSNs, MRNs, phone numbers, and patient identifiers.
- **Tamper-Evident HMAC-SHA256 Audit Trail:** Chained, cryptographically signed logs for every evaluation.
- **Configurable Audit Key:** `AUDIT_SECRET_KEY` env var required in production; no hardcoded defaults.

---

## Container Deployment

```bash
docker build -t news2-qsofa-early-warning .
docker run -p 8000:8000 -e AUDIT_SECRET_KEY=your-secret-key news2-qsofa-early-warning
```

Or with docker-compose:

```bash
docker-compose up
```
