#!/usr/bin/env python3
"""Tests for NEWS2 + qSOFA Early Warning Score Calculator.

Run with: python -m pytest test_news2_qsofa.py -v
    or:   python test_news2_qsofa.py
"""
import json
import os
import sys
import tempfile
import unittest

from news2_qsofa import (
    score_rr,
    score_spo2_scale1,
    score_spo2_scale2,
    score_sbp,
    score_hr,
    score_temp,
    score_consciousness,
    news2_response,
    qsofa_score,
    sirs_score,
    assess,
    calculate_news2,
    calculate_qsofa,
    process_csv,
    main,
)


class TestRRScoring(unittest.TestCase):
    """Test respiration rate scoring."""

    def test_rr_le_8(self):
        self.assertEqual(score_rr(8), 3)
        self.assertEqual(score_rr(5), 3)

    def test_rr_9_to_11(self):
        self.assertEqual(score_rr(9), 1)
        self.assertEqual(score_rr(10), 1)
        self.assertEqual(score_rr(11), 1)

    def test_rr_12_to_20(self):
        self.assertEqual(score_rr(12), 0)
        self.assertEqual(score_rr(18), 0)
        self.assertEqual(score_rr(20), 0)

    def test_rr_21_to_24(self):
        self.assertEqual(score_rr(21), 2)
        self.assertEqual(score_rr(24), 2)

    def test_rr_ge_25(self):
        self.assertEqual(score_rr(25), 3)
        self.assertEqual(score_rr(30), 3)


class TestSpO2Scale1(unittest.TestCase):
    """Test SpO2 Scale 1 scoring."""

    def test_spo2_le_91(self):
        self.assertEqual(score_spo2_scale1(91), 3)
        self.assertEqual(score_spo2_scale1(85), 3)

    def test_spo2_92_93(self):
        self.assertEqual(score_spo2_scale1(92), 2)
        self.assertEqual(score_spo2_scale1(93), 2)

    def test_spo2_94_95(self):
        self.assertEqual(score_spo2_scale1(94), 1)
        self.assertEqual(score_spo2_scale1(95), 1)

    def test_spo2_ge_96(self):
        self.assertEqual(score_spo2_scale1(96), 0)
        self.assertEqual(score_spo2_scale1(100), 0)


class TestSpO2Scale2(unittest.TestCase):
    """Test SpO2 Scale 2 (COPD) scoring."""

    def test_spo2_le_83(self):
        self.assertEqual(score_spo2_scale2(83), 3)
        self.assertEqual(score_spo2_scale2(80), 3)

    def test_spo2_84_85(self):
        self.assertEqual(score_spo2_scale2(84), 2)
        self.assertEqual(score_spo2_scale2(85), 2)

    def test_spo2_86_87(self):
        self.assertEqual(score_spo2_scale2(86), 1)
        self.assertEqual(score_spo2_scale2(87), 1)

    def test_spo2_88_92(self):
        """Target range for COPD on O2."""
        self.assertEqual(score_spo2_scale2(88), 0)
        self.assertEqual(score_spo2_scale2(90), 0)
        self.assertEqual(score_spo2_scale2(92), 0)

    def test_spo2_93_94(self):
        self.assertEqual(score_spo2_scale2(93), 1)
        self.assertEqual(score_spo2_scale2(94), 1)

    def test_spo2_95_96(self):
        self.assertEqual(score_spo2_scale2(95), 2)
        self.assertEqual(score_spo2_scale2(96), 2)

    def test_spo2_ge_97(self):
        self.assertEqual(score_spo2_scale2(97), 3)
        self.assertEqual(score_spo2_scale2(100), 3)


class TestSBPScoring(unittest.TestCase):
    """Test systolic BP scoring."""

    def test_sbp_le_90(self):
        self.assertEqual(score_sbp(90), 3)
        self.assertEqual(score_sbp(80), 3)

    def test_sbp_91_100(self):
        self.assertEqual(score_sbp(91), 2)
        self.assertEqual(score_sbp(100), 2)

    def test_sbp_101_110(self):
        self.assertEqual(score_sbp(101), 1)
        self.assertEqual(score_sbp(110), 1)

    def test_sbp_111_219(self):
        self.assertEqual(score_sbp(111), 0)
        self.assertEqual(score_sbp(120), 0)
        self.assertEqual(score_sbp(219), 0)

    def test_sbp_ge_220(self):
        self.assertEqual(score_sbp(220), 3)
        self.assertEqual(score_sbp(250), 3)


class TestHRScoring(unittest.TestCase):
    """Test heart rate scoring."""

    def test_hr_le_40(self):
        self.assertEqual(score_hr(40), 3)
        self.assertEqual(score_hr(30), 3)

    def test_hr_41_50(self):
        self.assertEqual(score_hr(41), 1)
        self.assertEqual(score_hr(50), 1)

    def test_hr_51_90(self):
        self.assertEqual(score_hr(51), 0)
        self.assertEqual(score_hr(70), 0)
        self.assertEqual(score_hr(90), 0)

    def test_hr_91_110(self):
        self.assertEqual(score_hr(91), 1)
        self.assertEqual(score_hr(110), 1)

    def test_hr_111_130(self):
        self.assertEqual(score_hr(111), 2)
        self.assertEqual(score_hr(130), 2)

    def test_hr_ge_131(self):
        self.assertEqual(score_hr(131), 3)
        self.assertEqual(score_hr(150), 3)


class TestTempScoring(unittest.TestCase):
    """Test temperature scoring."""

    def test_temp_le_35(self):
        self.assertEqual(score_temp(35.0), 3)
        self.assertEqual(score_temp(34.0), 3)

    def test_temp_35_1_to_36(self):
        self.assertEqual(score_temp(35.1), 1)
        self.assertEqual(score_temp(36.0), 1)

    def test_temp_36_1_to_38(self):
        self.assertEqual(score_temp(36.1), 0)
        self.assertEqual(score_temp(37.0), 0)
        self.assertEqual(score_temp(38.0), 0)

    def test_temp_38_1_to_39(self):
        self.assertEqual(score_temp(38.1), 1)
        self.assertEqual(score_temp(39.0), 1)

    def test_temp_ge_39_1(self):
        self.assertEqual(score_temp(39.1), 2)
        self.assertEqual(score_temp(40.0), 2)


class TestConsciousness(unittest.TestCase):
    """Test consciousness scoring."""

    def test_alert(self):
        self.assertEqual(score_consciousness("A"), 0)

    def test_confused(self):
        self.assertEqual(score_consciousness("C"), 3)

    def test_verbal(self):
        self.assertEqual(score_consciousness("V"), 3)

    def test_pain(self):
        self.assertEqual(score_consciousness("P"), 3)

    def test_unresponsive(self):
        self.assertEqual(score_consciousness("U"), 3)


class TestNEWS2Response(unittest.TestCase):
    """Test NEWS2 response categories."""

    def test_low_risk(self):
        self.assertIn("Low", news2_response(0))
        self.assertIn("Low", news2_response(4))

    def test_medium_risk(self):
        self.assertIn("Medium", news2_response(5))
        self.assertIn("Medium", news2_response(6))

    def test_high_risk(self):
        self.assertIn("High", news2_response(7))
        self.assertIn("High", news2_response(15))


class TestQSOFA(unittest.TestCase):
    """Test qSOFA scoring."""

    def test_qsofa_zero(self):
        """Normal vitals: qSOFA = 0."""
        score, flags = qsofa_score(16, 130, "A")
        self.assertEqual(score, 0)
        self.assertEqual(len(flags), 0)

    def test_qsofa_rr_high(self):
        """RR >= 22: 1 point."""
        score, flags = qsofa_score(24, 130, "A")
        self.assertEqual(score, 1)
        self.assertIn("RR>=22", flags)

    def test_qsofa_sbp_low(self):
        """SBP <= 100: 1 point."""
        score, flags = qsofa_score(16, 95, "A")
        self.assertEqual(score, 1)
        self.assertIn("SBP<=100", flags)

    def test_qsofa_altered_mental(self):
        """Altered consciousness: 1 point."""
        score, flags = qsofa_score(16, 130, "V")
        self.assertEqual(score, 1)
        self.assertIn("GCS<15/avpu!=A", flags)

    def test_qsofa_all_three(self):
        """All three criteria met: qSOFA = 3."""
        score, flags = qsofa_score(25, 90, "V")
        self.assertEqual(score, 3)

    def test_qsofa_two_criteria(self):
        """Two criteria: qSOFA = 2 (sepsis risk)."""
        score, flags = qsofa_score(24, 95, "A")
        self.assertEqual(score, 2)


class TestSIRS(unittest.TestCase):
    """Test SIRS scoring."""

    def test_sirs_zero(self):
        score, flags = sirs_score(37.0, 80, 16)
        self.assertEqual(score, 0)

    def test_sirs_temp_abnormal(self):
        score, flags = sirs_score(35.5, 80, 16)
        self.assertEqual(score, 1)

    def test_sirs_hr_high(self):
        score, flags = sirs_score(37.0, 95, 16)
        self.assertEqual(score, 1)

    def test_sirs_rr_high(self):
        score, flags = sirs_score(37.0, 80, 22)
        self.assertEqual(score, 1)

    def test_sirs_wcc_abnormal(self):
        score, flags = sirs_score(37.0, 80, 16, wcc=15.0)
        self.assertEqual(score, 1)

    def test_sirs_multiple(self):
        score, flags = sirs_score(39.0, 100, 24)
        self.assertEqual(score, 3)


class TestAssess(unittest.TestCase):
    """Test full assessment function."""

    def test_healthy_patient(self):
        """Healthy patient: NEWS2 = 0, qSOFA = 0."""
        result = assess("P001", rr=16, spo2=98, spo2_scale=1, supp_o2=0,
                        sbp=120, hr=72, temp=37.0, avpu="A")
        self.assertEqual(result.news2, 0)
        self.assertEqual(result.qsofa, 0)

    def test_sick_patient(self):
        """Sick patient: high NEWS2 and qSOFA."""
        result = assess("P002", rr=28, spo2=88, spo2_scale=1, supp_o2=1,
                        sbp=85, hr=120, temp=39.5, avpu="V")
        self.assertGreaterEqual(result.news2, 7)
        self.assertGreaterEqual(result.qsofa, 2)

    def test_copd_patient_scale2(self):
        """COPD patient on O2 with Scale 2."""
        result = assess("P003", rr=18, spo2=90, spo2_scale=2, supp_o2=1,
                        sbp=130, hr=80, temp=37.0, avpu="A")
        # SpO2 90 on Scale 2 = 0 (target range)
        self.assertIn("Low", result.news2_response)

    def test_red_score_warning(self):
        """Any single parameter score of 3 triggers a warning."""
        result = assess("P004", rr=6, spo2=98, spo2_scale=1, supp_o2=0,
                        sbp=120, hr=72, temp=37.0, avpu="A")
        # RR 6 = score 3 (red)
        self.assertTrue(any("Red score" in w for w in result.warnings))


class TestCalculateNews2(unittest.TestCase):
    """Test the convenience calculate_news2 function."""

    def test_normal(self):
        result = calculate_news2(rr=16, spo2=98, o2_support=False,
                                 sbp=120, hr=72, consciousness="A", temp=37.0)
        self.assertEqual(result["news2_score"], 0)

    def test_high_news2(self):
        result = calculate_news2(rr=28, spo2=88, o2_support=True,
                                 sbp=85, hr=120, consciousness="V", temp=39.5)
        self.assertGreaterEqual(result["news2_score"], 7)


class TestCalculateQSOFA(unittest.TestCase):
    """Test the convenience calculate_qsofa function."""

    def test_normal(self):
        result = calculate_qsofa(rr=16, sbp=130, gcs=15)
        self.assertEqual(result["qsofa_score"], 0)

    def test_high_qsofa(self):
        result = calculate_qsofa(rr=24, sbp=90, gcs=12)
        self.assertEqual(result["qsofa_score"], 3)

    def test_avpu_override(self):
        result = calculate_qsofa(rr=16, sbp=130, avpu="V")
        self.assertEqual(result["qsofa_score"], 1)


class TestBatchProcessing(unittest.TestCase):
    """Test CSV batch processing."""

    def test_batch_csv(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            inp = os.path.join(tmpdir, "in.csv")
            out = os.path.join(tmpdir, "out.csv")
            with open(inp, "w") as f:
                f.write("patient_id,rr,spo2,spo2_scale,supplemental_o2,systolic_bp,heart_rate,temperature,avpu\n")
                f.write("P001,16,98,1,0,120,72,37.0,A\n")
                f.write("P002,28,88,1,1,85,120,39.5,V\n")
            results = process_csv(inp, out)
            self.assertEqual(len(results), 2)
            self.assertTrue(os.path.exists(out))


class TestCLI(unittest.TestCase):
    """Test CLI interface."""

    def test_single_command(self):
        ret = main(["single", "--rr", "16", "--spo2", "98",
                     "--sbp", "120", "--hr", "72", "--temp", "37.0"])
        self.assertEqual(ret, 0)

    def test_no_command(self):
        with self.assertRaises(SystemExit):
            main([])


if __name__ == "__main__":
    unittest.main(verbosity=2)
