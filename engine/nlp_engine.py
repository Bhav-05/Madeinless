import os
os.environ["OMP_NUM_THREADS"] = "1"
import time
import json
import urllib.request
import urllib.parse
import urllib.error
import requests

HF_API_TOKEN = "HF_TOKEN"
API_URL = "https://api-inference.huggingface.co/models/typeform/distilbert-base-uncased-mnli"

headers = {"Authorization": f"Bearer {HF_API_TOKEN}", "Content-Type": "application/json"}

def drill_for_data(data):
    while isinstance(data, list):
        if len(data) == 0:
            return "unknown"
        data = data if isinstance(data, list) else data
    return data

def query_huggingface(log_text):
    payload = {
        "inputs": log_text,
        "parameters": {"candidate_labels": ["normal application behavior", "minor warning", "critical system crash"]}
    }
    data = json.dumps(payload).encode('utf-8')
    req = urllib.request.Request(API_URL, headers=headers, data=data, method="POST")

    try:
        with urllib.request.urlopen(req) as response:
            return json.loads(response.read().decode('utf-8'))
    except urllib.error.HTTPError as e:
        print(f"  [☁️ Hugging Face API Blocked: Error {e.code}]") 
        return None
    except Exception as e:
        return None

def fetch_live_logs():
    query = '{container_label_com_docker_compose_service="cartservice"}'
    encoded_query = urllib.parse.quote(query)
    url = f"http://localhost:3100/loki/api/v1/query_range?query={encoded_query}&limit=10&direction=backward"

    try:
        req = urllib.request.Request(url)
        with urllib.request.urlopen(req) as response:
            data = json.loads(response.read().decode('utf-8'))
            logs = []
            results = data.get('data', {}).get('result', [])
            for result in results:
                for value in result.get('values', []):
                    if isinstance(value, list) and len(value) > 1:
                        logs.append(value)
                    else:
                        logs.append(str(value))
            return logs
    except Exception as e:
        print(f"⚠️ Connection Error: {e}")
        return []

def process_logs():
    print("\n--- SILICON FLOW LIVE TELEMETRY ENGINE ---")
    print("Listening to Localhost Database...\n")
    
    seen_logs = set()
    
    # --- TEAM ENDPOINTS ---
    tm4_url = "http://10.42.121.70:8000/api/v1/webhook/log_event"
    tm3_url = "http://10.42.121.26:8001/alert"
    
    while True:
        live_logs = fetch_live_logs()
        print(f"📡 Radar Sweep: Scanned {len(live_logs)} logs... Waiting for anomalies.", end="\r")
        
        for raw_log in live_logs:
            if isinstance(raw_log, list) and len(raw_log) > 1:
                log_text = str(raw_log) 
            else:
                log_text = str(raw_log)
                
            if log_text in seen_logs:
                continue
            seen_logs.add(log_text)
                
            log_lower = log_text.lower()
            
            # --- THE PRE-FILTER UI FEED ---
            if any(word in log_lower for word in ["info", "debug", "application started", "content root path"]):
                
                # Send the boring log to TM4 so the dashboard looks alive!
                tm4_payload = {
                    "timestamp": time.strftime("%H:%M:%S"),
                    "service": "cartservice",
                    "log_text": log_text[:120], 
                    "classification": "NORMAL",
                    "nlp_confidence": 1.0,      
                    "badge_type": "SYS"         
                }
                
                try:
                    # Very short timeout so we don't slow down the AI loop
                    requests.post(tm4_url, json=tm4_payload, timeout=0.1)
                except Exception:
                    pass 
                
                continue # Skip the HuggingFace AI to save compute!
            
            # --- AI INFERENCE ---
            print(f"\n⏳ Analyzing: {log_text[:75]}...")
            
            result = query_huggingface(log_text)
            
            top_label = "unknown"
            confidence = 0.0
            
            if result and 'labels' in result:
                top_label = str(drill_for_data(result.get('labels', ['unknown'])))
                confidence = float(drill_for_data(result.get('scores', [0.0])))
                print(f"🧠 AI Decision: {top_label.upper()} (Score: {confidence:.2f})")
            
            elif not result:
                print("  [⚡ Switching to Local Heuristics Engine]")
                if any(err in log_lower for err in ["outofmemoryerror", "panic", "exception"]):
                    top_label = "critical system crash"
                    confidence = 0.99
                    print(f"🧠 Local Engine Decision: CRITICAL SYSTEM CRASH (Heuristics Triggered)")
                else:
                    continue 

            # --- TM4 DASHBOARD INTEGRATION (The AI Diagnosed Stream) ---
            classification_map = {
                "normal application behavior": "NORMAL",
                "minor warning": "WARNING",
                "critical system crash": "CRITICAL",
                "unknown": "NORMAL"
            }
            tm4_class = classification_map.get(top_label, "NORMAL")
            
            if tm4_class == "CRITICAL":
                badge = "CRIT"
            elif tm4_class == "WARNING":
                badge = "WARN"
            elif result: 
                badge = "AI"
            else:        
                badge = "SYS"

            tm4_ai_payload = {
                "timestamp": time.strftime("%H:%M:%S"),
                "service": "cartservice",
                "log_text": log_text[:150], 
                "classification": tm4_class,
                "nlp_confidence": round(confidence, 4),
                "badge_type": badge
            }

            try:
                requests.post(tm4_url, json=tm4_ai_payload, timeout=1)
            except Exception:
                pass 

            # --- TM3 TRIGGER & NETWORK HANDOFF ---
            if top_label == "critical system crash" and confidence > 0.50:
                alert_payload = {
                    "service_name": "cartservice", 
                    "nlp_confidence": round(confidence, 4)
                }
                
                tm3_payload = [alert_payload] 
                
                print("\n [CRITICAL ANOMALY DETECTED]")
                
                try:
                    print(f"📡 Beaming Array Payload to TM3 at {tm3_url}...")
                    response = requests.post(tm3_url, json=tm3_payload, timeout=3)
                    
                    if response.status_code == 200:
                        print(" Handoff Successful: TM3 is initiating auto-heal.")
                    else:
                        print(f" TM3 Laptop Error: Status {response.status_code}")
                except Exception as e:
                    print(f"❌ Network Error: Could not reach TM3's laptop. {e}")

                return 
        
        time.sleep(2)

if __name__ == "__main__":
    process_logs()