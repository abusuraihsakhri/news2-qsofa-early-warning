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
import argparse, csv, sys
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

def score_spo2_scale2(spo2: float) -> int:
    # RCP scale 2 for patients with hypercapnic respiratory failure (target 88-92)
    if spo2 <= 83: return 3
    if 84 <= spo2 <= 85: return 2
    if 86 <= spo2 <= 87: return 1
    if 88 <= spo2 <= 92: return 0
    if 93 <= spo2 <= 94: return 1  # on O2 only
    if 95 <= spo2 <= 96: return 2
    return 3  # >=97 on O2

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

def news2_response(score: int) -> str:
    if score <= 4: return "Low (routine monitoring)"
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

def assess(patient_id: str, rr, spo2, spo2_scale, supp_o2, sbp, hr, temp, avpu, wcc=None) -> WarningResult:
    warns: list[str] = []
    # coerce
    try:
        rr, spo2, sbp, hr, temp = float(rr), float(spo2), float(sbp), float(hr), float(temp)
        spo2_scale = int(spo2_scale) if spo2_scale not in (None,"") else 1
        supp_o2 = int(supp_o2) if supp_o2 not in (None,"") else 0
        avpu = str(avpu).strip().upper() or "A"
    except Exception as e:
        warns.append(str(e))
        raise

    # NEWS2 component scores
    s_rr = score_rr(rr)
    s_hr = score_hr(hr)
    s_sbp = score_sbp(sbp)
    s_temp = score_temp(temp)
    s_avpu = score_consciousness(avpu)
    s_o2 = 2 if supp_o2 == 1 else 0
    if spo2_scale == 2:
        s_spo2 = score_spo2_scale2(spo2)
        # Scale 2 scoring for 93-94 on O2 already gives 1 etc; if not on O2, clamp
        if supp_o2 == 0 and s_spo2 > 0 and spo2 >= 88:
            # RCP: scale 2 only applies when on O2; if breathing air, use scale 1
            s_spo2 = score_spo2_scale1(spo2)
            warns.append("SpO2 scale 2 without O2: fell back to scale 1 for SpO2")
    else:
        s_spo2 = score_spo2_scale1(spo2)

    news2 = s_rr + s_spo2 + s_o2 + s_sbp + s_hr + s_temp + s_avpu
    # RCP red score: any single 3 triggers medium at score 5 threshold, but we report raw
    detail = {"RR": s_rr, "SpO2": s_spo2, "O2": s_o2, "SBP": s_sbp, "HR": s_hr, "Temp": s_temp, "AVPU": s_avpu}
    if any(v == 3 for v in detail.values()):
        warns.append("Red score (3 in one parameter) → escalate even if NEWS2 <5 per RCP")

    q, qf = qsofa_score(rr, sbp, avpu)
    s, sf = sirs_score(temp, hr, rr, wcc)

    return WarningResult(patient_id, news2, news2_response(news2), detail, q, qf, s, sf, warns)

def calculate_news2(rr: float, spo2: float, o2_support: bool = False, sbp: float = 120, hr: float = 70, consciousness: str = "A", temp: float = 37.0, spo2_scale: int = 1) -> dict:
    res = assess("patient", rr=rr, spo2=spo2, spo2_scale=spo2_scale, supp_o2=1 if o2_support else 0, sbp=sbp, hr=hr, temp=temp, avpu=consciousness)
    return {"news2_score": res.news2, "response": res.news2_response, "detail": res.news2_detail, "warnings": res.warnings}

def calculate_qsofa(rr: float, sbp: float, gcs: Optional[int] = None, avpu: Optional[str] = None) -> dict:
    if avpu is None:
        avpu = "A" if (gcs is None or gcs >= 15) else "V"
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
            res = assess(pid, row["rr"], row["spo2"], row.get("spo2_scale",1), row.get("supplemental_o2",0),
                         row["systolic_bp"], row["heart_rate"], row["temperature"], row.get("avpu","A"), row.get("wcc"))
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
    s.add_argument("--temp", required=True, type=float); s.add_argument("--avpu", default="A", choices=["A","V","P","U","a","v","p","u"])
    s.add_argument("--wcc", type=float, default=None)
    b = sub.add_parser("batch"); b.add_argument("--input", required=True); b.add_argument("--output", required=True)
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
        print(f"Processed {len(results)} -> {a.output}  mean NEWS2={sum(r.news2 for r in results)/len(results):.1f}")
        for r in results: print(f"  {r.patient_id}: NEWS2={r.news2} qSOFA={r.qsofa} SIRS={r.sirs}")
        return 0
    p.print_help(); return 1

if __name__ == "__main__": sys.exit(main())
