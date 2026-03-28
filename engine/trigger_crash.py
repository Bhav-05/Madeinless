import os
import subprocess
import asyncio
import httpx
import time

# --- CONFIGURATION ---
# 1. DOUBLE CHECK TM3 IP: 10.42.121.26
# 2. DOUBLE CHECK TM3 PORT: 8001
TM3_URL = "http://10.42.121.26:8001/alert" 

def trigger_physical_crash():
    print("\n🔥 STEP 1: Physically starving cartservice of memory...")
    # This triggers the actual OOM in Docker
    cmd = "docker update --memory=50m --memory-swap=50m cartservice"
    subprocess.run(cmd, shell=True)
    print("✅ Memory Limit Imposed. System should start failing now.")

async def fire_payload(client, url, payload, request_id):
    try:
        # We send the payload (a list containing one dict)
        response = await client.post(url, json=payload, timeout=5.0)
        return response.status_code
    except Exception as e:
        return str(e)

async def execute_chaos_barrage():
    print(f"\n🚀 STEP 2: Launching Network Barrage to {TM3_URL}...")
    
    # Matching TM3's expected FastAPI List[AnomalyAlert] format
    payload = [{
        "service_name": "cartservice", 
        "nlp_confidence": 0.99
    }]
    
    start_time = time.perf_counter()
    async with httpx.AsyncClient() as client:
        # Firing 20 concurrent requests
        tasks = [fire_payload(client, TM3_URL, payload, i) for i in range(20)]
        results = await asyncio.gather(*tasks)
    
    end_time = time.perf_counter()
    
    # FIX: Correctly check the status code in the results list
    successes = [r for r in results if r == 200]
    
    print(f"⚡ BARRAGE COMPLETE in {end_time - start_time:.4f}s")
    print(f"📊 Results: {len(successes)}/20 Alerts Successfully Delivered.")
    
    if len(successes) < 20:
        print("⚠️  Warning: Some payloads failed.")
        # Print the first error if it exists to help you debug
        errors = [r for r in results if r != 200]
        if errors:
            print(f"DEBUG: First error seen: {errors}")

if __name__ == "__main__":
    print("\n" + "="*40)
    print("--- SILICON FLOW CHAOS TRIGGER ---")
    print("="*40)
    print("1. Standard OOM Crash (Physical)")
    print("2. Network Alert Barrage (Stress Test)")
    print("3. Full System Meltdown (Both)")
    
    choice = input("\nSelect Chaos Level (1-3): ")

    if choice == "1":
        trigger_physical_crash()
    elif choice == "2":
        asyncio.run(execute_chaos_barrage())
    elif choice == "3":
        trigger_physical_crash()
        asyncio.run(execute_chaos_barrage())
    else:
        print("Invalid choice. Aborting.")