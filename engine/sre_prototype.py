import docker
import time
import numpy as np
import httpx

_DOCKER_CLIENT = None

def get_docker_client():
    global _DOCKER_CLIENT
    if _DOCKER_CLIENT is None:
        _DOCKER_CLIENT = docker.from_env()
    return _DOCKER_CLIENT

def execute_autonomous_restart(target_container_name):
    start_time = time.perf_counter()
    daemon_client = get_docker_client()
    failing_workload = daemon_client.containers.get(target_container_name)
    failing_workload.restart(timeout=0)
    end_time = time.perf_counter()
    return end_time - start_time

def calculate_system_confidence(nlp_score, metric_deviation):
    nlp_weight = 0.5
    metric_weight = 0.5
    
    metric_score = np.select(
        [metric_deviation > 100, metric_deviation > 50],
        [1.0, 0.8],
        default=0.3
    )
    
    return (nlp_score * nlp_weight) + (metric_score * metric_weight)

def send_ui_receipt(container_name, nlp_score, deviation, confidence, latency, status):
    tm4_dashboard_url = "http://10.42.121.70:8000/api/v1/webhook/remediation"
    
    # Calculate the metric state based on your math
    m_state = "CRITICAL" if deviation > 100 else "DEGRADED" if deviation > 50 else "HEALTHY"
    
    payload = {
        "service": container_name,
        "nlp_confidence": float(nlp_score),
        "metric_deviation": float(deviation),
        "total_confidence": float(confidence),
        "restart_latency_sec": float(latency),
        "action_taken": status,
        # THE 3 NEW FIELDS TM4 REQUESTED:
        "log_anomaly_summary": "System Crash / OOM Error Detected", 
        "metric_state": m_state,
        "remediation_type": "container_restart"
    }
    
    try:
        httpx.post(tm4_dashboard_url, json=payload, timeout=2.0)
        print("UI RECEIPT: Resolution data transmitted to TM4 dashboard.")
    except Exception as e:
        print(f"UI RECEIPT WARNING: Dashboard unreachable - {e}")

def run_sre_engine(container_name, nlp_score, healthy_history, current_metrics):
    healthy_history = np.asarray(healthy_history)
    current_metrics = np.asarray(current_metrics)
    
    baseline_avg = np.mean(healthy_history)
    current_peak = np.max(current_metrics)
    
    if baseline_avg == 0:
        print(f"WARNING: Zero baseline for {container_name}. Skipping.")
        return
    
    deviation = ((current_peak - baseline_avg) / baseline_avg) * 100
    confidence = calculate_system_confidence(nlp_score, deviation)
    
    print(f"--- SRE Analysis for {container_name} ---")
    print(f"NLP Confidence: {nlp_score:.2%}")
    print(f"Metric Deviation: {deviation:.2f}%")
    print(f"Total System Confidence: {confidence:.2%}")
    
    if confidence > 0.60:
        print("ACTION: CONFIRMED CRASH. Initializing immediate restart...")
        latency = execute_autonomous_restart(container_name)
        print(f"SUCCESS: {container_name} restored in {latency:.4f} seconds.")
        send_ui_receipt(container_name, nlp_score, deviation, confidence, latency, "Warm Restart Executed")
    else:
        print("ACTION: FALSE ALARM. No infrastructure changes made.")
        send_ui_receipt(container_name, nlp_score, deviation, confidence, 0.0, "Suppressed False Alarm")
    print("-" * 40)