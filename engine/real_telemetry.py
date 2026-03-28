import time
import httpx
import asyncio

# TM4's Dashboard URL
TM4_TELEMETRY_URL = "http://10.42.121.70:8000/api/v1/webhook/telemetry"

# TM2's Prometheus Server (Running on your machine's IP)
PROMETHEUS_URL = "http://10.42.121.220:9090/api/v1/query" 

# Assume 16GB total memory for the host machine to calculate percentage.
HOST_MEMORY_BYTES = 16 * 1024 * 1024 * 1024 

async def fetch_prom_metric(client, query):
    """Fetches real data from TM2's Prometheus server."""
    try:
        response = await client.get(PROMETHEUS_URL, params={'query': query}, timeout=0.5)
        results = response.json().get('data', {}).get('result', [])
        if results:
            return float(results[0]['value'][1])
        return 0.0
    except Exception:
        # If Prometheus is down, return 0 instead of crashing the pump
        return 0.0

async def generate_real_telemetry(client):
    services = ["frontend", "payment", "checkout", "catalog", "cart", "recommendationservice"]
    service_health = []
    
    total_cpu_pct = 0
    total_mem_bytes = 0

    for svc in services:
        # 1. FIXED Hardware Metrics
        mem_query = f'container_memory_usage_bytes{{container_label_com_docker_compose_service="{svc}"}}'
        mem_bytes = await fetch_prom_metric(client, mem_query)
        total_mem_bytes += mem_bytes

        cpu_query = f'rate(container_cpu_usage_seconds_total{{container_label_com_docker_compose_service="{svc}"}}[1m])'
        cpu_val = await fetch_prom_metric(client, cpu_query)
        total_cpu_pct += (cpu_val * 100)

        # 2. FIXED Application Metrics (Using Network Traffic as a Proxy for RPS)
        # We calculate throughput in KB/s to show activity on the Bar Charts
        rps_query = f'rate(container_network_receive_bytes_total{{container_label_com_docker_compose_service="{svc}"}}[1m]) / 1024'
        rps_val = await fetch_prom_metric(client, rps_query)

        # 3. FIXED Latency (Simulated based on CPU load for the Radar Graph)
        # This ensures the Radar Graph actually moves and turns red during your crash!
        latency_ms = 10.0 + (cpu_val * 500) 

        latency_status = "good"
        if latency_ms > 300: latency_status = "alert"
        elif latency_ms > 150: latency_status = "warn"

        service_health.append({
            "name": svc,
            "latency_ms": round(latency_ms, 2),
            "latency_status": latency_status,
            "log_anomaly": "Normal",
            "metric_state": "HEALTHY",
            "ai_confidence": 0.0, 
            "remediation": "None",
            "requests_per_sec": int(rps_val) # Now shows actual traffic flow
        })

    # Global Metrics
    memory_usage_pct = (total_mem_bytes / HOST_MEMORY_BYTES) * 100
    
    # 4. FIXED Log Ingest Query
    promtail_ingest_query = 'sum(rate(promtail_sent_bytes_total[1m]))'
    ingested_val = await fetch_prom_metric(client, promtail_ingest_query)

    payload = {
        "services": service_health,
        "cpu_usage_pct": round(total_cpu_pct, 2),
        "memory_usage_pct": round(memory_usage_pct, 2),
        "ai_conf_pct": 0.0,
        "logs_ingested_per_sec": int(ingested_val)
    }
    return payload

async def run_telemetry_pump():
    print("🚀 INITIATING REAL TELEMETRY PUMP: Polling TM2's Prometheus...")
    
    async with httpx.AsyncClient() as client:
        while True:
            start_time = time.perf_counter()
            
            payload = await generate_real_telemetry(client)
            
            try:
                response = await client.post(TM4_TELEMETRY_URL, json=payload, timeout=1.0)
                frontend_data = payload['services'][0]
                print(f"[{time.strftime('%H:%M:%S')}] CPU {payload['cpu_usage_pct']}% | Frontend RPS: {frontend_data['requests_per_sec']} | Frontend Latency: {frontend_data['latency_ms']}ms")
            except Exception as e:
                print(f"[{time.strftime('%H:%M:%S')}] Failed to reach TM4 dashboard: {e}")
            
            elapsed = time.perf_counter() - start_time
            await asyncio.sleep(max(0, 1.0 - elapsed))

if __name__ == "__main__":
    asyncio.run(run_telemetry_pump())