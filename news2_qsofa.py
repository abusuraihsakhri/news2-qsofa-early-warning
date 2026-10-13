#!/usr/bin/env python3
"""
NEWS2 + qSOFA + SIRS Early Warning Calculator
==============================================

Computes three bedside deterioration scores from vitals:

- NEWS2 (Royal College of Physicians 2017): 7 params, 0-20, with
  SpO2 scale 1 (most patients) and scale 2 (hypercapnic COPD on O2).
  Triggers: 0-4 low, 5-6 medium, >=7 high.

- qSOFA (Singer et al. JAMA 2016): 3 binary items, 0-3. >=2 = high sepsis risk.

- SIRS (Bone 1992): 4 binary items, 0-4. >=2 = SIRS positive.

Stdlib only. Single + batch CSV.
"""
from __future__ import annotations
import argparse, csv, math, sys
from dataclasses import dataclass
from typing import Optional

# ---------------------------------------------------------------------------
# NEWS2 scoring tables
# ---------------------------------------------------------------------------
def score_rr(rr: float) -> int:
    if rr <= 8: return 3
    if 9 <= rr <= 11: return 1
    if 12 <= rr <= 20: return 0
    if 21 <= rr <= 24: return 2
    return 3  # >=25

def score_spo2_scale1(spo2: float) -> int:
    if spo2 <= 91: return 3
    if 92 <= spo2 <= 93: return 2
    if 94 <= spo2 <= 95: return 1
    return 0  # >=96

def score_spo2_scale2(spo2: float, supplemental_o2: bool = True) -> int:
    """RCP NEWS2 scale 2; high saturation only scores on supplemental O2.

    Scale 2 is ONLY for a clinician-prescribed 88–92% target (confirmed
    hypercapnic respiratory failure), not for COPD by diagnosis alone.
    """
    if spo2 <= 83: return 3
    if spo2 <= 85: return 2
    if spo2 <= 87: return 1
    if not supplemental_o2 or spo2 <= 92: return 0
    if spo2 <= 94: return 1
    if spo2 <= 96: return 2
    return 3

def score_sbp(sbp: float) -> int:
    if sbp <= 90: return 3
    if 91 <= sbp <= 100: return 2
    if 101 <= sbp <= 110: return 1
    if 111 <= sbp <= 219: return 0
    return 3  # >=220

def score_hr(hr: float) -> int:
    if hr <= 40: return 3
    if 41 <= hr <= 50: return 1
    if 51 <= hr <= 90: return 0
    if 91 <= hr <= 110: return 1
    if 111 <= hr <= 130: return 2
    return 3  # >=131

def score_temp(t: float) -> int:
    if t <= 35.0: return 3
    if 35.1 <= t <= 36.0: return 1
    if 36.1 <= t <= 38.0: return 0
    if 38.1 <= t <= 39.0: return 1
    return 2  # >=39.1

def score_consciousness(avpu: str) -> int:
    return 0 if avpu.upper() == "A" else 3  # V/P/U = 3

def news2_response(score: int, red: bool = False) -> str:
    if score <= 4:
        return ("Low–medium (single red parameter: urgent clinical review)"
                if red else "Low (routine monitoring)")
    if score <= 6: return "Medium (urgent review)"
    return "High (emergency assessment)"

# qSOFA / SIRS helpers
def qsofa_score(rr: float, sbp: float, avpu: str) -> tuple[int, list[str]]:
    flags = []
    if rr >= 22: flags.append("RR>=22")
    if sbp <= 100: flags.append("SBP<=100")
    if avpu.upper() != "A": flags.append("GCS<15/avpu!=A")
    return len(flags), flags

def sirs_score(temp: float, hr: float, rr: float, wcc: Optional[float] = None) -> tuple[int, list[str]]:
    flags = []
    if temp < 36.0 or temp > 38.0: flags.append("Temp<36 or >38")
    if hr > 90: flags.append("HR>90")
    if rr > 20: flags.append("RR>20")
    if wcc is not None and (wcc < 4.0 or wcc > 12.0): flags.append("WCC<4 or >12")
    return len(flags), flags

@dataclass
class WarningResult:
    patient_id: str
    news2: int
    news2_response: str
    news2_detail: dict
    qsofa: int
    qsofa_flags: list[str]
    sirs: int
    sirs_flags: list[str]
    warnings: list[str]

def _measure(name: str, value, minimum: float, maximum: float, *, integer: bool = False) -> float:
    if value is None or isinstance(value, str) and not value.strip():
        raise ValueError(f"{name} is required")
    try:
        number = float(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{name} must be numeric") from exc
    if not math.isfinite(number) or not minimum <= number <= maximum:
        raise ValueError(f"{name} must be finite and between {minimum:g} and {maximum:g}")
    if integer and not number.is_integer():
        raise ValueError(f"{name} must be a whole number")
    return number


def assess(patient_id: str, rr, spo2, spo2_scale, supp_o2, sbp, hr, temp, avpu, wcc=None) -> WarningResult:
    """Score validated observations. No implicit substitution for missing vitals."""
    rr = _measure("rr", rr, 1, 100, integer=True)
    spo2 = _measure("spo2", spo2, 0, 100, integer=True)
    sbp = _measure("systolic_bp", sbp, 1, 400, integer=True)
    hr = _measure("heart_rate", hr, 1, 300, integer=True)
    temp = _measure("temperature", temp, 25, 45)
    if round(temp, 1) != temp:
        raise ValueError("temperature must be recorded to one decimal place")
    scale = _measure("spo2_scale", spo2_scale, 1, 2, integer=True)
    oxygen = _measure("supplemental_o2", supp_o2, 0, 1, integer=True)
    if avpu is None or str(avpu).strip().upper() not in {"A", "C", "V", "P", "U"}:
        raise ValueError("avpu must be A, C (new confusion), V, P or U")
    avpu = str(avpu).strip().upper()
    if wcc is not None and str(wcc).strip():
        wcc = _measure("wcc", wcc, 0, 1000)
    else:
        wcc = None

    s_rr, s_hr = score_rr(rr), score_hr(hr)
    s_sbp, s_temp = score_sbp(sbp), score_temp(temp)
    s_avpu, s_o2 = score_consciousness(avpu), 2 if oxygen else 0
    s_spo2 = (score_spo2_scale2(spo2, bool(oxygen)) if scale == 2
              else score_spo2_scale1(spo2))
    detail = {"RR": s_rr, "SpO2": s_spo2, "O2": s_o2, "SBP": s_sbp,
              "HR": s_hr, "Temp": s_temp, "AVPU": s_avpu}
    red = any(value == 3 for value in detail.values())
    total = sum(detail.values())
    warns: list[str] = []
    if scale == 2:
        warns.append("Scale 2 requires a clinician-prescribed SpO2 target of 88–92%")
    if red:
        warns.append("Red score (3 in one parameter) -> urgent review even if NEWS2 <5 per RCP")
    if wcc is None:
        warns.append("SIRS is partial: white blood cell count (WCC) not provided")
    q, qf = qsofa_score(rr, sbp, avpu)
    s, sf = sirs_score(temp, hr, rr, wcc)
    return WarningResult(str(patient_id), total, news2_response(total, red), detail, q, qf, s, sf, warns)

def calculate_news2(rr: float, spo2: float, o2_support: bool = False, sbp: float = 120, hr: float = 70, consciousness: str = "A", temp: float = 37.0, spo2_scale: int = 1) -> dict:
    res = assess("patient", rr=rr, spo2=spo2, spo2_scale=spo2_scale, supp_o2=1 if o2_support else 0, sbp=sbp, hr=hr, temp=temp, avpu=consciousness)
    return {"news2_score": res.news2, "response": res.news2_response, "detail": res.news2_detail, "warnings": res.warnings}

def calculate_qsofa(rr: float, sbp: float, gcs: Optional[int] = None, avpu: Optional[str] = None) -> dict:
    rr = _measure("rr", rr, 1, 100, integer=True)
    sbp = _measure("systolic_bp", sbp, 1, 400, integer=True)
    if gcs is not None:
        gcs = _measure("gcs", gcs, 3, 15, integer=True)
    if avpu is None:
        avpu = "A" if (gcs is None or gcs == 15) else "V"
    if str(avpu).upper() not in {"A", "C", "V", "P", "U"}:
        raise ValueError("avpu must be A, C, V, P or U")
    score, flags = qsofa_score(rr=rr, sbp=sbp, avpu=avpu)
    return {"qsofa_score": score, "flags": flags}

# ---------------------------------------------------------------------------
# CSV
# ---------------------------------------------------------------------------
def process_csv(inp: str, out: str):
    results = []
    with open(inp, newline="", encoding="utf-8-sig") as f:
        r = csv.DictReader(f)
        for row in r:
            pid = row.get("patient_id") or row.get("id") or "?"
            try:
                consciousness = row.get("avpu") or row.get("consciousness")
                res = assess(pid, row["rr"], row["spo2"], row.get("spo2_scale", 1),
                             row.get("supplemental_o2", 0), row["systolic_bp"],
                             row["heart_rate"], row["temperature"], consciousness, row.get("wcc"))
            except (KeyError, TypeError, ValueError) as exc:
                raise ValueError(f"Invalid CSV row {r.line_num}: {exc}") from exc
            results.append(res)
    with open(out, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=["patient_id","news2","news2_response","news2_detail","qsofa","qsofa_flags","sirs","sirs_flags","warnings"])
        w.writeheader()
        for res in results:
            w.writerow({"patient_id":res.patient_id,"news2":res.news2,"news2_response":res.news2_response,
                        "news2_detail":res.news2_detail,"qsofa":res.qsofa,"qsofa_flags":";".join(res.qsofa_flags),
                        "sirs":res.sirs,"sirs_flags":";".join(res.sirs_flags),"warnings":"|".join(res.warnings)})
    return results

def build_parser():
    p = argparse.ArgumentParser(prog="news2_qsofa", description="NEWS2 + qSOFA + SIRS from vitals (RCP 2017, JAMA 2016).")
    sub = p.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("single")
    s.add_argument("--id", dest="patient_id", default="patient")
    s.add_argument("--rr", required=True, type=float); s.add_argument("--spo2", required=True, type=float)
    s.add_argument("--spo2-scale", type=int, default=1, choices=[1,2]); s.add_argument("--o2", type=int, default=0, choices=[0,1])
    s.add_argument("--sbp", required=True, type=float); s.add_argument("--hr", required=True, type=float)
    s.add_argument("--temp", required=True, type=float); s.add_argument("--avpu", default="A", choices=["A","C","V","P","U","a","c","v","p","u"])
    s.add_argument("--wcc", type=float, default=None)
    b = sub.add_parser("batch"); b.add_argument("--input", required=True); b.add_argument("--output", required=True)
    # Enterprise agent subcommands
    a = sub.add_parser("audit")
    a.add_argument("--task-id", default="CLI-AUDIT-01")
    c = sub.add_parser("chat")
    c.add_argument("query", nargs="+")
    sub.add_parser("verify-audit")
    return p

def main(argv=None):
    p = build_parser(); a = p.parse_args(argv)
    if a.cmd == "single":
        res = assess(a.patient_id, a.rr, a.spo2, a.spo2_scale, a.o2, a.sbp, a.hr, a.temp, a.avpu, a.wcc)
        print(f"Patient {res.patient_id}: NEWS2={res.news2} ({res.news2_response})  detail={res.news2_detail}")
        print(f"  qSOFA={res.qsofa} {'('+';'.join(res.qsofa_flags)+')' if res.qsofa_flags else ''}  SIRS={res.sirs} {'('+';'.join(res.sirs_flags)+')' if res.sirs_flags else ''}")
        if res.warnings: print("  Warnings: " + " | ".join(res.warnings))
        return 0
    if a.cmd == "batch":
        results = process_csv(a.input, a.output)
        mean = f"{sum(r.news2 for r in results)/len(results):.1f}" if results else "N/A"
        print(f"Processed {len(results)} -> {a.output}  mean NEWS2={mean}")
        for r in results: print(f"  {r.patient_id}: NEWS2={r.news2} qSOFA={r.qsofa} SIRS={r.sirs}")
        return 0
    if a.cmd == "audit":
        from agents.supervisor import SystemSupervisor
        from agents.models import SystemTaskPayload
        supervisor = SystemSupervisor(model_provider="mock")
        payload = SystemTaskPayload(
            task_id=a.task_id,
            target_identifier="CLI-TARGET",
            primary_metric=12.0,
            secondary_metric=4.0,
            status_descriptor="NOMINAL"
        )
        dossier = supervisor.process_task(payload)
        print(f"Audit dossier: {dossier.dossier_id} urgency={dossier.overall_urgency.value}")
        return 0
    if a.cmd == "chat":
        from agents.supervisor import SystemSupervisor
        supervisor = SystemSupervisor(model_provider="mock")
        query = " ".join(a.query)
        response = supervisor.query_supervisory_chat(query)
        print(f"Response: {response}")
        return 0
    if a.cmd == "verify-audit":
        from agents.base import AuditLogger
        valid = AuditLogger.verify_integrity()
        print(f"Audit trail integrity: {'VALID' if valid else 'COMPROMISED'}")
        return 0
    p.print_help(); return 1

if __name__ == "__main__": sys.exit(main())
