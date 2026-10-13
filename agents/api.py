"""
FastAPI REST API Server for News2 Qsofa Early Warning.
"""
from typing import Dict, Any, List, Optional
from dataclasses import asdict
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from .base import AuditLogger, PHIGuard
from .models import SystemTaskPayload, ConsensusDossier
from .supervisor import SystemSupervisor
from news2_qsofa import assess

supervisor = SystemSupervisor(model_provider="mock")

app = FastAPI(
    title="News2 Qsofa Early Warning API",
    description="Enterprise Distributed Component Platform (Clinical & Biomedical AI)",
    version="3.0.0-ENTERPRISE",
)


class ChatRequest(BaseModel):
    query: str


class VitalSigns(BaseModel):
    """Observations for deterministic scoring; no patient identifiers accepted."""
    rr: float
    spo2: float
    spo2_scale: int = 1
    supplemental_o2: int = 0
    systolic_bp: float
    heart_rate: float
    temperature: float
    avpu: str
    wcc: Optional[float] = None


@app.post("/api/score")
def api_score(vitals: VitalSigns):
    """Calculate NEWS2, qSOFA and SIRS without retaining the observation set."""
    try:
        result = assess(
            "anonymous", vitals.rr, vitals.spo2, vitals.spo2_scale,
            vitals.supplemental_o2, vitals.systolic_bp,
            vitals.heart_rate, vitals.temperature, vitals.avpu, vitals.wcc)
    except (TypeError, ValueError) as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return asdict(result)


@app.get("/health")
def health():
    return {"status": "HEALTHY", "service": "news2-qsofa-early-warning", "domain": "Clinical & Biomedical AI", "standard": "CAP / CLSI / ISO Standards", "version": "3.0.0-ENTERPRISE"}


@app.get("/metrics")
def metrics():
    return {
        "dossiers_processed_total": len(supervisor.dossier_registry),
        "audit_blocks_total": len(AuditLogger.get_trail()),
        "system_status": "NOMINAL_OPTIMAL"
    }


@app.post("/api/audit")
def api_audit(payload: SystemTaskPayload):
    dossier = supervisor.process_task(payload)
    return dossier.to_dict()


@app.post("/api/chat")
def api_chat(req: ChatRequest):
    try:
        ans = supervisor.query_supervisory_chat(req.query)
        return {"response": ans}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.get("/api/audit/logs")
def api_audit_logs():
    return {"audit_trail": AuditLogger.get_trail(), "verified": AuditLogger.verify_integrity()}
