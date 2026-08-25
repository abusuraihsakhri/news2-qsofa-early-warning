# NEWS2 + qSOFA Early Warning Score Calculator

Real clinical early warning scores for patient deterioration detection. Stdlib-only Python.

## Scores Implemented

### NEWS2 (National Early Warning Score 2)
Royal College of Physicians 2017. 7 parameters, score 0-20.

| Parameter | 3 | 2 | 1 | 0 | 1 | 2 | 3 |
|:----------|:--|:--|:--|:--|:--|:--|:--|
| RR (breaths/min) | ≤8 | | 9-11 | 12-20 | | 21-24 | ≥25 |
| SpO2 Scale 1 (%) | ≤91 | 92-93 | 94-95 | ≥96 | | | |
| SpO2 Scale 2 (%) | ≤83 | 84-85 | 86-87 | 88-92 (air) | 93-94 (O2) | 95-96 (O2) | ≥97 (O2) |
| Air or Oxygen | | O2:2 | | Air:0 | | | |
| Temperature (°C) | ≤35.0 | | 35.1-36.0 | 36.1-38.0 | 38.1-39.0 | ≥39.1 | |
| Systolic BP (mmHg) | ≤90 | 91-100 | 101-110 | 111-219 | | | ≥220 |
| Heart rate (bpm) | ≤40 | | 41-50 | 51-90 | 91-110 | 111-130 | ≥131 |
| Consciousness | | | | Alert | | | CVPU |

**Triggers:** 0 Low | 1-4 Low (routine) | 5-6 Medium (urgent review) | ≥7 High (emergency)

### qSOFA (Quick Sequential Organ Failure Assessment)
Singer et al., JAMA 2016. 3 items, score 0-3. ≥2 = high sepsis risk.

- RR ≥ 22: 1 point
- SBP ≤ 100 mmHg: 1 point
- Altered mentation (GCS < 15): 1 point

### SIRS (Systemic Inflammatory Response Syndrome)
Bone 1992. 4 items, score 0-4. ≥2 = SIRS positive.

## Quick Start

```bash
# Single patient assessment
python news2_qsofa.py single --rr 16 --spo2 98 --sbp 120 --hr 72 --temp 37.0 --avpu A

# COPD patient on O2 (Scale 2)
python news2_qsofa.py single --rr 18 --spo2 90 --spo2-scale 2 --o2 1 --sbp 130 --hr 80 --temp 37.0 --avpu A

# Batch CSV processing
python news2_qsofa.py batch --input patients.csv --output results.csv
```

## Python API

```python
from news2_qsofa import calculate_news2, calculate_qsofa, assess

# NEWS2
result = calculate_news2(rr=16, spo2=98, o2_support=False, sbp=120, hr=72, temp=37.0)
# {"news2_score": 0, "response": "Low (routine monitoring)", ...}

# qSOFA
result = calculate_qsofa(rr=24, sbp=95, gcs=13)
# {"qsofa_score": 3, "flags": ["RR>=22", "SBP<=100", "GCS<15/avpu!=A"]}

# Full assessment
result = assess("P001", rr=28, spo2=88, spo2_scale=1, supp_o2=1,
                sbp=85, hr=120, temp=39.5, avpu="V")
```

## Tests

```bash
python -m pytest test_news2_qsofa.py -v
```

## License

MIT
