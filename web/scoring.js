/* NEWS2 (RCP 2017), qSOFA and partial/full SIRS. Local browser and Node. */
(function (root, factory) {
  "use strict";
  const api = factory();
  if (typeof module === "object" && module.exports) module.exports = api;
  else root.EarlyWarning = api;
})(typeof globalThis !== "undefined" ? globalThis : this, function () {
  "use strict";
  function measure(name, value, min, max, integer) {
    if (value === null || value === undefined || String(value).trim() === "")
      throw new Error(name + " is required");
    const x = Number(value);
    if (!Number.isFinite(x) || x < min || x > max)
      throw new Error(name + " must be finite and between " + min + " and " + max);
    if (integer && !Number.isInteger(x)) throw new Error(name + " must be a whole number");
    return x;
  }

  function assess(v) {
    const rr = measure("Respiratory rate", v.rr, 1, 100, true);
    const spo2 = measure("SpO2", v.spo2, 0, 100, true);
    const sbp = measure("Systolic pressure", v.sbp, 1, 400, true);
    const hr = measure("Heart rate", v.hr, 1, 300, true);
    const temp = measure("Temperature", v.temp, 25, 45, false);
    if (Math.abs(temp * 10 - Math.round(temp * 10)) > 1e-8)
      throw new Error("Temperature must have at most one decimal place");
    const scale = measure("SpO2 scale", v.scale, 1, 2, true);
    const o2 = measure("Supplemental oxygen", v.o2, 0, 1, true);
    const avpu = String(v.avpu == null ? "" : v.avpu).trim().toUpperCase();
    if (!["A", "C", "V", "P", "U"].includes(avpu))
      throw new Error("Consciousness must be A, C (new confusion), V, P or U");
    const hasWcc = v.wcc !== null && v.wcc !== undefined && String(v.wcc).trim() !== "";
    const wcc = hasWcc ? measure("WCC", v.wcc, 0, 1000, false) : null;

    const detail = {
      RR: rr <= 8 ? 3 : rr <= 11 ? 1 : rr <= 20 ? 0 : rr <= 24 ? 2 : 3,
      "SpO2": scale === 1 ?
        (spo2 <= 91 ? 3 : spo2 <= 93 ? 2 : spo2 <= 95 ? 1 : 0) :
        (spo2 <= 83 ? 3 : spo2 <= 85 ? 2 : spo2 <= 87 ? 1 :
         (!o2 || spo2 <= 92) ? 0 : spo2 <= 94 ? 1 : spo2 <= 96 ? 2 : 3),
      O2: o2 ? 2 : 0,
      SBP: sbp <= 90 ? 3 : sbp <= 100 ? 2 : sbp <= 110 ? 1 : sbp <= 219 ? 0 : 3,
      HR: hr <= 40 ? 3 : hr <= 50 ? 1 : hr <= 90 ? 0 : hr <= 110 ? 1 : hr <= 130 ? 2 : 3,
      Temp: temp <= 35 ? 3 : temp <= 36 ? 1 : temp <= 38 ? 0 : temp <= 39 ? 1 : 2,
      AVPU: avpu === "A" ? 0 : 3
    };
    const news2 = Object.values(detail).reduce((a, b) => a + b, 0);
    const red = Object.values(detail).some(x => x === 3);
    const response = news2 >= 7 ? "High — emergency assessment" :
      news2 >= 5 ? "Medium — urgent review" :
      red ? "Low–medium — single red parameter: urgent clinical review" :
      "Low — routine monitoring";
    const qsofaFlags = [];
    if (rr >= 22) qsofaFlags.push("RR >=22");
    if (sbp <= 100) qsofaFlags.push("SBP <=100");
    if (avpu !== "A") qsofaFlags.push("Altered consciousness");
    const sirsFlags = [];
    if (temp < 36 || temp > 38) sirsFlags.push("Temperature <36 or >38");
    if (hr > 90) sirsFlags.push("HR >90");
    if (rr > 20) sirsFlags.push("RR >20");
    if (hasWcc && (wcc < 4 || wcc > 12)) sirsFlags.push("WCC <4 or >12");
    const warnings = [];
    if (scale === 2) warnings.push("Scale 2 requires a clinician-prescribed SpO2 target of 88–92%.");
    if (red) warnings.push("A single NEWS2 parameter scores 3: urgent clinical review.");
    if (!hasWcc) warnings.push("SIRS is partial: WCC not supplied.");
    return {
      news2: news2, response: response, detail: detail, red: red,
      qsofa: qsofaFlags.length, qsofaFlags: qsofaFlags,
      sirs: sirsFlags.length, sirsFlags: sirsFlags, sirsComplete: hasWcc,
      warnings: warnings
    };
  }

  function parseCsv(csv) {
    const input = String(csv).replace(/^\uFEFF/, "");
    const rows = [], row = [];
    let field = "", quoted = false;
    for (let i = 0; i < input.length; i++) {
      const c = input[i];
      if (quoted) {
        if (c === '"' && input[i + 1] === '"') { field += '"'; i++; }
        else if (c === '"') quoted = false;
        else field += c;
      } else if (c === '"' && field === "") quoted = true;
      else if (c === ",") { row.push(field); field = ""; }
      else if (c === "\n" || c === "\r") {
        if (c === "\r" && input[i + 1] === "\n") i++;
        row.push(field); field = "";
        if (row.some(x => x !== "")) rows.push(row.splice(0));
        else row.length = 0;
      } else if (c === '"') throw new Error("Unexpected quote in CSV");
      else field += c;
    }
    if (quoted) throw new Error("Unclosed quoted CSV field");
    row.push(field);
    if (row.some(x => x !== "")) rows.push(row);
    if (!rows.length) throw new Error("CSV is empty");
    const header = rows.shift().map(h => h.trim());
    if (new Set(header).size !== header.length) throw new Error("Duplicate CSV column");
    const required = ["rr", "spo2", "systolic_bp", "heart_rate", "temperature"];
    required.forEach(h => { if (!header.includes(h)) throw new Error("Missing column: " + h); });
    if (!header.includes("avpu") && !header.includes("consciousness"))
      throw new Error("CSV requires avpu or consciousness column");
    return rows.map((cells, i) => {
      if (cells.length !== header.length) throw new Error("Row " + (i + 2) + ": incorrect column count");
      const o = {};
      header.forEach((h, j) => { o[h] = cells[j]; });
      return o;
    });
  }
  function quoteCsv(v) {
    let s = String(v === null || v === undefined ? "" : v);
    // Prevent spreadsheet formula execution when downloaded CSV is opened.
    if (/^[\s\u0000-\u001f]*[=+@-]/.test(s)) s = "\u0027" + s;
    return /[",\r\n]/.test(s) ? '"' + s.replace(/"/g, '""') + '"' : s;
  }
  function exportCsv(results) {
    const header = ["patient_id", "news2", "news2_response", "RR", "SpO2", "O2", "SBP",
                    "HR", "Temp", "AVPU", "qsofa", "sirs", "sirs_complete", "warnings"];
    const lines = [header.join(",")];
    results.forEach(({ patientId, result }) => {
      lines.push([
        patientId, result.news2, result.response, result.detail.RR, result.detail.SpO2,
        result.detail.O2, result.detail.SBP, result.detail.HR, result.detail.Temp,
        result.detail.AVPU, result.qsofa, result.sirs, result.sirsComplete,
        result.warnings.join("; ")
      ].map(quoteCsv).join(","));
    });
    return lines.join("\r\n") + "\r\n";
  }
  return { assess: assess, parseCsv: parseCsv, exportCsv: exportCsv };
});
