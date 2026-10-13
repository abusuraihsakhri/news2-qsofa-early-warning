# NEWS2, qSOFA and SIRS Early Warning

A deterministic bedside score calculator for research, education, and clinical decision support. Supports a static browser application, a dependency-free Python scoring engine, CSV batch processing, and an optional FastAPI service.

## Scoring

- **NEWS2 (0–20):** RCP 2017 respiratory rate, SpO₂, supplemental oxygen, systolic blood pressure, heart rate, temperature and ACVPU. Scores 5–6 prompt urgent review; ≥7 require emergency assessment. **Any single component score of 3 requires escalation even when the total is below 5.**
- **SpO₂ Scale 2:** Use only when a qualified clinician has prescribed an SpO₂ target of **88–92%**, typically for confirmed hypercapnic respiratory failure. On room air, saturations ≥93% score **0** on Scale 2; elevated saturations score only while receiving supplemental oxygen.
- **qSOFA (0–3):** respiratory rate ≥22/min, systolic pressure ≤100 mmHg and altered mental status (AVPU surrogate; GCS <15 when supplied via the Python convenience function). It is **not** a stand-alone sepsis diagnostic or screening rule.
- **SIRS (0–4):** temperature, heart rate, respiratory rate, and white-cell count. When WCC is omitted, only a **partial 3-component score** is reported.

The calculator validates ranges, completeness, and numerical finiteness. Results must be interpreted against the **[Royal College of Physicians NEWS2 guidance](https://www.rcp.ac.uk/resources/national-early-warning-score-news-2/)** and local escalation protocols. The SIRS and qSOFA implementations use their conventional thresholds.

**Clinical limitation:** This software has not undergone prospective clinical validation as a medical device. Do not substitute its output for examination, assessment, or locally mandated care pathways.

## Browser application

The static app is in [web/](web/) and has no runtime dependencies, login, API calls, external fonts, or browser storage. Enter a single observation set, or import a CSV for local batch processing and download the scored results. No observations are sent to a server by the browser application.

For local use, open \`web/index.html\` directly in a modern browser, or serve the repository using:

\`\`\`bash
python -m http.server 8000
\`\`\`

Then visit \`http://localhost:8000/web/\`. GitHub Pages builds are configured through \`.github/workflows/pages.yml\` on pushes to \`master\`.

CSV requires the columns \`rr,spo2,systolic_bp,heart_rate,temperature,avpu\` (or \`consciousness\` instead of \`avpu\`). Optional columns are \`patient_id,spo2_scale,supplemental_o2,wcc\`. For example, see [sample_vitals.csv](sample_vitals.csv). Avoid identifiable data in demonstration environments, and protect downloaded CSV files.

## Python CLI

The core calculation requires Python **3.10+** and the standard library only.

\`\`\`bash
python cli.py single --rr 16 --spo2 98 --sbp 120 --hr 72 --temp 37.0 --avpu A
python cli.py single --rr 28 --spo2 88 --sbp 85 --hr 120 --temp 39.5 --avpu V --o2 1
python cli.py batch --input sample_vitals.csv --output results.csv
\`\`\`

Missing or invalid observations raise an error; CSV batch processing reports the offending input row. Blank WCC is accepted but explicitly marks SIRS incomplete.

## Optional API and demonstration agent modules

Install the server and test dependencies:

\`\`\`bash
python -m pip install fastapi uvicorn pydantic pytest
uvicorn agents.api:app --host 127.0.0.1 --port 8000
\`\`\`

Available API routes:

| Method | Route | Function |
| --- | --- | --- |
| POST | \`/api/score\` | Validated scoring from vital signs; no patient identifier accepted |
| GET | \`/health\` | Service health response |
| GET | \`/metrics\` | JSON service counters |
| POST | \`/api/audit\` | Demonstration agent task processing |
| POST | \`/api/chat\` | Deterministic mock response (not clinical advice) |
| GET | \`/api/audit/logs\` | In-memory signed audit-chain entries |

Example:

\`\`\`bash
curl -s http://127.0.0.1:8000/api/score \
  -H 'Content-Type: application/json' \
  -d '{"rr":16,"spo2":98,"systolic_bp":120,"heart_rate":72,"temperature":37,"avpu":"A"}'
\`\`\`

The optional agent endpoints are development demonstrations, **not authenticated production clinical services**. PHI detection is pattern-based and cannot guarantee de-identification. Do not expose the API publicly without independently implementing transport security, authentication, authorization, access logging and clinical governance.

## Container

Configure a unique key outside source control; no production signing key is included:

\`\`\`bash
export AUDIT_SECRET_KEY="$(python -c 'import secrets; print(secrets.token_hex(32))')"
docker compose up --build
\`\`\`

Compose binds to \`127.0.0.1:8000\` by default. \`AUDIT_SECRET_KEY\` signs the in-memory HMAC-SHA256 chain; it is not a replacement for encryption or access control. The Python core and browser calculator do not need this key.

## Tests and implementation

\`\`\`bash
python -m pip install pytest fastapi uvicorn pydantic
python -m pytest -v
node --test web/scoring.test.cjs
node --check web/scoring.js
\`\`\`

The Python engine and JavaScript browser engine use the same documented scoring thresholds, with regression tests for clinical boundaries, validation, CSV import/export, and signing integrity. The static client uses ordinary JavaScript, **not** Pyodide; no browser Python runtime or server is required.

Works with current Chromium, Firefox and Safari versions supporting modern JavaScript and the File API. MIT licensed; see [LICENSE](LICENSE).
