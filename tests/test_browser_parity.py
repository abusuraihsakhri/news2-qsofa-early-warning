"""Parity between Python canonical scorer and dependency-free browser scorer."""
import json
import shutil
import subprocess
from pathlib import Path

import pytest

from news2_qsofa import assess


def test_browser_python_scoring_parity():
    node = shutil.which("node")
    if not node:
        pytest.skip("Node is not available in this environment")
    cases = []
    for scale in (1, 2):
        for oxygen in (0, 1):
            for spo2 in (80, 83, 84, 85, 86, 87, 88, 91, 92, 93, 94, 95, 96, 97, 100):
                for rr in (1, 8, 9, 11, 12, 16, 20, 21, 22, 23, 24, 25, 26, 30, 40, 100):
                    cases.append({
                        "rr": rr, "spo2": spo2, "scale": scale, "o2": oxygen,
                        "sbp": 100, "hr": 111, "temp": 38.1, "avpu": "C", "wcc": 13
                    })
    js_path = Path(__file__).resolve().parents[1] / "web" / "scoring.js"
    runner = ("const fs=require('node:fs');"
              "const score=require(process.argv[1]);"
              "const cases=JSON.parse(fs.readFileSync(0,'utf8'));"
              "process.stdout.write(JSON.stringify(cases.map(x=>score.assess(x))));")
    result = subprocess.run(
        [node, "-e", runner, str(js_path)],
        input=json.dumps(cases), capture_output=True, text=True, check=True, timeout=30)
    js = json.loads(result.stdout)
    assert len(js) == len(cases)
    for case, web in zip(cases, js):
        py = assess("synthetic", rr=case["rr"], spo2=case["spo2"],
                    spo2_scale=case["scale"], supp_o2=case["o2"],
                    sbp=case["sbp"], hr=case["hr"], temp=case["temp"],
                    avpu=case["avpu"], wcc=case["wcc"])
        assert web["news2"] == py.news2
        assert web["detail"] == py.news2_detail
        assert web["qsofa"] == py.qsofa
        assert web["sirs"] == py.sirs
