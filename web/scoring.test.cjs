"use strict";
const test = require("node:test");
const assert = require("node:assert/strict");
const scoring = require("./scoring.js");
const base = {rr:16,spo2:98,scale:1,o2:0,sbp:120,hr:72,temp:37,avpu:"A",wcc:""};

test("normal observations and incomplete SIRS", () => {
  const r = scoring.assess(base);
  assert.equal(r.news2,0); assert.equal(r.qsofa,0);
  assert.equal(r.sirs,0); assert.equal(r.sirsComplete,false);
});
test("scale 2 room-air saturation above 92 never adds points", () => {
  for (const spo2 of [93,94,95,96,97,100]) {
    const r = scoring.assess({...base,scale:2,spo2});
    assert.equal(r.detail.SpO2,0);
    assert.equal(r.news2,0);
  }
});
test("scale 2 on oxygen includes saturation and oxygen points", () => {
  const values = [[83,3],[84,2],[86,1],[88,0],[92,0],[93,1],[94,1],[95,2],[96,2],[97,3]];
  values.forEach(([spo2, expected]) => {
    const r = scoring.assess({...base,scale:2,o2:1,spo2});
    assert.equal(r.detail.SpO2,expected); assert.equal(r.news2,expected+2);
  });
});
test("clinical red score, confusion, and SIRS count", () => {
  const r = scoring.assess({...base,rr:8,avpu:"C",hr:100,wcc:16});
  assert.equal(r.detail.RR,3);
  assert.equal(r.qsofa,1);
  assert.equal(r.sirs,2);
  assert.equal(r.sirsComplete,true);
});
test("non-finite, out-of-range, missing and fractional inputs reject", () => {
  for (const change of [{spo2:101},{rr:"NaN"},{hr:Infinity},{temp:36.05},
                        {rr:12.2},{avpu:""},{wcc:"xyz"},{scale:3},{o2:2}])
    assert.throws(()=>scoring.assess({...base,...change}));
});
test("quote-aware CSV rows parsed and malformed CSV rejected", () => {
  const input = "patient_id,rr,spo2,systolic_bp,heart_rate,temperature,avpu\r\n" +
                '"SYN,1",16,98,120,72,37.0,A\r\n';
  const rows = scoring.parseCsv(input);
  assert.equal(rows.length,1); assert.equal(rows[0].patient_id,"SYN,1");
  assert.throws(()=>scoring.parseCsv("rr,rr\n16,16\n"),/Duplicate/);
  assert.throws(()=>scoring.parseCsv("rr,spo2,systolic_bp,heart_rate,temperature,avpu\n16,98,120\n"),/column count/);
});
test("CSV export protects spreadsheet formula payloads", () => {
  const csv = scoring.exportCsv([{patientId:"=HYPERLINK(\"https://example.invalid\")",result:scoring.assess(base)}]);
  assert.match(csv, /'=HYPERLINK/);
});
