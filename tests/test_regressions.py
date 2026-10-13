"""Clinical boundary, CSV and audit-integrity regressions."""
import csv
import math
import tempfile
from pathlib import Path

import pytest

from agents.base import AuditTrail
from news2_qsofa import assess, calculate_qsofa, main, process_csv


BASE = dict(patient_id="synthetic", rr=16, spo2=98, spo2_scale=1,
            supp_o2=0, sbp=120, hr=72, temp=37.0, avpu="A")


def test_scale_2_room_air_does_not_score_hyperoxia():
    for saturation in [93, 94, 95, 96, 97, 100]:
        res = assess(**{**BASE, "spo2": saturation, "spo2_scale": 2})
        assert res.news2_detail["SpO2"] == 0
        assert res.news2_detail["O2"] == 0
        assert res.news2 == 0


@pytest.mark.parametrize("spo2,points", [(83, 3), (84, 2), (86, 1),
                                         (88, 0), (92, 0), (93, 1),
                                         (94, 1), (95, 2), (96, 2), (97, 3)])
def test_scale_2_on_oxygen(spo2, points):
    res = assess(**{**BASE, "spo2": spo2, "spo2_scale": 2, "supp_o2": 1})
    assert res.news2_detail["SpO2"] == points
    assert res.news2_detail["O2"] == 2


def test_single_red_escalates_response():
    res = assess(**{**BASE, "rr": 8})
    assert res.news2 == 3
    assert "urgent" in res.news2_response.lower()


def test_acvpu_new_confusion():
    res = assess(**{**BASE, "avpu": "C"})
    assert res.news2_detail["AVPU"] == 3
    assert res.qsofa == 1


@pytest.mark.parametrize("overrides", [
    {"spo2": 101}, {"rr": 0}, {"rr": "NaN"}, {"sbp": math.inf},
    {"hr": ""}, {"temp": 36.05}, {"wcc": "not recorded"},
    {"spo2_scale": 3}, {"supp_o2": 2}, {"avpu": ""},
    {"rr": 12.5}, {"spo2": None},
])
def test_invalid_observations_are_rejected(overrides):
    with pytest.raises(ValueError):
        assess(**{**BASE, **overrides})


def test_sirs_wcc_missing_marked_incomplete():
    res = assess(**BASE)
    assert res.sirs == 0
    assert any("partial" in w.lower() for w in res.warnings)
    res = assess(**{**BASE, "wcc": "15.2"})
    assert res.sirs == 1
    assert not any("partial" in w.lower() for w in res.warnings)


def test_csv_accepts_empty_wcc_and_annotations(tmp_path):
    inp, out = tmp_path / "in.csv", tmp_path / "out.csv"
    inp.write_text("patient_id,rr,spo2,systolic_bp,heart_rate,temperature,avpu,wcc\n"
                   "SYN,16,98,120,72,37.0,A,\n", encoding="utf-8")
    result = process_csv(str(inp), str(out))
    assert result[0].sirs == 0
    assert "partial" in out.read_text(encoding="utf-8")
    with out.open(newline="", encoding="utf-8") as f:
        assert next(csv.DictReader(f))["patient_id"] == "SYN"


def test_csv_invalid_row_rejected_before_writing(tmp_path):
    inp, out = tmp_path / "in.csv", tmp_path / "out.csv"
    inp.write_text("rr,spo2,systolic_bp,heart_rate,temperature,avpu\n"
                   "16,98,120,72,37,A\n9,999,120,72,37,A\n", encoding="utf-8")
    with pytest.raises(ValueError, match="row 3"):
        process_csv(str(inp), str(out))
    assert not out.exists()


def test_empty_csv_and_cli_no_division_by_zero(tmp_path):
    inp, out = tmp_path / "empty.csv", tmp_path / "out.csv"
    inp.write_text("rr,spo2,systolic_bp,heart_rate,temperature,avpu\n", encoding="utf-8")
    assert main(["batch", "--input", str(inp), "--output", str(out)]) == 0


def test_qsofa_validates_gcs():
    with pytest.raises(ValueError):
        calculate_qsofa(22, 90, gcs=18)


def test_audit_detects_any_signed_record_tampering():
    audit = AuditTrail(secret_key="unit-test-only-audit-key")
    audit.log("test", "worker", "TEST", {"ok": True})
    audit.log("test", "supervisor", "SECOND", {"ok": True})
    assert audit.verify_integrity()
    returned = audit.get_trail()
    returned[0]["actor"] = "tampered"
    assert audit.verify_integrity(), "Returned logs must not alias internal state"
    audit.logs[0]["actor"] = "tampered"
    assert not audit.verify_integrity()


def test_api_scores_without_patient_identity():
    from fastapi import HTTPException
    from agents.api import VitalSigns, api_score
    data = VitalSigns(rr=16, spo2=98, systolic_bp=120,
                      heart_rate=72, temperature=37, avpu="A")
    result = api_score(data)
    assert result["news2"] == 0
    assert result["qsofa"] == 0
    assert result["patient_id"] == "anonymous"
    assert result["news2_detail"]["SpO2"] == 0
    bad = VitalSigns(rr=16, spo2=102, systolic_bp=120,
                     heart_rate=72, temperature=37, avpu="A")
    with pytest.raises(HTTPException) as error:
        api_score(bad)
    assert error.value.status_code == 422


def test_csv_export_escapes_formula_patient_id(tmp_path):
    inp, out = tmp_path / "formulas.csv", tmp_path / "results.csv"
    inp.write_text("patient_id,rr,spo2,systolic_bp,heart_rate,temperature,avpu\n"
                   "=HYPERLINK(1),16,98,120,72,37,A\n", encoding="utf-8")
    process_csv(str(inp), str(out))
    with out.open(newline="", encoding="utf-8") as f:
        record = next(csv.DictReader(f))
    assert record["patient_id"].startswith("'=")
