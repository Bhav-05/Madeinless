import httpx
import asyncio
import urllib.parse
import html
from collections import deque
from datetime import datetime
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

app = FastAPI(title="PS3 Observability Dashboard API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

TM1_CHAOS_URL = "http://10.42.121.220:9000/chaos/inject"
PROMETHEUS_URL = "http://10.42.121.220:9090/api/v1/query"
LOKI_URL = "http://10.42.121.220:3100/loki/api/v1/query_range"
HOST_MEMORY_BYTES = 2 * 1024 * 1024 * 1024  

def _rolling(initial_value: float, length: int = 30) -> list:
    return [initial_value] * length

dashboard_state: dict = {
    "global_metrics": {
        "logs_ingested_per_sec": 0,
        "active_anomalies": 0,
        "peak_ai_confidence_pct": 0,
        "total_auto_recoveries": 0,
        "alerts_suppressed": 0,
        "last_remediation_sla_seconds": 0.0,
    },
    "hardware_charts": {
        "cpu_usage_pct":    _rolling(0.0),
        "memory_usage_pct": _rolling(0.0),
        "ai_conf_pct":      _rolling(0.0),
    },
    "microservices": [],
    "traffic_rps": [0, 0, 0, 0, 0, 0],
    "latest_remediation": None,
    "log_stream": [],
}

_log_buffer: deque = deque(maxlen=50)

SERVICE_MAPPING = {
    "frontend": "frontend",
    "payment": "paymentservice",
    "checkout": "checkoutservice",
    "catalog": "catalogservice",
    "cart": "cartservice",
    "recommendationservice": "recommendationservice"
}

for ui_name in SERVICE_MAPPING.keys():
    dashboard_state["microservices"].append({
        "name": ui_name,
        "latency_ms": 0.0,
        "latency_pct": 0.0,
        "latency_status": "good",
        "log_anomaly": "Normal",   # No anomaly detected until AI webhook fires
        "metric_state": "HEALTHY",
        "ai_confidence": 0,
        "remediation": "None",
        "requests_per_sec": 0,
    })

class LogEvent(BaseModel):
    timestamp: str = Field(default_factory=lambda: datetime.now().strftime("%H:%M:%S"))
    service: str = Field(...)
    log_text: str = Field(...)
    classification: str = Field(...)
    nlp_confidence: float = Field(..., ge=0.0, le=1.0)
    badge_type: str = Field(...)

class RemediationPayload(BaseModel):
    service: str = Field(...)
    nlp_confidence: float = Field(..., ge=0.0, le=1.0)
    metric_deviation: float = Field(...)
    total_confidence: float = Field(..., ge=0.0, le=1.0)
    restart_latency_sec: float = Field(...)
    action_taken: str = Field(...)
    log_anomaly_summary: str = Field(...)
    metric_state: str = Field(...)
    remediation_type: str = Field(...)

class ChaosRequest(BaseModel):
    target_service: str = Field(...)
    fault_type: str = Field(...)

def _append_rolling(series: list, value: float, maxlen: int = 30) -> list:
    series.append(round(value, 2))
    return series[-maxlen:]

# INCREASED max_val so the frontend asset traffic doesn't explode the bar width
def _normalise_latency(val: float, max_val: float = 2500.0) -> float:
    return round(min(val / max_val * 100, 100), 1)

async def fetch_prom_metric(client, query):
    try:
        response = await client.get(PROMETHEUS_URL, params={'query': query}, timeout=2.0)
        if response.status_code != 200:
            return 0.0
        results = response.json().get('data', {}).get('result', [])
        if results:
            return float(results[0]['value'][1])
        return 0.0
    except Exception:
        return 0.0

async def poll_prometheus():
    async with httpx.AsyncClient() as client:
        while True:
            total_cpu_pct = 0
            total_mem_bytes = 0
            updated_rows = []
            
            for ui_name, prom_name in SERVICE_MAPPING.items():
                mem_query = f'container_memory_usage_bytes{{container_label_com_docker_compose_service="{prom_name}"}}'
                mem_bytes = await fetch_prom_metric(client, mem_query)
                total_mem_bytes += mem_bytes

                cpu_query = f'rate(container_cpu_usage_seconds_total{{container_label_com_docker_compose_service="{prom_name}"}}[1m])'
                cpu_val = await fetch_prom_metric(client, cpu_query)
                total_cpu_pct += (cpu_val * 100)

                net_in_query = f'rate(container_network_receive_bytes_total{{container_label_com_docker_compose_service="{prom_name}"}}[1m]) / 1024'
                net_in_kb = await fetch_prom_metric(client, net_in_query)

                net_out_query = f'rate(container_network_transmit_bytes_total{{container_label_com_docker_compose_service="{prom_name}"}}[1m]) / 1024'
                net_out_kb = await fetch_prom_metric(client, net_out_query)
                
                latency_status = "good"
                if cpu_val > 0.8: latency_status = "alert"
                elif cpu_val > 0.5: latency_status = "warn"

                existing = next((r for r in dashboard_state["microservices"] if r["name"] == ui_name), None)
                
                updated_rows.append({
                    "name": ui_name,
                    "latency_ms": round(net_out_kb, 1), 
                    "latency_pct": _normalise_latency(net_out_kb),
                    "latency_status": latency_status,
                    "log_anomaly": existing["log_anomaly"] if existing else "Normal",
                    "metric_state": "CRITICAL" if existing and existing["metric_state"] == "CRITICAL" else ("DEGRADED" if latency_status != "good" else "HEALTHY"),
                    "ai_confidence": existing["ai_confidence"] if existing else 0,
                    "remediation": existing["remediation"] if existing else "None",
                    "requests_per_sec": int(net_in_kb) 
                })

            memory_usage_pct = (total_mem_bytes / HOST_MEMORY_BYTES) * 100
            
            # CAP CPU at 100% so it doesn't break the graph
            capped_cpu = min(total_cpu_pct, 100.0)

            promtail_ingest_query = 'sum(rate(promtail_sent_bytes_total[1m]))'
            ingested_val = await fetch_prom_metric(client, promtail_ingest_query)

            dashboard_state["hardware_charts"]["cpu_usage_pct"] = _append_rolling(dashboard_state["hardware_charts"]["cpu_usage_pct"], capped_cpu)
            dashboard_state["hardware_charts"]["memory_usage_pct"] = _append_rolling(dashboard_state["hardware_charts"]["memory_usage_pct"], memory_usage_pct)
            dashboard_state["hardware_charts"]["ai_conf_pct"] = _append_rolling(dashboard_state["hardware_charts"]["ai_conf_pct"], dashboard_state["global_metrics"]["peak_ai_confidence_pct"])

            dashboard_state["global_metrics"]["logs_ingested_per_sec"] = int(ingested_val)
            dashboard_state["microservices"] = updated_rows
            dashboard_state["traffic_rps"] = [r["requests_per_sec"] for r in updated_rows]

            await asyncio.sleep(1.0)

async def poll_loki():
    seen_logs = set()
    async with httpx.AsyncClient() as client:
        while True:
            query = '{container_label_com_docker_compose_service=~".+"}'
            encoded_query = urllib.parse.quote(query)
            url = f"{LOKI_URL}?query={encoded_query}&limit=10&direction=backward"
            
            try:
                response = await client.get(url, timeout=2.0)
                if response.status_code != 200:
                    await asyncio.sleep(2.0)
                    continue

                data = response.json()
                results = data.get('data', {}).get('result', [])
                
                for result in results:
                    service = result.get('stream', {}).get('container_label_com_docker_compose_service', 'system')
                    for value in result.get('values', []):
                        raw_text = str(value[1]) if len(value) > 1 else str(value)
                        if raw_text in seen_logs:
                            continue
                        seen_logs.add(raw_text)
                        
                        # ESCAPE HTML TAGS SO THE UI DOESN'T BREAK
                        safe_text = html.escape(raw_text[:150])
                        
                        event = {
                            "timestamp": datetime.now().strftime("%H:%M:%S"),
                            "service": service,
                            "log_text": safe_text,
                            "classification": "NORMAL", 
                            "nlp_confidence": 100,
                            "badge_type": "SYS",
                        }
                        
                        _log_buffer.append(event)
                        dashboard_state["log_stream"] = list(_log_buffer)

            except Exception:
                pass
            
            await asyncio.sleep(2.0)

@app.on_event("startup")
async def startup_event():
    asyncio.create_task(poll_prometheus())
    asyncio.create_task(poll_loki())

@app.post("/api/v1/webhook/log_event")
async def receive_log_event(payload: LogEvent):
    gm = dashboard_state["global_metrics"]

    if payload.classification == "NORMAL":
        gm["alerts_suppressed"] = gm.get("alerts_suppressed", 0) + 1
        return {"status": "suppressed"}

    event = {
        "timestamp":      payload.timestamp,
        "service":        payload.service,
        "log_text":       html.escape(payload.log_text), # Escape incoming AI text
        "classification": payload.classification,
        "nlp_confidence": round(payload.nlp_confidence * 100),   
        "badge_type":     payload.badge_type,
    }

    _log_buffer.append(event)
    dashboard_state["log_stream"] = list(_log_buffer)

    if payload.classification == "CRITICAL":
        gm["active_anomalies"] = gm.get("active_anomalies", 0) + 1
        if round(payload.nlp_confidence * 100) > gm.get("peak_ai_confidence_pct", 0):
            gm["peak_ai_confidence_pct"] = round(payload.nlp_confidence * 100)

        for row in dashboard_state["microservices"]:
            if row["name"] == payload.service.replace("-service", "") or row["name"] == payload.service:
                row["log_anomaly"] = "AI Critical Alert"
                row["metric_state"] = "CRITICAL"
                row["ai_confidence"] = round(payload.nlp_confidence * 100)

    elif payload.classification == "WARNING":
        for row in dashboard_state["microservices"]:
            if row["name"] == payload.service.replace("-service", "") or row["name"] == payload.service:
                if row["metric_state"] != "CRITICAL":
                    row["log_anomaly"] = "AI Warning"
                    row["metric_state"] = "DEGRADED"
                    row["ai_confidence"] = round(payload.nlp_confidence * 100)

    return {"status": "ok", "classification": payload.classification}

@app.post("/api/v1/webhook/remediation")
async def receive_remediation(payload: RemediationPayload):
    gm = dashboard_state["global_metrics"]

    gm["active_anomalies"]            = 0
    gm["total_auto_recoveries"]       = gm.get("total_auto_recoveries", 0) + 1
    gm["last_remediation_sla_seconds"] = round(payload.restart_latency_sec, 3)
    gm["peak_ai_confidence_pct"]      = round(payload.total_confidence * 100)

    dashboard_state["latest_remediation"] = {
        **payload.model_dump(),
        "received_at": datetime.now().strftime("%H:%M:%S"),
        "rca_summary": (
            f"RCA Complete: Detected '{html.escape(payload.log_anomaly_summary)}' in "
            f"{payload.service}. Cross-referenced with a "
            f"{round(float(payload.metric_deviation) * 100, 1)}% metric deviation. "
            f"System reached {round(payload.total_confidence * 100)}% confidence. "
            f"Action: {payload.action_taken.replace('_', ' ')} executed in "
            f"{payload.restart_latency_sec:.2f}s."
        ),
    }

    resolved_event = {
        "timestamp":      datetime.now().strftime("%H:%M:%S"),
        "service":        payload.service,
        "log_text":       f"✓ Remediation complete {payload.action_taken.replace('_', ' ')} in {payload.restart_latency_sec:.2f}s",
        "classification": "RESOLVED",
        "nlp_confidence": round(payload.total_confidence * 100),
        "badge_type":     "SYS",
    }
    _log_buffer.append(resolved_event)
    dashboard_state["log_stream"] = list(_log_buffer)

    for row in dashboard_state["microservices"]:
        if row["name"] == payload.service or row["name"] == payload.service.replace("-service", ""):
            row["latency_status"] = "good"
            row["metric_state"]   = "HEALTHY"
            row["log_anomaly"]    = "Normal"
            row["remediation"]    = payload.remediation_type
            row["ai_confidence"]  = 0

    return {"status": "acknowledged", "rca": dashboard_state["latest_remediation"]["rca_summary"]}

@app.post("/api/v1/chaos/inject")
async def inject_chaos(request: ChaosRequest):
    for row in dashboard_state["microservices"]:
        if row["name"] == request.target_service or \
           row["name"] == request.target_service + "-service" or \
           row["name"] == request.target_service.replace("-service", ""):
            row["latency_status"] = "alert"
            row["metric_state"]   = "CRITICAL"
            row["log_anomaly"]    = f"Fault injected: {request.fault_type}"

    dashboard_state["global_metrics"]["active_anomalies"] = \
        dashboard_state["global_metrics"].get("active_anomalies", 0) + 1

    inject_event = {
        "timestamp":      datetime.now().strftime("%H:%M:%S"),
        "service":        request.target_service,
        "log_text":       f"Manual override: Injecting '{request.fault_type}' into {request.target_service}...",
        "classification": "WARNING",
        "nlp_confidence": 100,
        "badge_type":     "WARN",
    }
    _log_buffer.append(inject_event)
    dashboard_state["log_stream"] = list(_log_buffer)

    try:
        async with httpx.AsyncClient(timeout=3.0) as client:
            resp = await client.post(
                TM1_CHAOS_URL,
                json={"target_service": request.target_service, "fault_type": request.fault_type},
            )
            tm1_status = resp.status_code
    except Exception as exc:
        tm1_status = f"unreachable ({exc.__class__.__name__})"
        
    return {
        "status":        "injected",
        "target_service": request.target_service,
        "fault_type":    request.fault_type,
        "tm1_status":    tm1_status,
    }

@app.get("/api/v1/dashboard/state")
async def get_dashboard_state():
    return dashboard_state

@app.get("/health")
async def health():
    return {"status": "ok", "timestamp": datetime.now().isoformat()}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)