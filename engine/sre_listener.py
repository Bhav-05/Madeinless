import asyncio
import logging
import time
from statistics import mean
from typing import List, Optional
from contextlib import asynccontextmanager

import httpx
import uvicorn
from fastapi import BackgroundTasks, FastAPI
from pydantic import BaseModel

from sre_prototype import run_sre_engine

ACTIVE_RESTORATIONS = set()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)
logger = logging.getLogger("sre_listener")

http_client: Optional[httpx.AsyncClient] = None

@asynccontextmanager
async def lifespan(app: FastAPI):
    global http_client
    http_client = httpx.AsyncClient(timeout=httpx.Timeout(10.0, connect=5.0))
    logger.info("HTTP client initialized")
    yield
    if http_client:
        await http_client.aclose()
        logger.info("HTTP client closed")

app = FastAPI(lifespan=lifespan)

PROMETHEUS_URL = "http://10.42.121.220:9090/api/v1/query_range"

class AnomalyAlert(BaseModel):
    service_name: str
    nlp_confidence: float

async def fetch_live_metrics(container_name: str) -> List[float]:
    if http_client is None:
        raise RuntimeError("HTTP client is not initialized")

    now = time.time()
    params = {
        "query": f'container_memory_usage_bytes{{container_label_com_docker_compose_service="{container_name}"}}',
        "start": now - 15,
        "end": now,
        "step": "1s",
    }

    try:
        response = await http_client.get(PROMETHEUS_URL, params=params)
        response.raise_for_status()
        results = response.json().get("data", {}).get("result", [])
        if not results:
            return []

        values = results[0].get("values", [])
        return [float(val[1]) for val in values if len(val) >= 2 and val[1] is not None]

    except httpx.HTTPStatusError as exc:
        logger.warning("Prometheus returned non-2xx status for %s: %s", container_name, exc)
    except Exception:
        logger.warning("Failed to fetch metrics for %s (Network Error). Using fallback.", container_name)

    return []

async def process_batch_alerts(alerts: List[AnomalyAlert]):
    if not alerts:
        return

    # THE FIX: Grab the first item in the list to get the target container name
    container_name = alerts[0].service_name

    if container_name in ACTIVE_RESTORATIONS:
        logger.info("🛡️ IDEMPOTENCY: Active lock for %s. Skipping.", container_name)
        return

    try:
        ACTIVE_RESTORATIONS.add(container_name)
        
        logger.info(f"⏳ Waiting 2s for Prometheus metrics to sync for {container_name}...")
        await asyncio.sleep(2) 
        
        live_metrics = await fetch_live_metrics(container_name)
        
        if len(live_metrics) > 5:
            healthy_history = live_metrics[:-3]
            current_spike = live_metrics[-3:]
        else:
            logger.warning(f"📉 Low data points for {container_name}. Using scaled baseline.")
            healthy_history = [100.0, 102.0, 101.0]
            current_spike = [105.0, 400.0, 800.0] 

        average_nlp_confidence = mean([alert.nlp_confidence for alert in alerts])

        await asyncio.to_thread(
            run_sre_engine,
            container_name,
            average_nlp_confidence,
            healthy_history,
            current_spike,
        )

    finally:
        await asyncio.sleep(8) 
        if container_name in ACTIVE_RESTORATIONS:
            ACTIVE_RESTORATIONS.remove(container_name)
            logger.info("SRE Ready: Lock released for %s", container_name)

@app.post("/alert")
async def receive_alert(payload: List[AnomalyAlert], background_tasks: BackgroundTasks):
    if not payload:
        return {"status": "Ignored - Empty Batch"}

    background_tasks.add_task(process_batch_alerts, payload)
    return {"status": "Batch Analysis Started", "alerts_processed": len(payload)}

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8001)